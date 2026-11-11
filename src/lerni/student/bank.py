"""The checked bank (v4.5): race questions an educator rated, per student, on disk.

Good ones become examples each goal's question writing sees; Bad and Needs-a-fix ones, with
their why, become lines to avoid, and that exact question never races. Standard library only.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from lerni.student.interests import InterestMap
from lerni.student.jsonfiles import read_json, write_json_atomic
from lerni.student.results import question_hash
from lerni.student.students import check_username, default_data_dir

RATINGS = {"good": "Good", "needs a fix": "Needs a fix", "bad": "Bad"}
WRONG = ("Needs a fix", "Bad")
MAX_TEXT = 500  # a cell's text is cut here
FINGERPRINT = re.compile(r"[0-9a-f]{12}")  # results.question_hash


def _text(value: Any) -> str:
    # one line, trimmed and cut
    return " ".join(str(value or "").split())[:MAX_TEXT]


def _answer(value: Any) -> int | None:
    # the right choice as 0-2, from an index or a letter
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1, 2):
        return value
    letter = _text(value).upper()
    return "ABC".index(letter) if letter in ("A", "B", "C") else None


class BankStore:
    """Each student's rated questions, keyed by the question's fingerprint."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "bank"
        self._lock = threading.Lock()

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"

    def items(self, username: str) -> list[dict[str, Any]]:
        """Every rated item; none when the file is missing or broken (moved aside)."""
        data = read_json(self._path(username)) or {}
        items = data.get("items")
        return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []

    def add_labels(
        self, username: str, rows: Sequence[dict[str, Any]], m: InterestMap, today: date
    ) -> tuple[int, int]:
        """Keep each rated row on its goal; returns (kept, skipped: goal gone or bad row).

        Unrated rows are left out and not counted. A new rating replaces the old one.
        """
        from lerni.student.race import goal_of  # race imports this module

        new: dict[str, dict[str, Any]] = {}
        skipped = 0
        for raw in rows:
            row = {str(k).casefold(): v for k, v in raw.items()}  # the sheet's headers too
            rating = RATINGS.get(_text(row.get("rating")).casefold())
            if rating is None:
                continue
            question = _text(row.get("question"))
            choices = row.get("choices") or [row.get(c) for c in "abc" if row.get(c) is not None]
            goal = goal_of(m, _text(row.get("goal_id")), _text(row.get("goal")))
            if goal is None and row.get("goal_id"):  # an id from before a rename: by name
                goal = goal_of(m, "", _text(row.get("goal")))
            answer = _answer(next((row[k] for k in ("answer", "right answer", "right")
                                   if row.get(k) not in (None, "")), None))
            if (goal is None or not question or answer is None or not isinstance(choices, list)
                    or len(choices) != 3):
                skipped += 1
                continue
            key = _text(row.get("id"))  # the question as written, unless Sheets changed it
            key = key if FINGERPRINT.fullmatch(key) else question_hash(question)
            new[key] = {
                "id": key,
                "goal_id": goal.id,
                "goal": goal.name,
                "question": question,
                "choices": [_text(c) for c in choices],
                "answer": answer,
                "why": _text(row.get("why")),
                "concept": _text(row.get("concept")),
                "format": _text(row.get("format")),
                "setting": _text(row.get("interest") or row.get("setting")),
                "rating": rating,
                "problem": _text(row.get("problem")),
                "notes": _text(row.get("notes")),
                "day": today.isoformat(),
                "by": "educator",
            }
        with self._lock:
            data = read_json(self._path(username), strict=True) or {}
            old = [
                i for i in data.get("items") or [] if isinstance(i, dict) and i.get("id") not in new
            ]
            write_json_atomic(self._path(username), {"items": [*old, *new.values()]})
        return len(new), skipped

    def _newest(
        self, username: str, goal_id: str, ratings: Sequence[str], k: int
    ) -> list[dict[str, Any]]:
        mine = [
            i
            for i in self.items(username)
            if i.get("goal_id") == goal_id and i.get("rating") in ratings
        ]
        return sorted(mine, key=lambda i: str(i.get("day", "")), reverse=True)[:k]

    def good(self, username: str, goal_id: str, k: int = 2) -> list[dict[str, Any]]:
        """The newest Good items on this goal."""
        return self._newest(username, goal_id, ("Good",), k)

    def wrong(self, username: str, goal_id: str, k: int = 3) -> list[dict[str, Any]]:
        """The newest Bad or Needs-a-fix items on this goal with a problem or notes."""
        mine = [
            i
            for i in self._newest(username, goal_id, WRONG, 100)
            if i.get("problem") or i.get("notes")
        ]
        return mine[:k]

    def blocked(self, username: str) -> set[str]:
        """The fingerprints of every Bad or Needs-a-fix question: never raced."""
        return {
            str(i["id"]) for i in self.items(username) if i.get("rating") in WRONG and i.get("id")
        }
