"""Area sorter evals: real Claude calls, run by hand when the area instructions or model change.

    .venv/bin/python scripts/eval_areas.py

Uses the admin's Claude account. Add one case for each problem seen.
"""

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.area_sorter import (
    AREA_SCHEMA,
    AREA_SYSTEM,
    AREA_TIMEOUT_SECONDS,
    area_input,
    parse_areas,
)
from lerni.student.interests import InterestMap, add_goal, set_area


def sort(m: InterestMap) -> dict[str, str]:
    """Goal name → Claude's area, for the goals with none."""
    todo = [e for e in m.entries if e.kind == "goal" and not e.area]
    raw = ClaudeCodeQuizzer().write(AREA_SYSTEM, area_input(m, todo), AREA_SCHEMA,
                                    AREA_TIMEOUT_SECONDS * 2)  # first calls start slowly
    names = {e.id: e.name for e in todo}
    got = {names[i]: a for i, a in parse_areas(raw, todo).items()}
    print(got)
    return got


def main() -> None:
    passed = 0
    m = InterestMap()  # school subjects go to the starters
    for name in ("Fractions", "Photosynthesis", "Nouns and verbs", "Note values"):
        add_goal(m, name)
    got = sort(m)
    ok = got == {"Fractions": "Math", "Photosynthesis": "Science",
                 "Nouns and verbs": "Language", "Note values": "Music"}
    print("starters:", "ok" if ok else "FAIL")
    passed += ok

    m = InterestMap()  # two goals that belong together share one new area
    for name in ("Dribbling a ball", "Passing to a teammate", "Place value"):
        add_goal(m, name)
    got = sort(m)
    sport = got.get("Dribbling a ball")
    ok = (sport == got.get("Passing to a teammate") and sport not in (None, "Math")
          and got.get("Place value") == "Math")
    print("new area shared:", "ok" if ok else "FAIL")
    passed += ok

    m = InterestMap()  # a family's own area is reused
    set_area(m, add_goal(m, "Chess openings").id, "Chess")
    add_goal(m, "Chess endgames")
    got = sort(m)
    ok = got.get("Chess endgames") == "Chess"
    print("own area reused:", "ok" if ok else "FAIL")
    passed += ok
    print(f"{passed} of 3 passed")


if __name__ == "__main__":
    main()
