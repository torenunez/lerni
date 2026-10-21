"""Race question evals: real Claude calls, run by hand when the race instructions or model change.

    .venv/bin/python scripts/eval_race.py

Uses the admin's Claude account. Add one case for each problem seen.
"""

import re
from datetime import date

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.concepts import normalize
from lerni.student.garage import Car
from lerni.student.interests import InterestMap, add_goal, add_interest, remove
from lerni.student.race import (
    CHECK_SCHEMA,
    CHECK_SYSTEM,
    QUIZ_SYSTEM,
    Question,
    check_input,
    check_questions,
    quiz_input,
)

REUSED: list[int] = []  # per call: ideas Claude wrote again though told they were asked


def write(m: InterestMap, supervised: bool = True, before: list | None = None,
          levels: dict | None = None, cars: list | None = None) -> list:
    recent = [q.concept for q in before or []]
    raw = ClaudeCodeQuizzer().write(QUIZ_SYSTEM, quiz_input(m, date.today(), supervised, recent,
                                                            levels, cars or []))
    asked = {normalize(c) for c in recent}
    reused = [i for i in raw.get("questions", []) if normalize(str(i.get("concept"))) in asked]
    print(f"Claude reused {len(reused)} of the ideas it was told were asked")
    REUSED.append(len(reused))
    kept = check_questions(raw, m, concepts=recent,
                           texts=[normalize(q.question) for q in before or []])
    for q in kept:
        print(f"[{q.goal} · {q.concept}] {q.question} → {q.choices} ✓{q.choices[q.answer]}")
    return kept


def main() -> None:
    m = InterestMap()
    add_goal(m, "Fractions", "halves and quarters")
    add_goal(m, "Acceleration")
    cars = add_interest(m, "race cars")
    cars.days = [date.today().isoformat()]
    remove(m, add_interest(m, "sharks").id)
    kept = write(m)
    again = write(m, before=kept)  # the next call, told what was asked
    raw_again = len(again)
    results = [
        ("at least one race of good questions", len(kept) >= 5),
        ("every question practices a goal on the map",
         all(q.goal in ("Fractions", "Acceleration") for q in kept)),
        ("both goals come up (a goal with notes once lost all its questions)",
         {q.goal for q in kept} == {"Fractions", "Acceleration"}),
        ("nothing set aside comes up",
         all("shark" not in (q.question + " ".join(q.choices)).casefold() for q in kept)),
        # regression: production raced the same questions again and again
        ("told what was asked, the next set is still a race's worth of new ideas", raw_again >= 5),
        ("told what was asked, Claude reuses at most one idea", REUSED[-1] <= 1),
    ]
    # the blind check (v3.14): a wrong key is caught, a right one kept
    keyed = [
        Question("Fractions", "A race car does 2 laps, then 2 more. How many laps in all?",
                 ("5", "4", "3"), 0, "2 and 2 make 4.", "adding laps"),  # keyed wrong
        Question("Acceleration", "Which tells you how fast a car speeds up from a stop?",
                 ("its top speed", "its 0 to 60 time", "its color"), 0, "", "0-60 vs top speed"),
        Question("Fractions", "Half of 10 laps is how many laps?", ("5", "2", "20"), 0, "",
                 "half of a number"),  # keyed right
    ]
    picks = [p["pick"] for p in
             ClaudeCodeQuizzer().write(CHECK_SYSTEM, check_input(keyed), CHECK_SCHEMA)["picks"]]
    print("blind picks:", picks)
    results.append(("both wrong keys are caught", picks[0] != "A" and picks[1] != "A"))
    results.append(("a right key is kept", picks[2] == "A"))
    # levels (v3.18): the same goal at 1 and at 5, printed to compare by eye
    one = InterestMap()
    goal = add_goal(one, "Fractions", "halves and quarters")
    trucks = add_interest(one, "monster trucks")
    trucks.days = [date.today().isoformat()]
    for level in (1, 5):
        print(f"--- level {level}")
        sets = write(one, levels={goal.id: level})
        results.append((f"level {level} still makes a race", len(sets) >= 5))
    # the garage (v3.19): two cars in reach; the locked one is never given, so never named
    near = [Car("p1", "McLaren P1", 460, "#000", "", 1_150_000, 2.7, "3.8L twin-turbo V8 hybrid",
                903, "Rear-wheel drive"),
            Car("m4", "BMW M4", 40, "#000", "", 100_000, 3.4, "3.0L twin-turbo I6", 523,
                "All-wheel drive")]
    facts = {2.7, 3.4, 903, 523, 1_150_000, 100_000, 3.8, 3.0, 60, 0}
    print("--- garage")
    asked = write(one, cars=near)
    about = [q for q in asked if "P1" in q.question or "M4" in q.question]
    quoted = [float(n.replace(",", "")) for q in about
              for n in re.findall(r"\d[\d,]*\.?\d*", q.question)]
    # regression: an earlier rule let Claude add facts (a V8's "left side") instead of comparing
    results.append(("a question compares two of the cars in reach",
                    any(("P1" in q.question or "McLaren" in q.question)
                        and ("M4" in q.question or "BMW" in q.question) for q in about)))
    results.append(("every big or decimal number quoted is a real fact",
                    all(n in facts for n in quoted if n >= 100 or n != int(n))))
    results.append(("the locked car never comes up", all("Jesko" not in q.question for q in asked)))
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
