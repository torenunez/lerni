# What People Need To Do

Lerni Explore is a small car-themed science lesson for a 7–9 year old, built to
run on one family's own computer. Most of it is software. Some of it isn't —
somebody has to read the lesson and decide it's accurate, age-appropriate, and
okay to show a kid.

**This page is that list.** It's for the educator and the parents, not for
programmers. If you're here to write code, skip to
[For developers](#for-developers) at the bottom.

---

## Right now

### The child does nothing yet

There's nothing to show them. The lesson exists but hasn't been reviewed, and
the software deliberately refuses to display unreviewed material. When it's
ready, a grown-up will sit with them the whole time — that's a design decision,
not a temporary limitation.

If your kid is asking to try it: that's the right instinct, and the honest
answer is "not yet, some grown-ups still have to check it."

### The educator has one job: read the lesson and say whether it's right

The whole lesson is about one idea: **a car's "0–60 time" tells you how many
seconds something took — it is not the same thing as acceleration.** A lot of
car writing gets this wrong, which is exactly why it's a good thing to teach.

Open **[the review sheet](./runbooks/chain-1-source-review.md)**. It lists the
four claims the lesson makes, side by side with what the NASA page they cite
actually says. Your job is to read four short quotes and say whether they hold up.

**One thing genuinely needs your judgment.** The lesson says "a 0–60 result
reports elapsed time" and cites a NASA physics page. That page is solid on
acceleration — but it never mentions cars at all. So: is it fair to cite it for
a claim about how car specs are written? Or should we find a second source? The
review sheet explains the tradeoff. There's no obviously right answer, which is
why a person has to decide.

### Parents have two jobs

**Read it as a parent, not as a physicist.** Is the tone right for a 7–9 year
old? Does the picture help or confuse? Is the wording something you'd be happy
to have your kid read? You're checking age fit, and separately looking at the
diagram and its text description for anyone who can't see it well.

**Then decide, explicitly, that this specific lesson is okay for your kid.**
That's a separate step from "it's accurate" and "it reads well." It's yours.

### Anyone can start: notes on what your kid actually likes about cars

No form to fill in yet — the template doesn't exist. Just jot things down as you
notice them. Which cars do they point at? What do they ask about? Do they care
about speed, or noise, or how something is built? This is what later lessons get
shaped around.

**Please don't write down:** their name or initials, birthday, school, where you
live, contact details, anything a doctor or teacher said about them, or their
exact words quoted back. A short paraphrase is plenty — "keeps asking why some
cars sound different" is more useful than a transcript anyway.

---

## How the sign-off works

Four separate people-checks, each a different question:

| Check | Question | Who |
|---|---|---|
| Accuracy | Is the science right, and does the source back it? | Educator, or anyone comfortable with physics |
| Age fit | Does this read well for a 7–9 year old? | Parent or educator |
| The picture | Does the diagram work, including its written description? | Parent or educator |
| Permission | Is this okay for *my* kid? | Parent |

All four have to happen before the child sees anything.

**A few things worth knowing about how this is recorded:**

Each sign-off gets written down with your *role* (like "parent" or "teacher")
and the real date — never your name. It's also tied to a fingerprint of the exact
wording you looked at. If anyone edits a single word of the lesson afterward, the
fingerprint stops matching and the software refuses to show it until someone
reviews the new version. That's the point: you're approving *specific words*, not
the lesson in general.

The flip side is that fixing a typo means asking for a fresh look. Slightly
annoying, and worth it.

**Nothing here is ever filled in automatically.** No AI, no script, no shortcut
writes a sign-off. If a check is blocking things, the only way through it is for
a person to actually do it.

---

## Already settled

| When | What | Where it landed |
|---|---|---|
| 2026-08-23 | Explore is the active project; the old Study tool is in maintenance only | `docs/mission.md` |
| 2026-08-23 | Interest-mapping and suggestions come *after* the first real session, not before | Sequenced in the master plan |
| 2026-08-23 | Developer tooling set up and working | — |
| 2026-08-23 | Checked the NASA source is still online and says what we thought | [Review sheet](./runbooks/chain-1-source-review.md) — this only confirms the page loads. It is **not** the accuracy check. |

Finished items stay on this page. Knowing a review happened, and when, is the
whole value of having done it.

---

## Coming later

Rough order, so nothing is a surprise. Don't act on these yet.

**Where things get stored.** Pick a folder on the family computer for the
lesson's records. It should be somewhere private and *not* inside iCloud,
Dropbox, or Google Drive — otherwise copies quietly spread to places we can't
clean up later.

**What gets kept, and for how long.** Whether to record anything about sessions
at all, and if so for how many days. Also: what "delete everything" can and can't
actually reach. It clears what the app manages. It can't reach your Time Machine
backups or a cloud sync you set up years ago, and we'd rather say so than imply
otherwise.

**Trying it yourself first.** A grown-up opens the lesson and clicks through it
before any child does. Also deciding whether read-aloud is on, and checking
whether your browser's speech feature runs on your machine or sends audio
somewhere — browsers differ, and it's worth actually checking rather than
assuming.

**Talking instead of typing.** Optional, and it has a real catch: your child's
raw voice reaches the transcription service *before* anything gets filtered.
Both parents need to understand that specifically and agree to it. Typing always
works and always stays local; this is genuinely optional.

**Whether to bring in an AI tutor at all.** Also optional. The lesson works
completely without one — a person wrote every word it can say. If you do want
one, that's when accounts, terms of service, data retention, and billing limits
come up, and there's [a full checklist](./runbooks/manual-setup.md) for it.
Until then: **no accounts, no API keys, no subscriptions, nothing to sign up for.**

**The go/no-go before the first real session.** Both parents confirm they
understand and agree to exactly what's enabled. One parent stays in the room and
can stop it at any moment. Everything is reviewed and everything is written down.

**After the first session.** Only then does the wider project start — mapping
your kid's interests to what's worth learning next, suggesting lessons, and so
on. That order is deliberate. Building a recommendation engine before knowing
whether one lesson holds a kid's attention would be building on a guess.

---

## For developers

Sourced from the `## Manual prerequisites` blocks across
[`prs/`](./prs/). The runbooks say *how*; this file tracks *whether*.

| Gate | Blocking items |
|---|---|
| PR-02 | 4 lesson attestations (`science`, `child_content`, `visual_accessibility`, `parent_approval`), all pinning the same `reviewed_payload_sha256` |
| PR-03 | Private runtime root outside the repo; helper Python qualified; fallback-only vs. plugin decision |
| PR-05 | Telemetry on/off; retention 1–3650 days or manual; paths private and non-synced; managed-wipe scope reviewed |
| PR-06 | Gradio version qualified; dedicated browser profile; browser speech routing confirmed; readiness review |
| PR-07 | Typed-only / local STT / external STT; both-parent acknowledgement that raw audio precedes redaction; mic permission scoped to local origin |
| PR-07A | Pilot level chosen; per-service terms/retention/logging/training/quota/billing/MFA/revocation; credential as an opaque reference only — never a literal in TOML, Git, IPC, telemetry, logs, or sheets |
| PR-08 | Attestations and hashes complete; export/delete/managed-wipe exercised with synthetic data; browser canaries; readiness digest acknowledged; both-parent consent |
| PR-09 | Local CSV vs. private Google Sheets (no Google API either way); reviewers lined up for the 25-attestation gate |
| PR-10 | Bundle carries real dates, source review, asset hash, 25 active attestations; both parents review generated diff and hashes |
| PR-11 | Parent scope and allowed nudge kinds; readiness attested only from actual observation, else `unknown` |

Two invariants hold throughout:

1. **No child-facing session before PR-08's pilot gate.** PR-06's UI is a
   parent/developer preview, not a pilot.
2. **No agent records an attestation, review date, or content hash.** Tooling may
   prepare evidence; only a human writes the verdict. Fabricating one violates
   Standing Rule 3.

Nothing in PRs 01–08 requires a service account or credential. See
[`runbooks/manual-setup.md`](./runbooks/manual-setup.md).
