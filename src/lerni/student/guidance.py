"""The educator's guidance notes (v4.9): short notes every race write and the morning plan
follow, for all goals or one goal, saved only from a tick in Tell Lerni (CLAUDE.md rule 5).

Stored per student at ``<data root>/guidance/<user>.json``: the notes, goal ids, and days;
never a student's words. Standard library only.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Collection
from datetime import date
from pathlib import Path
from typing import Any

from lerni.student.interests import MAX_NOTES
from lerni.student.jsonfiles import read_json, write_json_atomic
from lerni.student.students import check_username, default_data_dir

MAX_GUIDANCE = 10  # notes kept per student; the newest win (they go into every prompt)


class GuidanceStore:
    """Each student's guidance notes, newest last."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "guidance"
        self._lock = threading.Lock()

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"

    def notes(self, username: str) -> list[dict[str, Any]]:
        """Every note; none when the file is missing or broken (moved aside, never fatal)."""
        data = read_json(self._path(username)) or {}  # missing: no notes yet
        notes = data.get("notes")
        return (
            [n for n in notes if isinstance(n, dict) and n.get("text")]  # a hand edit: skipped
            if isinstance(notes, list)
            else []
        )

    def add(self, username: str, text: str, goal_id: str, today: date) -> None:
        """Keep a ticked note, for one goal (its id) or all goals ("")."""
        note = {
            "id": uuid.uuid4().hex[:8],  # a short id for Remove
            "goal_id": goal_id,  # "" for all goals
            "text": " ".join(text.split())[:MAX_NOTES],
            "day": today.isoformat(),
        }
        with self._lock:
            data = read_json(self._path(username), strict=True) or {}  # unreadable: kept as is
            old = [n for n in data.get("notes") or [] if isinstance(n, dict)]
            same = note["text"].casefold()  # "Use cm" and "use cm" are one note
            old = [
                n
                for n in old
                if (n.get("text", "").casefold(), n.get("goal_id")) != (same, goal_id)
            ]  # the same note again replaces the old one
            kept = [*old, note][-MAX_GUIDANCE:]  # the newest 10
            write_json_atomic(self._path(username), {"notes": kept})

    def remove(self, username: str, ids: Collection[str]) -> int:
        """Drop the notes with these ids; returns how many went."""
        with self._lock:
            data = read_json(self._path(username), strict=True) or {}
            old = [n for n in data.get("notes") or [] if isinstance(n, dict)]
            kept = [n for n in old if n.get("id") not in ids]  # an unknown id removes nothing
            write_json_atomic(self._path(username), {"notes": kept})
        return len(old) - len(kept)

    def for_goals(
        self, username: str, goal_ids: Collection[str] | None = None
    ) -> list[tuple[str, str]]:
        """(goal id, text) pairs: every all-goals note, plus these goals' own (None: all)."""
        return [
            (str(n.get("goal_id") or ""), str(n["text"]))
            for n in self.notes(username)
            if not n.get("goal_id") or goal_ids is None or n.get("goal_id") in goal_ids
        ]
