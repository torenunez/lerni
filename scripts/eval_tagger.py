"""Tagger evals: real Claude calls, run by hand when the tagger's instructions or model change.

    .venv/bin/python scripts/eval_tagger.py

Uses the admin's Claude account. Add one case for each mismatch seen in `lerni logs`.
"""

from datetime import date

from lerni.student.adapters.claude_code import ClaudeCodeTagger
from lerni.student.interests import InterestMap, add_goal, apply_tags, parse_tags
from lerni.student.tagging import TAGGER_SYSTEM, tagger_input

TODAY = date.today()


def run(m: InterestMap, previous: str, question: str, answer: str) -> InterestMap:
    raw = ClaudeCodeTagger().tag(TAGGER_SYSTEM, tagger_input(m, previous, question, answer))
    apply_tags(m, parse_tags(raw), question, TODAY)
    print(question, "→", raw)
    return m


def main() -> None:
    results = []
    # 1. a plain interest is tagged in the student's words; a dislike adds nothing
    m = run(InterestMap(), "", "I love cars! But I don't like sharks.",
            "Cars are great! Which kind?")
    ok = m.find("cars") is not None and m.find("sharks") is None
    results.append(("cars tagged, sharks not", ok))
    # 2. a bridge from an interest to a goal is seen
    m = InterestMap()
    m.entries.append(m.new_entry("cars", "interest"))
    add_goal(m, "Fractions")
    m = run(m, "", "How fast is a race car?",
            "Very fast! If a car does half a lap, that's a fraction: one of two equal parts. "
            "What's half of a 2-mile lap?")
    results.append(("bridge cars → Fractions", any(k.kind == "bridge" for k in m.links)))
    # 3. something personal is skipped
    m = run(InterestMap(), "", "My friend Jake lives on Maple Street, we play soccer there",
            "Soccer is fun! What position do you play?")
    results.append(("personal skipped", m.entries == []))
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
