# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by version; the admin's build work is the running list of [upcoming versions](#upcoming-versions). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each version: [roadmap](roadmap.md).

## Educator

### Now: Version 1 MVP

- [ ] Think of 2–3 things you'd like the supervised student to explore (with a note each on what you have in mind). Add them on MentalMaps (☰ → MentalMaps): type them into the list, or tell the chat, or attach your notes with 📎 and tick what to add.

- [ ] Before the first race: check the goals on MentalMaps are what you'd like the race to practice, since its questions come from them; then sit with the supervised student for their first race.

### Later: Version 1 MVP

- [ ] Talk with Lerni yourself for a few days and watch your own MentalMap; tell the admin what's confusing, or mention it in the MentalMaps chat.
- [ ] Try the conversation with the supervised-student voice, then sit beside the supervised student for a short first conversation. Keep notes private, or mention them in the MentalMaps chat.

### Later: Version 4 Remembering

- [ ] Pick one goal for the first fact cards (acceleration or fractions) and review a dozen short cards for it, with sources.

## Admin

### Now

- [ ] Check v3.7 on the iPhone and iPad (both on the same Wi-Fi as the Mac): Games, the ⭐ tap and "+3" in Chat, both MentalMap screens, and Hold to talk.
- [ ] Turn off extra usage (paid credits) on the Claude account Lerni uses (claude.ai → Settings → Usage), so Lerni can never spend credits; Lerni also rests if a call ever uses them.
- [ ] Pick Lerni's voice ([admin reference: Voice](reference/admin.md#voice); set it, then install the service again), try Hold to talk on the iPad, then with the supervised student and an adult nearby (Version 2 is done when their map grows from a spoken conversation).
- [ ] Optionally delete the old plan files on the home server (`~/.lerni/student/plans/`); nothing reads them any more.

### Upcoming versions

What ships next, in order, one PR each ([how versions work](roadmap.md#versions)):

1. **v3.22: missed ideas come back:** a miss is due in 1 day, then 3, then 7, and a right answer at 7 retires it (labels and dates only); up to 2 due ideas a race, asked in new words; the Practice line then matches missed ideas by their normalized label ("Thirds" and "thirds" are one).
2. **v3.23: the bonus round** (after the 2026-11-03 check of right answers per goal): an "explain it" question as question 4 when the student is last after question 3, or in about 1 race in 4; typed or spoken; Claude grades it against its key ideas: nailed 15 ⭐, partly 7, a real try 2, otherwise 0; nailed and partly move the car like a right answer; the answer stays in memory only.
3. **v3.24: probes:** one question a race tries a nearby idea not on the map; never set aside, never counted toward the level; after the race, up to two "Want to find out more?" topics open Chat; probe answers and taps are kept as labels for Version 5.
4. **v4.1: the Version 4 plan** (docs; Version 4 below), which also says where the embeddings fit.
5. **v4.2: spec 10, local embeddings:** a local embedder run as a command like `whisper-cli` (llama.cpp `llama-embedding` with a small model in `~/.lerni/models/`, chosen by a bake-off on about 100 labelled name pairs; nothing hosted), behind an adapter with a fake for tests, vectors cached by name. Uses: shortlist "same as" candidates the tagger can't see (Older interests, long maps) for Claude to confirm; catch set-aside topics by meaning in race questions (beside the word match, never instead), and rank the map block by the current message (whole lines; safety lines first). It flags and shortlists only; it never changes the map. Lifts spec 08's "no embeddings" for these uses only; and the plan.
6. **v4.3: local embeddings built,** per spec 10. Without the embedder, everything falls back to today's behavior.
7. **Version 4, remembering:** opens with an educator-approved fact-card library for one goal (`~/.lerni/library/`, nothing about any student): race questions quote a card and the server checks the quote; cards go into the map block as information; recall questions come from cards, with recall attempts kept apart from discussion (building on v3.22's review schedule; FSRS or SM-2). Bridge Trip (a trip along their map with recall stops) is its front door; its first PR writes the plan.

How PRs are split:

- **One unit per PR:** one change (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, todo, and progress for what it ships, and its version: the `vX.Y:` title and `version` in `pyproject.toml`.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **The shipped version stays in use:** each PR says in a Deploying section whether it's safe to put on the home server while the family uses it, how, and the caveats ([admin reference](reference/admin.md#updating-the-home-server)).
- **When a PR merges:** tag `main` with its version, delete its row, and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

Versions 1 and 2 also need sessions, not code: the educator sets goals, rehearses, and sits beside the supervised student (Educator and Student tasks above and below).

### Later

- [ ] A second backup place for a broken disk: an external drive (`lerni backup run --to …` in the agent) or Time Machine. The nightly copies (v3.20) are on the same disk.
- [ ] After a week of family use: compare each feature's Claude use (Chat, tagger, Upload, MentalMaps chat) and decide whether any can move to a cheaper model.
- [ ] Try the voice with the students before deciding whether a hosted voice (Inworld, about $18 a month) is worth it; a hosted service means student audio leaves the house, so it needs the educator's agreement first.
- [ ] MentalMaps chat: PDFs (its Claude call takes text only; Upload on My MentalMap still reads PDFs), and the same chat on My MentalMap once educators have used it.
- [ ] `feedback.summarize` is unused since v2.14 (the chat writes the note); remove it with its test, or use it for chat feedback.
- [ ] After the first supervised sessions, if useful: count redirects per session, and a "flag this reply" button for the adult nearby.
- [ ] Try Chat on the iPad and a phone with the keyboard open; then a VoiceOver and keyboard-only pass.

### Later: Version 3 Play and points

- [ ] Pit stop: fill a toy car's fuel gauge with quarters, then the same amount with eighths (fixed math, no Claude calls); the educator sketches the scene first.
- [ ] An educator "reset points", and Games for independent students.
- [ ] Other games: Beat builder (rhythm and fractions), Recipe mixer (ratios), Build and balance.
- [ ] A "this question seems wrong" button that doesn't use up a race (the blind check catches most wrong keys since v3.14).
- [ ] Garage extras: read-aloud 🔊 on cards; a short "here are your keys" moment on buying (reduced motion respected); paint and a number plate bought with ⭐; shark, rocket or dinosaur bodies for students who aren't into cars; an educator preview of a student's race questions.
- [ ] Two weeks after v3.7: are Lerni's questions getting real answers, or are points just being hunted? `answered` is Claude's judgment, not a check, so spot-check it in `lerni logs`. Tune the points, or stop.
- [ ] Two weeks after v3.18 (about 2026-11-03): read the results log; is each goal at about 50–75% right? If not, change `UP_AT`/`DOWN_AT` or the level descriptions in `QUIZ_SYSTEM`.

### Later: Version 4 Remembering

- [ ] Personal personas: Lerni learns what each student likes over time (topics, examples, answer length), starting from the persona for their kind; visible to the student, and to the educator for a supervised student.
- [ ] Later, once the results log has months of data: embedding hints for proposals already on the map, "kind of" suggestions, and near-repeat race questions.

### Before anyone outside the family uses the app

- [ ] Delete for good: also erase the item's history from its map journal and say that nightly copies keep it up to 30 days, or change the promise (educator PRD, "See and delete what's remembered"); since v3.20 the journal keeps it (the admin's call, 2026-10-21).
- [ ] Shorten how long conversation logs are kept (a year now) and decide what else to keep less of.
- [ ] Replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).
- [ ] Files in Gradio's cache (uploads, any voice audio) are reachable by URL to anyone signed in; serve them only to their owner, or keep none.
- [ ] A short notice of where messages go and that answers can be wrong.
- [ ] A flood of sign-ins mustn't stall signed-in pages: run the password check off the request threads with a small limit.
- [ ] Maybe a daily cap per student.

### Deferred review findings (small; family scale)

- [ ] **Chat:** Stop before the first word can be slow and a quick re-ask may say "Still answering"; the two chat panels allow 8 answers at once instead of 4 (share one concurrency id); a cancel can log "Exception ignored"; the new message isn't JSON like earlier turns; when Claude isn't set up the supervised screen greets over a disabled box; the guns redirect offered squirt guns (offer something unrelated).
- [ ] **Upload and feedback:** cap how big a .docx may expand when read, and show a friendly message for a malformed one; a file-read error can hide its cause; no server-side check for real names in proposals; "Tick what to add" shows when every idea is already on the map; `lerni feedback done` can lose an entry saved at the same moment and finds entries by position; editing feedback after checking keeps the old summary; Claude pads goal notes with restatements.
- [ ] **The map:** top interests rank by all-time days rather than the last 30; a faded explained goal can be listed twice in the block; the MentalMaps timer ticks on every page; an unreadable map file shows a Gradio error; `lerni logs` can fail if a purge runs mid-read.
- [ ] **Educator chat:** a proposal names its target, so an old one can change a newer item with the same name; Clear or a new student can be undone by a reply still arriving; 📎 notes are sent again every turn; removals are reported as "Added".
- [ ] **Tagging:** two quick answers' tags can land out of order, and a subject change counts against the newest bridge rather than the one in the answer before.
- [ ] **MentalMap list:** a redraw trusts the owner set by the last checked handler and doesn't re-check the viewer (every edit does).
- [ ] **Games:** a tap within 0.8 s is dropped silently; v3.16 review: with the driven car gone from the garage file, the starter can be both the drawn car and the slow rival; 🔇 shows 🔊 for a frame after each redraw while muted; an all-caps rival name of about 18 letters runs a little past its label pill; the MentalMaps points line refreshes only on picking a student. Garage file: a car removed from it disappears from its owners (add a `retired` flag instead, and say so in the admin reference); one route-test path is rewritten by the test client; the picture route serves any signed-in account, has no `nosniff`, and caches a replaced picture for a day. `lift_car.swift`: a bad crop number crashes it, it keeps every foreground object (a person beside the car), writes full size, and may ignore a photo's rotation.
- [ ] **Groups:** a group ticked in the MentalMaps chat can bring back a removed name without Put back, and one failing member skips the rest; the tagger can link any two names on the map without seeing the existing groups, and "Not under" blocks one direction only.
- [ ] **Services (v3.11 review):** the crossed-data and port checks know only the default folders and ports (read the other agent file instead), and don't catch both servers run from one checkout.
- [ ] **Names (v3.12 review):** spellings that differ only in spaces and punctuation count as one, so a set-aside "he'll" also blocks "hell" and "its" blocks "it's" (it errs toward blocking); a merge that finds a group loop keeps the first link it sees, which may not be the true one.
- [ ] **Memory (v3.10 review):** a resting item named only in the tagger's `about` doesn't wake (harmless: the tagger sees only the map); the concept ledger rewrites its whole file on each right answer and is never trimmed (about 600 KB a year); the map block can keep "Goals to bridge toward" with every goal line too long to fit.
- [ ] **Right answers (v3.14 review):** `_number` reads a choice's first number, so with a sum given, "Car 2" or "0 to 60 in 3 s" can be dropped wrongly (never a wrong key let through); two choices with the same number aren't caught; `week()` groups by goal name, so a renamed goal splits; seconds include reading the last why.
- [ ] **Race repeats (v3.9 review):** if Claude takes over 70 s while a start waits, both write at once and the background set isn't checked against the race just started, so the next race can repeat it.
- [ ] **Chat points (v3.7 review):** the ⭐ baseline is read when an answer ends, so a much faster tagger could add points before it and "+3" wouldn't show (read it when the answer starts); two answers close together announce only the second; "⭐ N +3" stays on the button until the next refresh; `games_tab` still types the header ⭐ as Markdown.
- [ ] **Garage (v3.5 review):** a driven car gone from the garage file leaves no tile saying "Driving" (the hero shows the starter); with no garage file a new player reads "Every car is yours! 🏆" over an empty Showroom; a cartoon car's Car facts holds only the ⚡ line (skip it); the Car facts line writes $2,500 instead of using `PRICE_PER_STAR`; car names go into the result line's Markdown unescaped; after buying on the finish screen the new car shows only on the next race; ⚡ 1–5 stands for only 3 race outcomes (⚡⚡⚡ to ⚡⚡⚡⚡⚡ race alike: use ⚡ 1–3 or a smooth boost); `usd: true` loads as $1 and `name: null` shows "None".
- [ ] **Names and races (v3.4 review):** a failed first Race tap makes a second waiting tap try Claude twice more (remember the failure for a few seconds); when the only goal is removed, its held questions still race; the Race catch-all logs nothing (log the error's type only); re-adding "shark" drops the removed "sharks" history; after Put back a kind can sit under both a group and that group's parent.
- [ ] **Safety:** nothing tells the educator when a student says they're hurt (a content-free "check in with the student" flag would); a sad-but-not-harm message ("my dog died") isn't clearly covered; the disclosure eval runs each case once and checks keywords.
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
