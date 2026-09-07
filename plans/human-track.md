# What People Need To Do

A small car-themed science lesson for a 7–9 year old, running on one family's
computer. Most of it is software. But somebody has to read the lesson and decide
it's accurate, age-appropriate, and okay to show a kid. That's this list.

Programmers: skip to [For developers](#for-developers).

---

## Now

**The child does nothing yet.** The lesson exists but hasn't been reviewed, and
the software refuses to show unreviewed material. When it's ready, a grown-up
sits with them the whole time.

**Educator — check the science.** Open [the review sheet](./runbooks/chain-1-source-review.md).
It puts the lesson's four claims next to what the NASA page they cite actually
says. Read four quotes, say whether they hold up.

One needs real judgment: the lesson says a "0–60 time" is elapsed time and cites
a NASA physics page — but that page never mentions cars. Fair citation, or find a
second source? The sheet lays out both.

**Parents — two calls.** Does it read well for a 7–9 year old, and does the
picture help? Then, separately: is this okay for *my* kid?

**Anyone — note what your kid likes about cars.** No form yet, just jot things
down. Which cars do they point at? Speed, noise, how it's built?

> Don't write down: name, initials, birthday, school, address, contact details,
> anything a doctor or teacher said, or their exact words. A paraphrase is more
> useful anyway.

---

## The four sign-offs

| Check | Question | Who |
|---|---|---|
| Accuracy | Is the science right, and does the source back it? | Educator |
| Age fit | Does this read well for a 7–9 year old? | Parent or educator |
| The picture | Does the diagram work, including its text description? | Parent or educator |
| Permission | Is this okay for *my* kid? | Parent |

All four before the child sees anything.

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
- **Go/no-go before the first session** — both parents agree to exactly what's
  enabled; one stays in the room and can stop it.
- **After that**, the wider project starts. Building a recommendation engine
  before knowing whether one lesson holds a kid's attention would be a guess.

---

## For developers

From the `## Manual prerequisites` blocks in [`prs/`](./prs/). Runbooks say
*how*; this file tracks *whether*.

| Gate | Blocking |
|---|---|
| PR-02 | 4 attestations (`science`, `child_content`, `visual_accessibility`, `parent_approval`) pinning one `reviewed_payload_sha256` |
| PR-03 | Runtime root outside repo; helper Python qualified; fallback-only vs. plugin |
| PR-05 | Telemetry on/off; retention 1–3650d or manual; paths private and non-synced; wipe scope reviewed |
| PR-06 | Gradio version; dedicated browser profile; speech routing confirmed; readiness review |
| PR-07 | Typed-only / local / external STT; both-parent ack that raw audio precedes redaction; mic scoped to local origin |
| PR-07A | Pilot level; per-service terms/retention/logging/training/quota/billing/MFA/revocation; credentials as opaque refs only |
| PR-08 | Attestations and hashes; export/delete/wipe exercised synthetically; browser canaries; readiness digest; both-parent consent |
| PR-09 | Local CSV vs. private Sheets (no Google API either way); reviewers for the 25-attestation gate |
| PR-10 | Real dates, source review, asset hash, 25 active attestations; both parents review generated diff |
| PR-11 | Parent scope and nudge kinds; readiness only from observation, else `unknown` |

1. **No child-facing session before PR-08's pilot gate.** PR-06's UI is a
   parent/developer preview.
2. **No agent records an attestation, date, or hash.** Tooling prepares evidence;
   humans write verdicts. Fabricating one violates Standing Rule 3.

Nothing in PRs 01–08 needs a service account or credential.
