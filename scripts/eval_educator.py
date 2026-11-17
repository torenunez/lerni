"""Educator agent evals: real Claude calls, run by hand when its persona or rules change.

    .venv/bin/python scripts/eval_educator.py
    .venv/bin/python scripts/eval_educator.py questions   # only Tell Lerni on questions (v4.9)

Add one case for each problem seen.
"""

import re
import sys
from datetime import date

from lerni.student.adapters.claude_code import ClaudeCodeChat, ClaudeCodeQuizzer
from lerni.student.conversation import Turn
from lerni.student.educator_agent import (
    check_keys,
    educator_map_text,
    educator_system,
    parse_educator_proposals,
    split_reply,
)
from lerni.student.interests import InterestMap, add_goal
from lerni.student.race import QUIZ_SYSTEM, check_questions, quiz_input

REPLIES: list[str] = []  # every visible reply, for the vocabulary check


def ask(text: str, m: InterestMap | None = None, levels: dict | None = None) -> list:
    """The agent's checked proposals for one educator message about a map (empty if none)."""
    m = m or InterestMap()
    system = educator_system(educator_map_text(m, levels) if m.entries else "")
    reply = "".join(ClaudeCodeChat().stream(system, [Turn("user", text)]))
    visible, raw = split_reply(reply)
    REPLIES.append(visible)  # what the educator reads on screen
    print(text, "→", visible[:200].replace("\n", " "))
    found = parse_educator_proposals(raw, m, levels)
    print("   ", [p.label for p in found])
    return found


def questions() -> list[tuple[str, bool]]:
    """Tell Lerni about questions (v4.9): 2 chat calls, 1 blind check, 1 race write."""
    m = InterestMap()
    length, clock = add_goal(m, "Measuring length"), add_goal(m, "Telling time")
    levels = {length.id: 3, clock.id: 3}
    easy = ask("These are too easy. Use cm, not inches.", m, levels)
    sheet = ask("Telling time worksheet: short hand on 3 and long hand on 12 is 3:00. Short hand "
                "halfway past 6 and long hand on 6 is 6:30.", m, levels)
    keys = check_keys(ClaudeCodeQuizzer(), [p for p in sheet if p.kind == "key"])
    print("    check:", [p.doubt or "agrees" for p in keys])
    notes = [("", p.notes) for p in easy if p.kind == "guidance"]  # as if ticked
    raw = ClaudeCodeQuizzer().write(QUIZ_SYSTEM, quiz_input(m, date.today(), True, levels=levels,
                                                            guidance=notes))
    written = [q.question + " " + " ".join(q.choices) for q in check_questions(raw, m)]
    return [
        ("'too easy' becomes a level change, not guidance",
         any(p.kind == "level" and p.step == 1 for p in easy)
         and not any(p.kind == "guidance" and "easy" in p.notes.lower() for p in easy)),
        ("'use cm' becomes a guidance note", bool(notes)),
        ("nothing about questions becomes a goal",
         not any(p.kind == "goal" for p in [*easy, *sheet])),
        ("a worksheet becomes two keys on its goal",
         [p.name for p in sheet if p.kind == "key"] == ["Telling time"] * 2),
        ("a race write follows the note (no inches)",
         bool(written) and not any(re.search(r"\binch", w, re.I) for w in written)),
    ]


def vocabulary() -> tuple[str, bool]:
    """Regression (v4.9): a reply said "wrong answers a child might believe" (rule 1)."""
    return ("replies say 'the student', never child or kid",
            not any(re.search(r"\b(child|children|kids?)\b", r, re.I) for r in REPLIES))


def main() -> None:
    if sys.argv[1:] == ["questions"]:
        for name, ok in [*questions(), vocabulary()]:
            print("PASS" if ok else "FAIL", name)
        return
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
        *questions(),
        vocabulary(),
    ]
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
