"""Upload evals: real Claude calls, run by hand when the upload's instructions or model change.

    .venv/bin/python scripts/eval_upload.py

Uses the admin's Claude account. Add one case for each problem seen.
"""

from lerni.student.adapters.claude_code import ClaudeCodeUploader
from lerni.student.upload import extract_upload, parse_proposals, upload_system


def run(notes: str, own: bool) -> list[tuple[str, str]]:
    raw = ClaudeCodeUploader().propose(upload_system(own), extract_upload(notes))
    proposals, claude_notes = parse_proposals(raw)
    print(notes, "→", [(p.kind, p.name, p.notes) for p in proposals], claude_notes)
    return [(p.kind, p.name.casefold()) for p in proposals]


def main() -> None:
    results = []
    # 1. an educator's notes with a made-up name: interests and goals, and never the name
    got = run("Tomasz loves dinosaurs and soccer. I'd like him to practice telling time "
              "and halves; he lives on Birch Lane.", own=False)
    kinds = dict((name, kind) for kind, name in got)
    named = any("tomasz" in name or "birch" in name for _, name in got)
    results.append(("educator notes", kinds.get("dinosaurs") == "interest"
                    and any(k == "goal" for k in kinds.values()) and not named))
    # 2. a person's own notes: what they enjoy is an interest, what they practice a goal
    got = run("I enjoy jazz piano and hiking. I want to practice Spanish verbs.", own=True)
    ok = ("interest", "jazz piano") in got and any(k == "goal" and "spanish" in n for k, n in got)
    results.append(("own notes", ok))
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
