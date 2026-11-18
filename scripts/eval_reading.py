"""Reading evals (v4.13): real Claude calls, run by hand when the reading prompts or model change.

    .venv/bin/python scripts/eval_reading.py   # about 7 small-model calls and one page fetch

A passage at levels 1 and 4 (a fable, then a government page), printed to read by eye: each
must pass the checks in code and the blind check, within a grade of its target. Then three
open answers: a good one, a bare noun (nudged), and an off-topic one (not right). Uses the
admin's Claude account. Add one case for each problem seen.
"""

import tempfile
from datetime import date
from pathlib import Path

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.interests import MapStore, add_interest
from lerni.student.reading import (
    TARGET,
    TOO_HARD,
    ReadingDesk,
    ReadingStore,
    Source,
    race_slots,
)

INTERESTS = ("sharks", "race cars", "dinosaurs")  # a made-up student's map
FABLE = Source("narrative", "The Tortoise and the Hare", "Aesop", "As is")
PAGE = Source("informational", "White Shark (great white)", "NOAA Fisheries",
              "Retold by Lerni (facts kept)", "https://www.fisheries.noaa.gov/species/white-shark",
              fetch=True,
              notes="Written for adults: pick a paragraph.")


def desk_for(root: Path, source: Source, level: int) -> ReadingDesk:
    """A reading desk on a throwaway folder: one source, a made-up map, at ``level``."""
    maps = MapStore(root)
    maps.change("eval", lambda m: [add_interest(m, n) for n in INTERESTS])
    store = ReadingStore(root)
    store.save_sources([source])
    store._change("eval", lambda d: d.update(level=level))  # start at this level
    return ReadingDesk(store, maps, writer=ClaudeCodeQuizzer())


def passage_at(source: Source, level: int) -> tuple[list[tuple[str, bool]], object]:
    """One passage from ``source`` at ``level``: (name, passed) per check, and the passage."""
    with tempfile.TemporaryDirectory() as tmp:
        p = desk_for(Path(tmp), source, level).write("eval", True, date.today())  # real calls
    name = f"level {level} ({source.title})"
    if p is None:
        print(f"\n{name}: dropped by a check")
        return [(f"{name}: written and checked", False)], None
    print(f"\n{name}: grade {p.grade} (target {TARGET[level]}), {len(p.text.split())} words")
    print(f"  {p.title}\n  {p.text}\n  Q: {p.question} {p.choices} -> {p.answer}")
    print(f"  Order: {p.order}\n  Open: {p.open_question} -> {p.key_ideas}")
    return [(f"{name}: written and checked", True),
            (f"{name}: within a grade of its target", p.grade <= TARGET[level] + TOO_HARD)], p


def open_answers(p) -> list[tuple[str, bool]]:
    """Three answers to the passage's last open question, graded by the real model."""
    with tempfile.TemporaryDirectory() as tmp:
        desk = desk_for(Path(tmp), FABLE, p.level)
        last = race_slots(p, desk.rng)[1][4]  # question 5
        good = desk.check("eval", last, f"{p.key_ideas[0]} and brave", date.today())
        bare = desk.check("eval", last, "a rabbit", date.today())
        off = desk.check("eval", last, "i like pizza", date.today())
    for label, c in (("good", good), ("bare", bare), ("off-topic", off)):
        print(f"  {label}: right={c.right} line={c.note!r} nudge={c.again!r}")
    return [("open: a good answer is right", good.right),
            ("open: a bare noun is nudged", bool(bare.again)),
            ("open: an off-topic answer is not right", not off.right)]


def main() -> None:
    first, fable = passage_at(FABLE, 1)
    second, _ = passage_at(PAGE, 4)
    results = [*first, *second, *(open_answers(fable) if fable else [])]
    print()
    for name, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in results)} of {len(results)} pass")


if __name__ == "__main__":
    main()
