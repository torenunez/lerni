"""Morning plan evals (v3.44): real Claude calls, run by hand when its instructions change.

    .venv/bin/python scripts/eval_morning.py   # 2 small-model calls, with the local embedder

The second run plans from the night job's shortlist (v4.16), ranked by the local embedder.

Uses the admin's Claude account and a made-up map (never a real one). Add one case for each
problem seen.
"""

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from lerni.student.adapters.claude_code import ClaudeCodeQuizzer
from lerni.student.adapters.llama_embed import embedder_from_env
from lerni.student.concepts import ConceptStore, normalize
from lerni.student.interests import Link, MapStore, add_goal, add_interest, remove
from lerni.student.morning import SuggestionStore, run_morning


def shortlisted_run(root: Path, maps: MapStore, concepts: ConceptStore, today: date) -> list:
    """The same map planned again from the shortlist, in a store of its own (v4.16)."""
    embedder, why = embedder_from_env()
    if embedder is None:  # the eval needs the home server's embedding model
        print(f"[shortlist] skipped: {why}")
        return []
    store = SuggestionStore(root / "shortlisted")
    run_morning("pat", ClaudeCodeQuizzer(), maps, concepts, store, today, embedder=embedder)
    made = store.get("pat")["connections"]
    for c in made:  # rank and similarity beside each, to read by eye
        print(f"[shortlisted #{c.get('rank')} {c.get('similarity')}] {c['interest']} → "
              f"{c['goal']}: {c['hook']}")
    return made


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
        shortlisted = shortlisted_run(root, maps, concepts, today)  # v4.16
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
            # v4.16: with a shortlist, every connection is on it, ranked, and has a hook
            ("the shortlisted plan proposes only shortlisted pairs, each ranked",
             bool(shortlisted) and all("rank" in c for c in shortlisted)),
            ("its hooks read as teaching angles (printed to read by eye), never empty",
             bool(shortlisted) and all(len(c["hook"]) > 10 for c in shortlisted)),
        ]
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
