"""Race results, kept for good: one line per answer and per finish, as labels and numbers.

``<data root>/results/<user>.jsonl``: the day, the race, the goal (id and name), the idea it
tested, a short hash of the question (never its words), the level it was written at, its
attempt (1: a new idea), right or wrong, and the seconds it took;
then each finish's place and points. What later versions learn difficulty and spaced
review from. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from lerni.student.concepts import normalize
from lerni.student.students import check_username, default_data_dir

WEEK_DAYS = 7
MISSED_DAYS = 14  # a miss shows this long, unless a right answer clears it
MAX_MISSED = 3


@dataclass(frozen=True)
class Practice:
    """How racing on one goal is going: read from the log, never stored."""

    last: str  # the last day it was raced (ISO)
    right: int  # this week
    asked: int
    missed: list[str]  # ideas missed lately and not answered right since, newest first


def question_hash(question: str) -> str:
    """A short fingerprint of a question, so repeats can be told apart without its words."""
    return hashlib.sha256(normalize(question).encode()).hexdigest()[:12]


class ResultsLog:
    """Everyone's race results on disk, one line appended at a time."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "results"
        self._lock = threading.Lock()

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.jsonl"

    def add(self, username: str, record: dict[str, Any]) -> None:
        """Append one record (labels and numbers only)."""
        path = self._path(username)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read(self, username: str) -> list[dict[str, Any]]:
        """Every record, oldest first; a broken line is skipped."""
        try:
            lines = self._path(username).read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines:  # the whole file: about 50 lines a day is small at family scale
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):  # anything else is skipped like a broken line
                out.append(record)
        return out

    def week(self, username: str, today: date) -> list[tuple[str, str, int, int]]:
        """Per goal over the last 7 days: (goal id, goal, right, asked), most recently
        practiced first; by id when the line has one, so a renamed goal keeps its rows."""
        since = (today - timedelta(days=WEEK_DAYS - 1)).isoformat()
        tally: dict[str, list[Any]] = {}
        for r in self.read(username):
            if "right" in r and str(r.get("day", "")) >= since and r.get("goal"):
                key = str(r.get("goal_id") or r["goal"])
                counts = tally.pop(key, [str(r.get("goal_id", "")), str(r["goal"]), 0, 0])
                counts[1] = str(r["goal"])  # the newest name, after a rename
                counts[2] += bool(r["right"])  # re-inserted below: newest last
                counts[3] += 1
                tally[key] = counts
        return [tuple(c) for c in reversed(tally.values())]  # type: ignore[misc]

    def asked_since(self, username: str, since: date) -> dict[str, int]:
        """Questions per goal id since ``since``, for picking the least practiced goals."""
        counts: dict[str, int] = {}
        for r in self.read(username):
            if "right" in r and r.get("goal_id") and str(r.get("day", "")) >= since.isoformat():
                counts[str(r["goal_id"])] = counts.get(str(r["goal_id"]), 0) + 1
        return counts

    def practice(self, username: str, goal_id: str, today: date) -> Practice | None:
        """One goal's Practice line, or None if it was never raced."""
        lines = [r for r in self.read(username)
                 if "right" in r and goal_id and r.get("goal_id") == goal_id]
        if not lines:
            return None
        week = (today - timedelta(days=WEEK_DAYS - 1)).isoformat()
        lately = (today - timedelta(days=MISSED_DAYS - 1)).isoformat()
        recent = [r for r in lines if str(r.get("day", "")) >= week]
        missed: dict[str, str] = {}  # newest first, each idea once (by its normalized label)
        cleared: set[str] = set()
        for r in reversed(lines):  # newest first: a right answer clears older misses
            concept = str(r.get("concept") or "")
            key = normalize(concept)
            if not key or str(r.get("day", "")) < lately:
                continue
            if r["right"]:
                cleared.add(key)
            elif key not in cleared:
                missed.setdefault(key, concept)
        return Practice(max(str(r.get("day", "")) for r in lines),
                        sum(bool(r["right"]) for r in recent), len(recent),
                        list(missed.values())[:MAX_MISSED])

