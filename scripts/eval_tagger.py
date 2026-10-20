"""Tagger evals: real Claude calls, run by hand when the tagger's instructions or model change.

    .venv/bin/python scripts/eval_tagger.py

Uses the admin's Claude account. Add one case for each mismatch seen in `lerni logs`.
"""

from datetime import date

from lerni.student.adapters.claude_code import ClaudeCodeTagger
from lerni.student.interests import InterestMap, add_goal, apply_tags, parents, parse_tags
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
    m = InterestMap()
    m.entries.append(m.new_entry("sharks", "interest"))
    m = run(m, "", "I saw a great white shark at the aquarium! It was huge!",
            "Great whites are the biggest predatory fish. What did it do?")
    white, sharks = m.find("great white shark") or m.find("great white"), m.find("sharks")
    ok = white is not None and parents(m, white.id) == [sharks.id]
    results.append(("great white is a kind of sharks", ok))

    m = InterestMap()
    for name in ("cars", "engines"):
        m.entries.append(m.new_entry(name, "interest"))
    m = run(m, "", "How do car engines work?",
            "An engine burns fuel to push pistons that turn the wheels. Want to see how?")
    results.append(("an engine is part of a car, not a kind", not parents(m, m.find("engines").id)))
    # 6–7. a real answer to Lerni's question is "right"; emojis earn nothing
    asked = "What do you think makes a car speed up: the engine pushing harder, or the paint?"
    for answer, want in (("the engine pushes it harder", "right"), ("🤷😂", None)):
        raw = ClaudeCodeTagger().tag(TAGGER_SYSTEM, tagger_input(InterestMap(), asked, answer,
                                                                 "Nice! Engines push."))
        print(answer, "→", raw)
        results.append((f"{answer!r} answered {want}", parse_tags(raw).answered == want))
    # 8–9. the very same thing joins its item; something related doesn't (v3.12)
    m = InterestMap()
    m.entries.append(m.new_entry("Tyrannosaurus", "interest"))
    m = run(m, "", "The T-Rex is my favorite!", "The T-Rex had tiny arms and huge teeth!")
    results.append(("T-Rex joins Tyrannosaurus", len(m.entries) == 1
                    and m.find("T-Rex") is m.find("Tyrannosaurus")))
    m = InterestMap()
    m.entries.append(m.new_entry("volcano", "interest"))
    m = run(m, "", "What is lava made of?", "Lava is melted rock that comes out of a volcano.")
    results.append(("lava stays its own thing", m.find("lava") is not m.find("volcano")))
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
