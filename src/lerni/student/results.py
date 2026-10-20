"""Race results, kept for good: one line per answer and per finish, as labels and numbers.

``<data root>/results/<user>.jsonl``: the day, the race, the goal, the idea it tested,
a short hash of the question (never its words), right or wrong, and the seconds it took;
then each finish's place and points. What later versions learn difficulty and spaced
review from. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from lerni.student.concepts import normalize
from lerni.student.students import check_username, default_data_dir

WEEK_DAYS = 7


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
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def week(self, username: str, today: date) -> list[tuple[str, int, int]]:
        """Per goal over the last 7 days: (goal, right, asked), most recently practiced first."""
        since = (today - timedelta(days=WEEK_DAYS - 1)).isoformat()
        tally: dict[str, list[int]] = {}
        for r in self.read(username):
            if "right" in r and str(r.get("day", "")) >= since and r.get("goal"):
                counts = tally.pop(str(r["goal"]), [0, 0])  # re-inserted: newest last
                counts[0] += bool(r["right"])
                counts[1] += 1
                tally[str(r["goal"])] = counts
        return [(goal, right, asked) for goal, (right, asked) in reversed(tally.items())]


def week_line(results: ResultsLog, username: str, today: date) -> str:
    """ "This week: Fractions 7/10 · Acceleration 4/5", or "" with no races this week."""
    week = results.week(username, today)
    return ("This week: " + " · ".join(f"{g} {r}/{a}" for g, r, a in week)) if week else ""
