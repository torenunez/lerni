"""Conversation logs: each exchange and what the tagger did, kept 7 days for the admin.

``<data root>/logs/<username>/<date>.jsonl``, one JSON line per exchange. The
only place message text is saved; read with ``lerni logs``. Standard library only.
"""

from __future__ import annotations

import json
import shutil
import threading
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from lerni.student.students import check_username, default_data_dir

KEEP_DAYS = 7  # a file this many days old or older is deleted


class ConversationLog:
    """Every student's exchanges for the last 7 days."""

    def __init__(self, root: Path | None = None, today: Callable[[], date] = date.today) -> None:
        self.root = (root or default_data_dir()) / "logs"
        self.today = today
        self._lock = threading.Lock()
        self._purged: date | None = None

    def write(self, username: str, record: dict[str, Any]) -> None:
        """Append one exchange to today's file, purging old files once a day."""
        today = self.today()
        if self._purged != today:
            self.purge()
        line = {"time": datetime.now().isoformat(timespec="seconds"), **record}
        path = self.root / check_username(username) / f"{today.isoformat()}.jsonl"
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    def purge(self) -> None:
        """Delete files 7 or more days old, and folders left empty."""
        cutoff = (self.today() - timedelta(days=KEEP_DAYS)).isoformat()
        with self._lock:
            self._purged = self.today()
            if not self.root.is_dir():
                return
            for folder in self.root.iterdir():
                for path in folder.glob("*.jsonl"):
                    if path.stem <= cutoff:  # ISO dates sort like dates
                        path.unlink()
                if folder.is_dir() and not any(folder.iterdir()):
                    shutil.rmtree(folder)

    def read(self, username: str | None = None) -> list[dict[str, Any]]:
        """The kept exchanges, oldest first, each with its ``username``."""
        if not self.root.is_dir():
            return []
        if username:
            folders = [self.root / check_username(username)]
        else:
            folders = sorted(self.root.iterdir())
        records = []
        for folder in folders:
            for path in sorted(folder.glob("*.jsonl")):
                for line in path.read_text(encoding="utf-8").splitlines():
                    records.append({"username": folder.name, **json.loads(line)})
        return sorted(records, key=lambda r: r.get("time", ""))
