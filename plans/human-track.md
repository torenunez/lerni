# What People Need To Do

Lerni turns something a child already cares about into a short, adult-supervised
learning activity. Most of it is software. But people decide what is worth
teaching, whether it is accurate and suitable, and whether a child tries it.
That's this list.

Programmers: skip to [For developers](#for-developers).

---

## Now — educator and parent

You don't have to wait for the app. Start here, in this order:

1. **Pick a starting interest and one concrete goal.** Something the child
   actually cares about right now. Cars are just one example; music, cooking,
   plants, or building work the same way.
2. **Sketch three to five activities** with the
   [path templates](../curation/templates/educator-paths-v1/README.md). Each
   activity needs a target idea, an order number, the teaching move that leads to
   it, and a goal. Look at the [six example paths](../curation/examples/educator-paths-v1-draft/README.md)
   for shape — they are drafts, not approved lessons.
3. **Prepare only the first activity** in full: opening question, what you'll do,
   how you'll check understanding, what you hope to see, materials (or `none`).
4. **Review it for real.** Educator and parent both read the exact wording and
   materials: accurate? clear? right for this child? Only then mark it reviewed,
   with your role and the actual date.
5. **Optional: try it** as a short walkthrough (below). No app needed.
6. **Revise one thing** based on what you saw, then pick the next activity.

**The child does not use the app yet.** It isn't built. A walkthrough with a
prepared, reviewed activity does not need it.

**Separately, if you want the existing car lesson:** the educator can check its
science with [the review sheet](./runbooks/chain-1-source-review.md). One claim
needs real judgment — the lesson calls a "0–60 time" elapsed time and cites a NASA
physics page that never mentions cars. That lesson only matters once the app
exists; it is not required for a walkthrough.

> Never write in any curriculum file: name, initials, birthday, school, address,
> contact details, anything a doctor or teacher said, or the child's exact words.
> What a particular child liked or did is a private observation — keep it in a
> separate private log, not in the repository.

---

## A short walkthrough (optional, no app)

**Prepare.** One activity, fully written and reviewed as above. Have materials
ready and a way to answer by speaking, pointing, drawing, or showing — no typing
needed. Agree who leads and who watches. A parent is present throughout.

**Ask, don't assume.** Offer it in one sentence and let the child say no. Say
that stopping is fine.

**Keep it short.** About 5–10 minutes. Stop earlier if they want to, lose
interest, or seem uncomfortable. Finishing is not the goal.

**Check gently.** Ask the prepared question. If they pick an answer, ask why or
ask them to show you. If you gave a hint, note that — a hinted answer is not the
same as an independent one.

**Afterwards, write brief private notes** — not a transcript. Useful categories:
interest, understanding, wording, activity, accessibility, willingness, and later
recall. Keep what happened separate from what you think it means. Don't copy the
hoped-for result into the notes; a missing answer is not zero understanding.

**Revise one thing** the notes justify. Bump the activity's revision number and
get a fresh review if the wording changed.

Walkthrough notes stay private. They never go into the curriculum tables or this
repository.

---

## The four sign-offs — packaged app lessons only

These apply to a lesson packaged for the app (today: the Chain-1 car lesson).
A walkthrough activity needs the real review described above, not these.

| Check | Question | Who |
|---|---|---|
| Accuracy | Is the science right, and does the source back it? | Educator |
| Age fit | Does this read well for a 7–9 year old? | Parent or educator |
| The picture | Does the diagram work, including its text description? | Parent or educator |
| Permission | Is this okay for *my* kid? | Parent |

All four before the child sees that lesson in the app. They are recorded in the
lesson's TOML file (`review.attestations`), not in a spreadsheet — see the
[review sheet](./runbooks/chain-1-source-review.md).

Each is recorded with your **role** and the date — never your name — and tied to
a fingerprint of the exact wording you read. Edit one word later and it stops
matching, so it goes back for review. You're approving specific words, not the
lesson in general. Fixing a typo costs a fresh look; that's the tradeoff.

**Nothing here is ever filled in automatically.** No AI or script writes a
sign-off. The only way past a check is for a person to do it.

---

## Settled

| When | What |
|---|---|
| 2026-08-23 | Explore is the active project; the old Study tool is maintenance-only |
| 2026-08-23 | Interest-mapping and suggestions come *after* the first real session |
| 2026-08-23 | Developer tooling working |
| 2026-08-23 | NASA source confirmed online — page loads, **not** the accuracy check |
| 2026-09-25 | Revised direction adopted in the docs: educator path authoring and a reviewed walkthrough can start now, alongside development; suggestions still come later. A planning decision, not a review |

Finished items stay here. Knowing a review happened, and when, is the point.

---

## Later

Rough order. Don't act on these yet.

- **Where things get stored** — a private folder, *not* iCloud/Dropbox/Drive, or
  copies spread where we can't clean them up.
- **What's kept and for how long** — including what "delete everything" can't
  reach. It won't touch your Time Machine backups or an old cloud sync.
- **A grown-up tries it first**, before any child. Also: does your browser's
  read-aloud run locally or send audio out? Worth checking, not assuming.
- **Talking instead of typing** — optional, with a real catch: raw voice reaches
  the transcription service *before* any filtering. Both parents must agree to
  that specifically. Typing always works and stays local.
- **Whether to use an AI tutor at all** — also optional. A person wrote every
  word the lesson can say. Accounts, terms, and billing only matter if you say
  yes ([checklist](./runbooks/manual-setup.md)). Until then: nothing to sign up for.
- **Go/no-go before the first app session** — both parents agree to exactly what's
  enabled; one stays in the room and can stop it.
- **After that**, the wider project starts. Building a recommendation engine
  before knowing whether one lesson holds a kid's attention would be a guess.

---

## For developers

From the `## Manual prerequisites` blocks in [`prs/`](./prs/). Runbooks say
*how*; this file tracks *whether*.

| Gate | Blocking |
|---|---|
| M1 | None — templates, examples, and checker are developer work; educator usability feedback welcome |
| M2 | Real educator and parent review of the selected activity before any walkthrough; observations kept private |
| PR-02 | 4 attestations (`science`, `child_content`, `visual_accessibility`, `parent_approval`) pinning one `reviewed_payload_sha256` |
| PR-03 | Runtime root outside repo; helper Python qualified; fallback-only vs. plugin |
| PR-05 | Telemetry on/off; retention 1–3650d or manual; paths private and non-synced; wipe scope reviewed |
| PR-06 | Gradio version; dedicated browser profile; speech routing confirmed; readiness review |
| PR-07 | Typed-only / local / external STT; both-parent ack that raw audio precedes redaction; mic scoped to local origin |
| PR-07A | Pilot level; per-service terms/retention/logging/training/quota/billing/MFA/revocation; credentials as opaque refs only |
| PR-08 | Attestations and hashes; export/delete/wipe exercised synthetically; browser canaries; readiness digest; both-parent consent |
| PR-09 | Strict import only (the drafting checker shipped at M1): local CSV vs. private Sheets (no Google API either way); an agreed `educator-paths-v1` delivery mapping; reviewers for the legacy 25-attestation gate |
| PR-10 | Real dates, source review, asset hash, 25 active attestations; both parents review generated diff |
| PR-11 | Parent scope and nudge kinds; readiness only from observation, else `unknown` |

1. **No child uses the app before its technical gate** (PR-08, reduced to the
   M3 slice once its checks are specified), an adult rehearsal, and parent
   authorization. PR-06's UI is a parent/developer preview. A genuinely reviewed
   educator-led walkthrough without the app is not blocked by this.
2. **No agent records an attestation, date, or hash.** Tooling prepares evidence;
   humans write verdicts. Fabricating one violates Standing Rule 3.

Nothing in PRs 01–08 needs a service account or credential.
