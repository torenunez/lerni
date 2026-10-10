# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release; the admin's build work is the running list of [upcoming PRs](#upcoming-prs). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Think of 2–3 things you'd like the supervised student to explore (with a note each on what you have in mind). You'll add them on the Maps tab, or upload your notes.

### Later: Release 1 MVP

- [ ] Talk with Lerni yourself for a few days and watch your own map; say what's confusing in Feedback or to the admin.
- [ ] Try the conversation with the supervised-student voice, then sit beside the supervised student for a short first conversation. Keep notes private, or put them in Feedback.

## Admin

- [ ] Install the home server's certificate on the iPad and phones ([admin reference: HTTPS](reference/admin.md#https-for-voice), step 3), sign in again at the `https://` address, and replace the iPad's home-screen icon. (The server side is done.)
- [ ] Optionally delete the old plan files on the home server (`~/.lerni/student/plans/`); nothing reads them since step 10.

### Upcoming PRs

The running list of what ships next, in order. Design: [specs/04-interest-map.md](../plans/specs/04-interest-map.md); step details: [Release 1 plan](../plans/release-1-mvp.md#to-build).

How PRs are split:

- **One unit per PR:** one build step (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, todo, and progress for what it ships.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **The shipped release stays in use:** each PR says in a Deploying section whether it's safe to put on the home server while the family uses it, how, and the caveats ([admin reference](reference/admin.md#updating-the-home-server)).
- **When a PR merges:** delete its row and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

Next: Release 2 step 1, HTTPS ([plan](../plans/release-2-step-1-https.md)); then step 2, voice ([spec 05](../plans/specs/05-voice.md)).

Release 1 now needs sessions, not code: the educator sets goals, rehearses, and sits beside the supervised student (Educator and Student tasks above and below).

### Ask Lerni: deferred review findings

- [ ] After the first supervised sessions, if useful: count redirects per session, and a "flag this reply" button for the adult nearby.

- [ ] Try Ask on the iPad and a phone with the keyboard open; then a VoiceOver and keyboard-only pass.
- [ ] Maybe: a daily cap per student once others use it.
- [ ] Before anyone outside the family uses Ask: a short notice of where messages go and that answers can be wrong.

### Interest map: later

- [ ] Small, from the step 9 review: Stop before the first word can be slow and a quick re-ask may say "Still answering"; the two chat panels allow 8 answers at once instead of 4 (share one concurrency id); a cancel can log "Exception ignored"; the new message isn't JSON like earlier turns; when Claude isn't set up the supervised screen greets over a disabled box; the guns redirect offered squirt guns (offer something unrelated).
- [ ] Small, from the step 8 review: cap how big a .docx may expand when read, and show a friendly message for a malformed one; a file-read error can hide its cause; no server-side check for real names in proposals; "Tick what to add" shows when every idea is already on the map; `lerni feedback done` can lose an entry saved at the same moment and finds entries by position; editing feedback after checking keeps the old summary; Claude pads goal notes with restatements.
- [ ] Small, from the step 7 review: at a full map a just-added interest can be dropped by the next one; the map block's 1,500-character cut can cut a line mid-word; top interests rank by all-time days rather than the last 30; a faded explained goal can be listed twice in the block; the Maps timer ticks on every page; an unreadable map file shows a Gradio error; `lerni logs` can fail if a purge runs mid-read.
- [ ] When a map outgrows the picture (more than 15 entries drawn): show more, for example by grouping or a focus on one entry and its links; the list below already has them all.

### Now: Release 2 Voice

- [ ] Before step 2: check the home server can run both helpers (about 2–4 cores and 2 GB for text-to-speech) and has the disk space.
- [ ] Try the voice with the students before deciding whether a hosted voice (Inworld, about $18 a month) is worth it; a hosted service means student audio leaves the house, so it needs the educator's agreement first.
- [ ] Before anyone outside the family uses the app: files in Gradio's cache (uploads, any voice audio) are reachable by URL to anyone signed in; serve them only to their owner, or keep none.
- [ ] Before anyone outside the household uses the app: replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).

### Later: Release 3 Remembering

- [ ] Personal personas: Lerni learns what each student likes over time (topics, examples, answer length), starting from the persona for their kind; visible to the student, and to the educator for a supervised student.
- [ ] Write `plans/release-3-remembering.md`, starting from the map: recall questions about goals the student once explained, tracking the last recall attempt apart from the last time a goal was discussed.

### Accounts: deferred review findings (family scale; harden before anyone else uses it)

- [ ] Before anyone outside the family uses the app: a flood of sign-ins mustn't stall signed-in pages. Run the password check off the request threads with a small limit.
- [ ] Small: two educators archiving each other leaves none (recover with `lerni student add`); password hashing runs inside the account write lock; a live session can guess its current password in My account without the sign-in delay; a non-ASCII cookie gives a 500; an archived account is detectable by timing; `/signin` has no Origin check and `/signout` is a GET; no upload size limit; the data folder is created 0755; a password change doesn't sign out other devices.
- [ ] Tests: the role check on each educator handler, cookie expiry, and a supervised cookie calling an educator event over HTTP.

### Admin tool maintenance

- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Release 1 MVP

- [ ] Independent student (the admin first): once step 7 lands, talk with Lerni over a few days on your own device, add a goal, and check the map matches what you talked about; note what's confusing.
- [ ] Supervised student: try the MVP with the educator beside them. They can say no or stop at any time.
