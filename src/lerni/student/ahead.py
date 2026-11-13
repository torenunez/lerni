"""Race questions written ahead, kept on disk until their day ends (v4.6.1), so a restart or
a deploy doesn't throw them away and the next race doesn't wait for Claude.

Stored per student at ``<data root>/ahead/<user>.json``: the day, and today's unraced
questions and bonus questions as Claude wrote them (never a student's words). A file from an
earlier day is deleted at start-up and each morning. Standard library only.
"""

from __future__ import annotations

import threading
from datetime import date
from pathlib import Path
from typing import Any

from lerni.student.jsonfiles import read_json, write_json_atomic
from lerni.student.students import check_username, default_data_dir


class AheadStore:
    """Each student's questions written ahead, as plain dicts (the race desk builds them)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "ahead"
        self._lock = threading.Lock()

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"  # a safe name: no path tricks

    def save(
        self,
        username: str,
        day: date,
        questions: list[dict[str, Any]],
        bonuses: list[dict[str, Any]],
    ) -> None:
        """Replace this student's file with what's held now, stamped with ``day``."""
        with self._lock:  # one write at a time; the file is replaced whole
            write_json_atomic(
                self._path(username),
                {"day": day.isoformat(), "questions": questions, "bonuses": bonuses},
            )

    def load(self, today: date) -> dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
        """Today's files only: (questions, bonuses) by username; a broken file is skipped."""
        held = {}  # username: (questions, bonuses)
        for path in sorted(self.root.glob("*.json")) if self.root.is_dir() else []:
            data = read_json(path) or {}  # unreadable: moved aside, never fatal
            if data.get("day") != today.isoformat():
                continue  # an earlier day's: purge deletes it
            qs, bs = data.get("questions"), data.get("bonuses")  # a hand edit may break either
            held[path.stem] = (
                [q for q in qs if isinstance(q, dict)] if isinstance(qs, list) else [],
                [b for b in bs if isinstance(b, dict)] if isinstance(bs, list) else [],
            )
        return held

    def purge(self, today: date) -> int:
        """Delete every file from an earlier day (rule 6: kept until its day ends)."""
        gone = 0  # files deleted, for the caller
        with self._lock:
            for path in self.root.glob("*.json") if self.root.is_dir() else []:
                data = read_json(path) or {}  # a broken one was moved aside already
                if data.get("day") != today.isoformat():  # its day has ended
                    path.unlink(missing_ok=True)
                    gone += 1
        return gone
