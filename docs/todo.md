# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by version; the admin's build work is the running list of [upcoming versions](#upcoming-versions). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each version: [roadmap](roadmap.md).

## Educator

### Now: Version 1 MVP

- [ ] Think of 2–3 things you'd like the supervised student to explore (with a note each on what you have in mind). Add them on MentalMaps (☰ → MentalMaps): type them into the list, or tell the chat, or attach your notes with 📎 and tick what to add.

- [ ] Before the first race (v3.1): check the goals on MentalMaps are what you'd like the race to practice, since its questions come from them; then sit with the supervised student for their first race.

### Later: Version 1 MVP

- [ ] Talk with Lerni yourself for a few days and watch your own MentalMap; tell the admin what's confusing, or mention it in the MentalMaps chat.
- [ ] Try the conversation with the supervised-student voice, then sit beside the supervised student for a short first conversation. Keep notes private, or mention them in the MentalMaps chat.

## Admin

### Now

- [ ] Say when to update production from v2.18 to v2.20 (it fixes the list that can come up blank on MentalMaps); then check on the iPhone and iPad: the ☰ menu, both MentalMap screens (tap and pinch the picture), the usage warning, and Hold to talk.
- [ ] Turn off extra usage (paid credits) on the Claude account Lerni uses (claude.ai → Settings → Usage), so Lerni can never spend credits; Lerni also rests if a call ever uses them.
- [ ] Pick Lerni's voice ([admin reference: Voice](reference/admin.md#voice)), try Hold to talk on the iPad, then with the supervised student and an adult nearby (Version 2 is done when their map grows from a spoken conversation).
- [ ] Optionally delete the old plan files on the home server (`~/.lerni/student/plans/`); nothing reads them any more.

### Upcoming versions

What ships next, in order, one PR each ([how versions work](roadmap.md#versions)):

1. **v3.2: points in the conversation, and Ask becomes Chat:** the tagger judges the student's answer to Lerni's last question (right, a real try, or nothing) and the server adds points, once per exchange, up to a daily cap; "⭐ +3" shows by the total; no multiple choice in the conversation.
2. **v3.3: voice that fails says so:** if `say` returns empty audio, startup prints `Voice (hold to talk): off` with the reason, instead of sending silence; the microphone is released if you let go before Safari asks; recording stops and sends at 30 seconds instead of dropping the end; a microphone failure switches to Type with a short note.
3. **v3.4: production keeps running on its own:** run production and development the same way, as macOS LaunchAgents in the desktop session (start at login, restart after a crash); check `say` works there first. Until then both run in Terminal windows, and production stops if that window or the Mac does.
4. **Version 4, remembering:** Bridge Trip (a trip along their map with recall stops) is its front door; its first PR writes the plan.

How PRs are split:

- **One unit per PR:** one change (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, todo, and progress for what it ships, and its version: the `vX.Y:` title and `version` in `pyproject.toml`.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **The shipped version stays in use:** each PR says in a Deploying section whether it's safe to put on the home server while the family uses it, how, and the caveats ([admin reference](reference/admin.md#updating-the-home-server)).
- **When a PR merges:** tag `main` with its version, delete its row, and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

Versions 1 and 2 also need sessions, not code: the educator sets goals, rehearses, and sits beside the supervised student (Educator and Student tasks above and below).

### Later

- [ ] Decide how long to keep conversation logs (7 days now; 20 days or longer is under consideration). Longer keeps more of the students' words on disk; it changes CLAUDE.md rule 6 and the PRDs.
- [ ] After a week of family use: compare each feature's Claude use (Ask, tagger, Upload, MentalMaps chat) and decide whether any can move to a cheaper model.
- [ ] Try the voice with the students before deciding whether a hosted voice (Inworld, about $18 a month) is worth it; a hosted service means student audio leaves the house, so it needs the educator's agreement first.
- [ ] MentalMaps chat: PDFs (its Claude call takes text only; Upload on My MentalMap still reads PDFs), and the same chat on My MentalMap once educators have used it.
- [ ] `feedback.summarize` is unused since v2.14 (the chat writes the note); remove it with its test, or use it for chat feedback.
- [ ] After the first supervised sessions, if useful: count redirects per session, and a "flag this reply" button for the adult nearby.
- [ ] Try Ask on the iPad and a phone with the keyboard open; then a VoiceOver and keyboard-only pass.

### Later: Version 3 Play and points

- [ ] Pit stop: fill a toy car's fuel gauge with quarters, then the same amount with eighths (fixed math, no Claude calls); the educator sketches the scene first.
- [ ] A private real-car pack: the admin picks licensed side-profile photos of the student's favorite cars (Wikimedia, Unsplash, Pexels); Claude removes backgrounds, aligns them, blurs badges, and lists them with prices in a private garage file on the home server (never in the repo), with credits.
- [ ] An educator "reset points", and Games for independent students.
- [ ] Other games: Beat builder (rhythm and fractions), Recipe mixer (ratios), Build and balance.
- [ ] Two weeks after v3.2: are Lerni's questions getting real answers, or are points just being hunted? Tune the points, or stop.

### Later: Version 4 Remembering

- [ ] Personal personas: Lerni learns what each student likes over time (topics, examples, answer length), starting from the persona for their kind; visible to the student, and to the educator for a supervised student.
- [ ] Write the Version 4 plan (`plans/v4.1-remembering.md`), starting from the MentalMap: recall questions about goals the student once explained, tracking the last recall attempt apart from the last time a goal was discussed.

### Before anyone outside the family uses the app

- [ ] Replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).
- [ ] Files in Gradio's cache (uploads, any voice audio) are reachable by URL to anyone signed in; serve them only to their owner, or keep none.
- [ ] A short notice of where messages go and that answers can be wrong.
- [ ] A flood of sign-ins mustn't stall signed-in pages: run the password check off the request threads with a small limit.
- [ ] Maybe a daily cap per student.

### Deferred review findings (small; family scale)

- [ ] **Ask:** Stop before the first word can be slow and a quick re-ask may say "Still answering"; the two chat panels allow 8 answers at once instead of 4 (share one concurrency id); a cancel can log "Exception ignored"; the new message isn't JSON like earlier turns; when Claude isn't set up the supervised screen greets over a disabled box; the guns redirect offered squirt guns (offer something unrelated).
- [ ] **Upload and feedback:** cap how big a .docx may expand when read, and show a friendly message for a malformed one; a file-read error can hide its cause; no server-side check for real names in proposals; "Tick what to add" shows when every idea is already on the map; `lerni feedback done` can lose an entry saved at the same moment and finds entries by position; editing feedback after checking keeps the old summary; Claude pads goal notes with restatements.
- [ ] **The map:** the map block's 1,500-character cut can cut a line mid-word; top interests rank by all-time days rather than the last 30; a faded explained goal can be listed twice in the block; the MentalMaps timer ticks on every page; an unreadable map file shows a Gradio error; `lerni logs` can fail if a purge runs mid-read.
- [ ] **Educator chat:** a proposal names its target, so an old one can change a newer item with the same name; Clear or a new student can be undone by a reply still arriving; 📎 notes are sent again every turn; removals are reported as "Added".
- [ ] **Tagging:** two quick answers' tags can land out of order, and a subject change counts against the newest bridge rather than the one in the answer before.
- [ ] **MentalMap list:** a redraw trusts the owner set by the last checked handler and doesn't re-check the viewer (every edit does).
- [ ] **Games:** an educator's race uses their own map, so they can't rehearse a student's questions; in dark mode the MentalMap picture's labels are hard to read.
- [ ] **Menu:** the closed drawer is still reachable by keyboard and VoiceOver.
- [ ] **Accounts:** two educators archiving each other leaves none (recover with `lerni student add`); password hashing runs inside the account write lock; a live session can guess its current password in My account without the sign-in delay; a non-ASCII cookie gives a 500; an archived account is detectable by timing; `/signin` has no Origin check and `/signout` is a GET; the data folder is created 0755; a password change doesn't sign out other devices.
- [ ] **Tests:** the role check on each educator handler, cookie expiry, and a supervised cookie calling an educator event over HTTP.

### Admin tool maintenance

- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Version 1 MVP

- [ ] Independent student (the admin first): talk with Lerni over a few days on your own device, add a goal on My MentalMap, and check it matches what you talked about; note what's confusing.
- [ ] Supervised student: try the MVP with the educator beside them. They can say no or stop at any time.

### Later: Version 3 Play and points

- [ ] Supervised student: a first race with the educator beside them, then answer Lerni's questions in the conversation for points; buy a car.
