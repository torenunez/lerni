"""Every idea a player's race questions have tested, kept for good: the long-term record
of what was asked and how it went, the "asked lately" list that keeps questions new, and
each goal's level (v3.18), so questions get harder or easier for about 50-75% right.

One JSON file per player in ``<data root>/concepts/``: short concept labels, the
goal they practiced, dates, counts, and levels by goal id, never a question or an answer.
Standard library only.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from lerni.student.jsonfiles import write_json_atomic
from lerni.student.students import check_username, default_data_dir

MAX_CONCEPT = 40  # characters in a label
KEEP_RECENT = 40  # labels sent to Claude as asked lately
RECENT_DAYS = 14
START_LEVEL, MIN_LEVEL, MAX_LEVEL = 3, 1, 5  # 3 is the questions before levels
LEVEL_WINDOW = 5  # answers on a goal between level checks
REVIEW_DAYS = (1, 3, 7)  # a missed idea comes back after these gaps, one per right answer
UP_AT, DOWN_AT = 4, 2  # this many right of 5 or more: harder; this many or fewer: easier
GOAL_DAYS = (1, 3, 7, 14)  # a goal's boxes: days until it comes back (v3.28)


def normalize(text: str) -> str:
    """Lowercase words only, single-spaced, for comparing labels and questions."""
    return " ".join(re.sub(r"[^\w]+", " ", text.casefold()).split())


def _level(v: Any) -> int:
    """A stored level as 1 to 5; anything odd (a hand edit) is the start level."""
    try:
        level = int(v.get("level", START_LEVEL)) if isinstance(v, dict) else START_LEVEL
    except (TypeError, ValueError):
        return START_LEVEL
    return max(MIN_LEVEL, min(MAX_LEVEL, level))


def _day(value: Any) -> date | None:
    """A stored ISO date, or None for none or anything odd (a hand edit)."""
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


class ConceptStore:
    """Everyone's concept ledgers on disk, changed one at a time."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_data_dir()) / "concepts"
        self._lock = threading.Lock()  # a few writes per race

    def _path(self, username: str) -> Path:
        return self.root / f"{check_username(username)}.json"

    def _read(self, username: str) -> dict[str, Any]:
        try:
            data = json.loads(self._path(username).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}  # missing or broken: nothing known, and the race still runs
        return data if isinstance(data, dict) else {}

    def ledger(self, username: str) -> list[dict[str, Any]]:
        """Every idea asked, oldest-touched first: concept, goal, first, last, asked, right."""
        data = self._read(username)
        if not data:
            return []
        if "concepts" not in data:  # a v3.9 file: the recent list only
            return [
                {
                    "concept": str(r["concept"]),
                    "goal": str(r.get("goal", "")),
                    "first": str(r.get("day", "")),
                    "last": str(r.get("day", "")),
                    "asked": 1,
                    "right": 0,
                }
                for r in reversed(data.get("recent", []))
                if isinstance(r, dict) and r.get("concept")
            ]
        return [c for c in data["concepts"] if isinstance(c, dict) and c.get("concept")]

    def recent(self, username: str, today: date | None = None) -> list[str]:
        """Labels asked in the last 14 days, newest first, at most 40."""
        cutoff = ((today or date.today()) - timedelta(days=RECENT_DAYS)).isoformat()
        asked = [
            str(c["concept"])
            for c in reversed(self.ledger(username))
            if str(c.get("last", "")) >= cutoff
        ]
        return asked[:KEEP_RECENT]

    def _levels(self, username: str) -> dict[str, dict[str, Any]]:
        raw = self._read(username).get("levels", {})
        return {str(g): v for g, v in raw.items() if isinstance(v, dict)} if isinstance(
            raw, dict) else {}

    def _change(self, username: str, fn: Any = None, levels: Any = None) -> None:
        # the ideas and the levels are written together, so neither loses the other
        with self._lock:
            ledger, by_goal = self.ledger(username), self._levels(username)
            if fn is not None:
                fn(ledger)
            if levels is not None:
                levels(by_goal)
            write_json_atomic(self._path(username),
                              {"schema": 3, "concepts": ledger, "levels": by_goal})

    def levels(self, username: str) -> dict[str, int]:
        """Each goal's level by goal id; a goal not listed is at the start level."""
        return {g: _level(v) for g, v in self._levels(username).items()}

    def practiced(self, username: str, goal_id: str, right: bool) -> None:
        """Count one answer on a goal; every 5, its level moves by how many were right."""
        if not goal_id:
            return  # a goal gone from the map

        def apply(by_goal: dict[str, dict[str, int]]) -> None:
            v = by_goal.get(goal_id)
            if not isinstance(v, dict) or not all(
                    isinstance(v.get(k), int) for k in ("asked", "right")):
                # a hand edit (odd counts) starts the count over
                v = {"level": _level(v), "right": 0, "asked": 0}
            by_goal[goal_id] = v
            v["asked"] += 1
            v["right"] += bool(right)
            if v["asked"] >= LEVEL_WINDOW:
                step = 1 if v["right"] >= UP_AT else -1 if v["right"] <= DOWN_AT else 0
                v.update(level=_level({"level": _level(v) + step}), right=0, asked=0)

        self._change(username, levels=apply)

    def raced(self, username: str, per_goal: dict[str, tuple[int, int]],
              today: date | None = None) -> None:
        """Move each goal a finished race asked by how it went: all right on a due goal, one box
        up (a longer gap); half or fewer, back to box 0 (tomorrow); otherwise it stays, so a
        goal raced again early (the same set's second race) never skips a box."""
        day = today or date.today()

        def apply(by_goal: dict[str, dict[str, Any]]) -> None:
            for goal_id, (right, asked) in per_goal.items():
                if not goal_id or asked <= 0:
                    continue
                v = by_goal.setdefault(goal_id, {"level": START_LEVEL, "right": 0, "asked": 0})
                box = v.get("box") if isinstance(v.get("box"), int) else 0
                box = min(max(box, 0), len(GOAL_DAYS) - 1)  # a hand edit stays in range
                was_due = _day(v.get("due"))
                if right * 2 <= asked:
                    box = 0
                elif right < asked or (was_due is not None and was_due > day):
                    continue  # partly right, or early: box and date stay
                elif "due" in v or box:
                    box = min(box + 1, len(GOAL_DAYS) - 1)
                else:
                    box = 1  # first race, all right
                v.update(box=box, due=(day + timedelta(days=GOAL_DAYS[box])).isoformat())

        self._change(username, levels=apply)

    def schedule(self, username: str) -> dict[str, tuple[date, int]]:
        """Each raced goal's (due date, box) by goal id; a goal not listed is due now."""
        out = {}
        for goal_id, v in self._levels(username).items():
            due = _day(v.get("due"))
            if due is not None:
                box = v.get("box") if isinstance(v.get("box"), int) else 0
                out[goal_id] = (due, min(max(box, 0), len(GOAL_DAYS) - 1))
        return out

    def add(self, username: str, items: list[tuple[str, str]], today: date | None = None) -> None:
        """Note (goal, concept) pairs asked today; each moves to the end, as the newest."""
        day = (today or date.today()).isoformat()

        def apply(ledger: list[dict[str, Any]]) -> None:
            for goal, concept in items:
                key = normalize(concept)
                old = next((c for c in ledger if normalize(str(c["concept"])) == key), None)
                if old is None:
                    old = {
                        "concept": concept,
                        "goal": goal,
                        "first": day,
                        "last": day,
                        "asked": 0,
                        "right": 0,
                    }
                else:
                    ledger.remove(old)
                old.update(goal=goal, last=day, asked=int(old.get("asked", 0)) + 1)
                ledger.append(old)

        self._change(username, apply)

    def answered(self, username: str, concept: str, right: bool,
                 today: date | None = None) -> None:
        """Count an answer on this idea and move its review: a miss is due tomorrow; a right
        answer on a due idea pushes it to 3 days, then 7, then retires it."""
        day = today or date.today()

        def apply(ledger: list[dict[str, Any]]) -> None:
            key = normalize(concept)
            for c in ledger:
                if normalize(str(c["concept"])) != key:
                    continue
                if not right:
                    c.update(step=0, due=(day + timedelta(days=REVIEW_DAYS[0])).isoformat())
                    continue
                c["right"] = int(c.get("right", 0)) + 1
                due = _day(c.get("due"))
                if due is None or due > day:
                    continue  # never missed, retired, or not due yet: only counted
                step = min(max(c.get("step", 0) if isinstance(c.get("step"), int) else 0, 0), 2) + 1
                if step >= len(REVIEW_DAYS):
                    c.pop("due", None)  # right three times in a row: learned
                    c.pop("step", None)
                else:
                    c.update(step=step, due=(day + timedelta(days=REVIEW_DAYS[step])).isoformat())

        self._change(username, apply)

    def due(self, username: str, today: date | None = None) -> list[tuple[str, str]]:
        """(goal, idea) pairs due for review today or earlier, the longest waiting first."""
        day = today or date.today()
        waiting = [c for c in self.ledger(username) if (d := _day(c.get("due"))) and d <= day]
        waiting.sort(key=lambda c: c["due"])
        return [(str(c.get("goal", "")), str(c["concept"])) for c in waiting]
