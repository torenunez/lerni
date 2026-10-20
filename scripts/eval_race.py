"""Race question evals: real Claude calls, run by hand when the race instructions or model change.

    .venv/bin/python scripts/eval_race.py

Uses the admin's Claude account. Add one case for each problem seen.
"""

from datetime import date

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.concepts import normalize
from lerni.student.interests import InterestMap, add_goal, add_interest, remove
from lerni.student.race import QUIZ_SYSTEM, check_questions, quiz_input


def write(m: InterestMap, supervised: bool = True, before: list | None = None) -> list:
    recent = [q.concept for q in before or []]
    raw = ClaudeCodeQuizzer().write(QUIZ_SYSTEM, quiz_input(m, date.today(), supervised, recent))
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
    ]
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
