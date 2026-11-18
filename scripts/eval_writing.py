"""Writing evals (v4.14): real Claude calls, run by hand when the writing prompt or model change.

    .venv/bin/python scripts/eval_writing.py   # 3 small-model calls

Three paragraphs answering a prompt about a made-up fable, graded by the real model: a good
one meets every item Claude checks; a list of facts with no wrap-up misses the wrap-up and the
tip says so; one with misspellings has them come back as their right spellings. Uses the
admin's Claude account. Add one case for each problem seen.
"""

import tempfile
from datetime import date
from pathlib import Path

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.writing import Task, WritingDesk, WritingStore

# the respond prompt, as the reading call would write it
PROMPT = "Would you rather be the tortoise or the hare? Use one thing from the story."
# every checklist item met: topic, details, describing words, a wrap-up
GOOD = ("I would rather be the tortoise. The slow, steady tortoise never stopped walking. "
        "The proud hare took a long nap and lost the race. Being careful helped the tortoise "
        "win. That is why I would pick the tortoise.")
# facts in a row, no describing words to speak of, and no last sentence that sums up
NO_WRAP = ("The tortoise was slow. The hare was fast. The hare took a nap. The tortoise "
           "walked past him. The race had a finish line.")
# "becuase" and "frend" should come back as because and friend
MISSPELLED = ("I wud be the hare becuase he is fast. The hare can run reely far. He took a "
              "nap under a big tree. My frend says the tortoise is better. I still like the "
              "hare most.")


class Collect:
    """Stands in for the spelling desk: keeps the suggested words to print."""

    def __init__(self) -> None:
        self.words: list[str] = []

    def suggest(self, username: str, words: list[str], today: date) -> int:
        self.words += words  # nothing saved: printed below
        return len(words)


def main() -> None:
    spelling = Collect()  # no spelling file: the eval keeps nothing
    with tempfile.TemporaryDirectory() as tmp:
        desk = WritingDesk(WritingStore(Path(tmp)), writer=ClaudeCodeQuizzer(), spelling=spelling)
        task = Task("respond", PROMPT)
        graded = {name: desk.grade("eval", task, text, date.today())  # real calls
                  for name, text in (("good", GOOD), ("no wrap-up", NO_WRAP),
                                     ("misspelled", MISSPELLED))}
    for name, g in graded.items():
        print(f"{name}: marks={g.marks} well={g.well!r} tip={g.tip!r}")
    print(f"suggested: {spelling.words}")  # read by eye, with the lines above
    good, flat = graded["good"], graded["no wrap-up"]
    results = [
        # first, details, describing, wrap: what Claude checks (capitals are code's)
        ("good: every item Claude checks is met",
         all(good.marks[i] for i in (0, 1, 2, 4))),
        ("no wrap-up: wrap-up not yet, and the tip names an ending",
         not flat.marks[4] and any(w in flat.tip.lower() for w in ("end", "wrap", "sum"))),
        ("misspelled: the right spellings come back",
         {"because", "friend"} <= set(spelling.words)),
    ]
    print()  # then the pass/fail summary
    for name, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{sum(ok for _, ok in results)} of {len(results)} pass")


if __name__ == "__main__":
    main()
