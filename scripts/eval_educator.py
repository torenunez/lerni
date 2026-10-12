"""Educator agent evals: real Claude calls, run by hand when its persona or rules change.

    .venv/bin/python scripts/eval_educator.py

Add one case for each problem seen.
"""

from lerni.student.adapters.claude_code import ClaudeCodeChat
from lerni.student.conversation import Turn
from lerni.student.educator_agent import (
    educator_system,
    parse_educator_proposals,
    split_reply,
)
from lerni.student.interests import InterestMap


def ask(text: str) -> list:
    """The agent's checked proposals for one educator message about an empty map."""
    reply = "".join(ClaudeCodeChat().stream(educator_system(""), [Turn("user", text)]))
    visible, raw = split_reply(reply)
    print(text, "→", visible[:200].replace("\n", " "))
    found = parse_educator_proposals(raw, InterestMap())
    print("   ", [p.label for p in found])
    return found


def main() -> None:
    goal = ask("I'd like them to get comfortable with fractions; they love baking.")
    named = ask("Notes from Ms. Rivera: Mateo Rivera loves trains and needs help "
                "reading clocks.")
    app = ask("The talk button is too small on the iPad.")
    leaked = any(w in (p.name + p.notes) for p in named for w in ("Mateo", "Rivera"))
    results = [
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
