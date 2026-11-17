"""Spelling evals (v4.10): real Claude calls, run by hand when the spelling prompts or model change.

    .venv/bin/python scripts/eval_spelling.py   # 3 small-model calls

Lerni's picks at levels 1 and 5 for a made-up map, and sentences for a short class list,
printed to read by eye; every word must pass the checks. Uses the admin's Claude account.
Add one case for each problem seen.
"""

import tempfile
from datetime import date
from pathlib import Path

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.interests import MapStore, add_interest
from lerni.student.spelling import (
    LEVELS,
    PICK_RE,
    PICKS_PER_CALL,
    SpellingDesk,
    SpellingStore,
    uses_word,
)

INTERESTS = ("dinosaurs", "LEGO", "race cars")  # a made-up student's map
CLASS_LIST = "because\nfriend\nagain\nsaid"


def picks_at(level: int) -> list[tuple[str, bool]]:
    """Lerni's picks for a fresh student at ``level``; (name, passed) per check."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        maps = MapStore(root)
        maps.change("eval", lambda m: [add_interest(m, n) for n in INTERESTS])
        store = SpellingStore(root)  # a throwaway folder: nothing real is touched
        store.change("eval", lambda d: d.update(level=level))  # start at this level
        desk = SpellingDesk(store, maps, writer=ClaudeCodeQuizzer())
        kept = desk.write_picks("eval", date.today())  # the one real call
        words = store.get("eval")["words"]
    print(f"\nLevel {level} ({LEVELS[level]}): {kept} kept of {PICKS_PER_CALL} asked")
    for w in words:  # read by eye: does each fit the level and the interests?
        parts = f"  [{' · '.join(w['parts'])}]" if w["parts"] else ""
        print(f"  {w['word']:<12} {w['kind']:<9} {w['sentence']}{parts}")
    return [
        (f"level {level}: at least 8 of {PICKS_PER_CALL} kept", kept >= 8),
        (f"level {level}: plain lowercase words", all(PICK_RE.fullmatch(w["word"])
                                                       for w in words)),
        (f"level {level}: each sentence uses its word", all(uses_word(w["sentence"], w["word"])
                                                            for w in words)),
        (f"level {level}: some adjectives", any(w["kind"] == "adjective" for w in words)),
    ]


def class_sentences() -> list[tuple[str, bool]]:
    """Sentences for a class list: one per word, each using it."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = SpellingStore(root)
        desk = SpellingDesk(store, MapStore(root), writer=None)  # no Claude yet
        desk.set_class_list("eval", CLASS_LIST)  # so no background sentence call
        desk.writer = ClaudeCodeQuizzer()
        written = desk.write_sentences("eval")  # the one real call, waited for
        words = store.get("eval")["words"]
    print(f"\nClass list sentences: {written} of {len(words)}")
    for w in words:
        print(f"  {w['word']:<10} {w['sentence']}")
    return [("class list: a sentence for every word", written == len(words))]


def main() -> None:
    results = [*picks_at(1), *picks_at(5), *class_sentences()]  # 3 calls in all
    print()
    for name, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in results)} of {len(results)} pass")


if __name__ == "__main__":
    main()
