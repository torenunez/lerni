"""A batch of race questions per goal for the admin to rate (v4.5), written on a copy of the
data so nothing real is recorded. Standard library only."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from lerni.student.bank import BankStore
from lerni.student.concepts import ConceptStore
from lerni.student.garage import Garage
from lerni.student.interests import MapStore
from lerni.student.meaning import Embedder
from lerni.student.morning import SuggestionStore
from lerni.student.points import PointsStore
from lerni.student.race import Checker, Quizzer, RaceDesk, RaceUnavailable, race_view
from lerni.student.results import ResultsLog, question_hash

COPIED = ("maps", "concepts", "points", "results", "suggestions", "bank", "cars", "garage.json")
CHUNK = 3  # goals a write covers: about 3 kept questions each
ROUNDS = 4  # at most this many passes over the goals
PROBES = "Nearby ideas"  # the sheet's goal for probes


def write_batch(
    root: Path,
    username: str,
    quizzer: Quizzer,
    *,
    supervised: bool,
    today: date,
    per_goal: int = 8,
    checker: Checker | None = None,
    embedder: Embedder | None = None,
    only: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Questions that pass every race check, about ``per_goal`` on each goal, sorted by goal.

    Args:
        root: The real data folder; only read, through a temporary copy.
        username: Whose map and history the questions are written from.
        quizzer: Claude (or a fake) writing the questions.
        supervised: The account's kind, for the voice.
        today: The day the questions are written for.
        per_goal: Questions wanted on each goal.
        checker: The blind check; None keeps every question.
        embedder: Checks by meaning; None leaves them to words.
        only: Goal names to write on (any case); empty for every goal.

    Returns:
        One row per question: id, goal, goal_id, interest, format, question, choices,
        answer (0-2), right (A-C), why, concept, probe.
    """
    with tempfile.TemporaryDirectory(prefix="lerni-batch-") as tmp:
        copy = Path(tmp)
        for name in COPIED:  # never logs, accounts, or keys
            src = root / name
            if src.is_dir():
                shutil.copytree(src, copy / name)
            elif src.is_file():
                shutil.copy2(src, copy / name)
        desk = RaceDesk(
            quizzer,
            MapStore(copy),
            PointsStore(copy),
            ConceptStore(copy),
            checker=checker,
            results=ResultsLog(copy),
            garage=Garage(copy),
            embedder=embedder,
            bank=BankStore(copy),
        )
        desk.suggestions = SuggestionStore(copy)
        m = race_view(desk.maps.get(username), frozenset())
        wanted = {g.casefold() for g in only}  # --goal: just these
        goals = [e.name for e in m.entries
                 if e.kind == "goal" and (not wanted or e.name.casefold() in wanted)]
        count = dict.fromkeys(goals, 0)
        rows: dict[str, dict[str, Any]] = {}
        for _ in range(ROUNDS):
            need = [g for g in goals if count[g] < per_goal]
            if not need:
                break
            for i in range(0, len(need), CHUNK):
                try:
                    kept = desk._write(username, supervised, today, goals=need[i : i + CHUNK])
                except RaceUnavailable:
                    continue  # a chunk Claude couldn't write: the next round tries again
                _, held = desk._sets.get(username, ("", []))
                desk._sets[username] = (today.isoformat(), [*held, *kept])  # avoided next
                for q in kept:
                    key = question_hash(q.question)
                    if key in rows:
                        continue
                    goal = q.goal if not q.probe else PROBES
                    count[goal] = count.get(goal, 0) + 1
                    rows[key] = {
                        "id": key,
                        "goal": goal,
                        "goal_id": q.goal_id,
                        "interest": q.setting,
                        "format": q.format,
                        "question": q.question,
                        "choices": list(q.choices),
                        "answer": q.answer,
                        "right": "ABC"[q.answer],
                        "why": q.why,
                        "concept": q.concept,
                        "probe": q.probe,
                    }
    return sorted(rows.values(), key=lambda r: r["goal"].casefold())
