"""The ideas each player's race questions recently tested, so new ones ask about others.

One JSON file per player in ``<data root>/concepts/``: short concept labels, the
goal they practiced, and the day, never a question or an answer. Standard library only.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import date, timedelta
from pathlib import Path

from lerni.student.jsonfiles import write_json_atomic
from lerni.student.students import check_username, default_data_dir

MAX_CONCEPT = 40  # characters in a label
KEEP_RECENT = 40  # labels remembered per player
RECENT_DAYS = 14


def normalize(text: str) -> str:
    """Lowercase words only, single-spaced, for comparing labels and questions."""
    return " ".join(re.sub(r"[^\w]+", " ", text.casefold()).split())


class ConceptStore:
    """Everyone's recent concepts on disk, changed one at a time per player."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "concepts"
        self._lock = threading.Lock()  # few writes, one per race start

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"

    def _read(self, username: str) -> list[dict[str, str]]:
        try:
            data = json.loads(self._path(username).read_text(encoding="utf-8"))
            return [r for r in data.get("recent", []) if isinstance(r, dict) and r.get("concept")]
        except (OSError, ValueError, AttributeError):
            return []  # missing or broken: nothing recent, and the race still runs

    def recent(self, username: str, today: date | None = None) -> list[str]:
        """Labels asked in the last 14 days, newest first, at most 40."""
        cutoff = ((today or date.today()) - timedelta(days=RECENT_DAYS)).isoformat()
        return [str(r["concept"]) for r in self._read(username) if str(r.get("day", "")) >= cutoff][
            :KEEP_RECENT
        ]

    def add(self, username: str, items: list[tuple[str, str]], today: date | None = None) -> None:
        """Remember (goal, concept) pairs asked today; an old label moves to the front."""
        day = (today or date.today()).isoformat()
        cutoff = ((today or date.today()) - timedelta(days=RECENT_DAYS)).isoformat()
        with self._lock:
            new = [{"concept": c, "goal": g, "day": day} for g, c in items]
            keys = {normalize(r["concept"]) for r in new}
            old = [
                r
                for r in self._read(username)
                if normalize(str(r["concept"])) not in keys and str(r.get("day", "")) >= cutoff
            ]
            write_json_atomic(
                self._path(username), {"schema": 1, "recent": (new + old)[:KEEP_RECENT]}
            )
