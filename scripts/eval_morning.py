"""Morning plan evals (v3.44): real Claude calls, run by hand when its instructions change.

    .venv/bin/python scripts/eval_morning.py

Uses the admin's Claude account and a made-up map (never a real one). Add one case for each
problem seen.
"""

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.concepts import ConceptStore, normalize
from lerni.student.interests import Link, MapStore, add_goal, add_interest, remove
from lerni.student.morning import SuggestionStore, run_morning


def main() -> None:
    today = date.today()
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        maps, concepts, store = MapStore(root), ConceptStore(root), SuggestionStore(root)
        made = {}

        def fill(m):
            made["Fractions"] = add_goal(m, "Fractions", "halves and quarters")
            made["Nouns"] = add_goal(m, "Nouns", "naming words")
            for name in ("trains", "baking", "dogs", "music", "volcanoes", "space"):
                made[name] = add_interest(m, name)
            remove(m, add_interest(m, "spiders").id)
            m.links.append(Link(made["trains"].id, made["Fractions"].id, "bridge", str(today)))

        maps.change("pat", fill)
        asked = [(made["Fractions"].id, "Fractions", f"fractions idea {n}") for n in range(12)]
        concepts.add("pat", asked, today - timedelta(days=5))  # running out: steps asked for
        run_morning("pat", ClaudeCodeQuizzer(), maps, concepts, store, today)
        data = store.get("pat")
        for c in data["connections"]:
            print(f"[connection] {c['interest']} → {c['goal']}: {c['hook']}")
        for g in data["goals"]:
            print(f"[goal] {g['goal']}: {g['notes']}")
        steps = data["steps"].get(made["Fractions"].id, {}).get("steps", [])
        print(f"[steps] {steps}")
        said = " ".join([*(c["hook"] for c in data["connections"]), *steps,
                         *(g["notes"] for g in data["goals"])]).casefold()
        results = [
            ("connections use map items, never trains for Fractions (bridged already)",
             len(data["connections"]) >= 3 and not any(
                 c["interest"] == "trains" and c["goal"] == "Fractions"
                 for c in data["connections"])),
            ("nothing names a set-aside", "spider" not in said),
            ("a running-out goal gets distinct steps within its notes",
             len(steps) >= 8 and len({normalize(s) for s in steps}) == len(steps)),
        ]
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
