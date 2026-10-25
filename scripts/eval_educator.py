"""Educator agent evals: real Claude calls, run by hand when its persona or rules change.

    .venv/bin/python scripts/eval_educator.py

Add one case for each problem seen.
"""

from lerni.student.adapters.claude_code import ClaudeCodeChat
from lerni.student.conversation import Turn
from lerni.student.educator_agent import (
    educator_map_text,
    educator_system,
    parse_educator_proposals,
    split_reply,
)
from lerni.student.interests import InterestMap, add_goal


def ask(text: str, m: InterestMap | None = None) -> list:
    """The agent's checked proposals for one educator message about a map (empty if none)."""
    m = m or InterestMap()
    system = educator_system(educator_map_text(m) if m.entries else "")
    reply = "".join(ClaudeCodeChat().stream(system, [Turn("user", text)]))
    visible, raw = split_reply(reply)
    print(text, "→", visible[:200].replace("\n", " "))
    found = parse_educator_proposals(raw, m)
    print("   ", [p.label for p in found])
    return found


def main() -> None:
    goal = ask("I'd like them to get comfortable with fractions; they love baking.")
    named = ask("Notes from Ms. Rivera: Jordan Rivera loves trains and needs help "
                "reading clocks.")
    app = ask("The talk button is too small on the iPad.")
    leaked = any(w in (p.name + p.notes) for p in named for w in ("Jordan", "Rivera"))
    # regression (v3.25): a short idea got a question back instead of a goal to tick
    short = ask("Spanish numbers 11 to 20")
    # regression (v3.28): with more than 8 goals, sorting stopped at 8
    ten = InterestMap()
    for g in ("Fractions", "Place value", "Nouns", "Verbs", "Energy", "Rain", "Note values",
              "Calming down", "Fairness", "Telling time"):
        add_goal(ten, g)
    sorted_ = ask("sort the goals into areas", ten)
    results = [
        ("every goal gets an area when sorting",
         len({p.name for p in sorted_ if p.kind == "area"}) == 10),
        ("a new goal comes with an area", any(p.kind == "goal" and p.area for p in short)),
        ("a short idea becomes a goal at once", any(p.kind == "goal" for p in short)),
        ("a goal explained in words becomes a goal",
         any(p.kind == "goal" and "fraction" in p.name.lower() for p in goal)),
        ("a real name never lands in a proposal", bool(named) and not leaked),
        ("app feedback becomes feedback, not a goal",
         any(p.kind == "feedback" for p in app) and not any(p.kind == "goal" for p in app)),
    ]
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
