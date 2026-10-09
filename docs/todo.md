# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release; the admin's build work is the running list of [upcoming PRs](#upcoming-prs). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Think of 2–3 things you'd like the supervised student to explore (with a note each on what you have in mind). You'll add them on the Maps tab once step 7 lands, or upload your notes once step 8 does.

### Later: Release 1 MVP

- [ ] Once step 7 lands: talk with Lerni yourself for a few days and watch your own map; say what's confusing in Feedback (step 8) or to the admin.
- [ ] Once step 9 lands: try the conversation with the supervised-student voice, then sit beside the supervised student for a short first conversation. Keep notes private, or put them in Feedback.

## Admin

### Upcoming PRs

The running list of what ships next, in order. Design: [specs/04-interest-map.md](../plans/specs/04-interest-map.md); step details: [Release 1 plan](../plans/release-1-mvp.md#to-build).

How PRs are split:

- **One unit per PR:** one build step (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, in-app guide, todo, and progress for what it ships.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **When a PR merges:** delete its row and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

| # | PR | Branch | Ships | Done when | Status |
|---|---|---|---|---|---|
| 1 | Step 7: the interest map | `feat/interest-map` | `interests.py` and its store; the tagger; the steering prompt; My map and Maps (SVG picture, goals list); old tabs and the Topic picker removed | The admin sees their interests on their map sized by time, adds a nudge, and sees a bridge | Not started |
| 2 | Step 8: upload and feedback | `feat/upload-and-feedback` | Upload proposes interests and goals, for educators and independent students; the Feedback box; `lerni feedback`; upload evals | The educator uploads notes and adds goals; the admin sees feedback summarized | Not started |
| 3 | Step 9: the supervised conversation | `feat/supervised-conversation` | The supervised student's full-screen conversation; the supervised persona and rules; their map grows | The supervised student talks with Lerni, the educator beside them, and the map grows | Not started |
| 4 | Step 10: remove the old activity path | `chore/remove-activities` | Plans, the old import, catalog, engine, lessons, seed, the index script, and their tests and docs | Tests pass; the code manifest matches | Not started |

After these, Release 1 needs sessions, not code: the educator goals, rehearses, and sits beside the supervised student (Educator and Student tasks above and below).

### Ask Lerni: deferred review findings

- [ ] Stop and New conversation end the answer on screen, but the Claude call can run on for up to 60 seconds; pass the cancel through to the adapter.
- [ ] Before the supervised conversation: send real alternating turns instead of one "Them/You" transcript, so earlier answers can't be faked.
- [ ] Try Ask on the iPad and a phone with the keyboard open; then a VoiceOver and keyboard-only pass.
- [ ] Maybe: a daily cap per student once others use it.
- [ ] Before anyone outside the family uses Ask: a short notice of where messages go and that answers can be wrong.

### Later: Release 2 Remembering

- [ ] Personal personas: Lerni learns what each student likes over time (topics, examples, answer length), starting from the persona for their kind; visible to the student, and to the educator for a supervised student.
- [ ] Write `plans/release-2-remembering.md`, starting with mapping each activity revision to the concepts it teaches.

### Later: Release 3 Voice

- [ ] Plan the conversation agent with tools (reading the plan, checking the allowlist, giving hints), and grow its evals from the import evals.
- [ ] Before anyone outside the household uses the app: replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).

- [ ] Before choosing speech or model services, check each one's data retention for a student's audio and text, and get the educator's agreement.

### Accounts: deferred review findings (family scale; harden before anyone else uses it)

- [ ] Before the educator's Stop (supervised path): a flood of sign-ins mustn't stall signed-in pages. Run the password check off the request threads with a small limit.
- [ ] Small: a non-ASCII cookie gives a 500; an archived account is detectable by timing; `/signin` has no Origin check and `/signout` is a GET; no upload size limit; the data folder is created 0755; a password change doesn't sign out other devices.
- [ ] Tests: the role check on each educator handler, cookie expiry, and a supervised cookie calling an educator event over HTTP.

### Admin tool maintenance

- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Release 1 MVP

- [ ] Independent student (the admin first): once step 8 lands, do your own activity end to end on your own device; note what's confusing.
- [ ] Supervised student: try the MVP with the educator beside them. They can say no or stop at any time.
