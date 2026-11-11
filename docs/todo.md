# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by version; the admin's build work is the running list of [upcoming versions](#upcoming-versions). When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each version: [roadmap](roadmap.md).

## Educator

### Now: Version 1 MVP

- [ ] Think of 2–3 things you'd like the supervised student to explore (with a note each on what you have in mind). Add them on MentalMaps (☰ → MentalMaps): type them into the list, or tell the chat, or attach your notes with 📎 and tick what to add.

- [ ] Before the first race: check the goals on MentalMaps are what you'd like the race to practice, since its questions come from them; then sit with the supervised student for their first race.

### Later: Version 1 MVP

- [ ] Talk with Lerni yourself for a few days and watch your own MentalMap; tell the admin what's confusing, or mention it in the Tell Lerni box.
- [ ] Try the conversation with the supervised-student voice, then sit beside the supervised student for a short first conversation. Keep notes private, or mention them in the Tell Lerni box.

### Later: Version 4 The educator's Chat

- [ ] Pick one goal (acceleration or fractions) and gather a worksheet or answer key for it, to give Lerni through Chat when Version 4 arrives.

## Admin

### Now

- [ ] Read the private repeat report (Claude runs it on existing labels, on your screen only; never committed).
- [ ] Check v3.7 on the iPhone and iPad (both on the same Wi-Fi as the Mac): Games, the ⭐ tap and "+3" in Chat, both MentalMap screens, and Hold to talk.
- [ ] Turn off extra usage (paid credits) on the Claude account Lerni uses (claude.ai → Settings → Usage), so Lerni can never spend credits; Lerni also rests if a call ever uses them.
- [ ] Pick Lerni's voice ([admin reference: Voice](reference/admin.md#voice); set it, then install the service again), try Hold to talk on the iPad, then with the supervised student and an adult nearby (Version 2 is done when their map grows from a spoken conversation).
- [ ] Optionally delete the old plan files on the home server (`~/.lerni/student/plans/`); nothing reads them any more.

### Upcoming versions

What ships next, in order, one PR each ([how versions work](roadmap.md#versions)):

Longer sessions within the Claude plan's limits (the admin's call, 2026-11-11; [plan](../plans/longer-sessions.md)); later rows take the next number when they start:

1. **v4.6, usage meter:** each Claude call records its use case, model, tokens, seconds, retries, and the 5-hour and weekly shares after it (numbers only, `usage/<day>.jsonl`); `lerni stats` shows Claude use by feature. A week of data may reorder rows 4, 6, and 7.
2. **Question quality from the ratings** (the admin's notes, 2026-11-11): numbers realistic for the setting (a soccer score isn't 37); choices that are plain answers, not explanations; a hard word or idea (a clock's long and short hands) explained in the question first; the "a bit of history" twist only when it's part of the question, never a sentence tacked on; and checked with the race eval. Then a real rating round on production's data, the Korean goal first (the admin noticed its questions were too hard and off the goal).
3. **Map picture: general interests only** (the admin, 2026-11-11): only top-level items (cars, not a car model), each sized by its kinds' days on a scale that keeps growing past today's "strong" cap (`strength`, `RADII` in `mapdraw.py`); kinds stay in the list, and links to a kind draw to its general interest. Mockup first.
4. **Overnight write-ahead:** at 02:00 the day's supply (about 12 races and their bonuses) is written through every check and kept on disk until the day ends (the admin's call, a rule 6 addition), so a restart doesn't rewrite it; the session writes only when it runs out.
5. **Check a few questions** ([plan](../plans/v4.0-educator-chat.md)): up to 3 of the questions actually raced, from different goals (the least checked first) and weighted toward ones the student missed, to mark Right ✓ or Wrong ✗; ✓ goes into the goal's checked bank, ✗ never races again; races mix in up to 1 banked question each, not again for 7 days, retired after 3 right in a row; an idea right every time (at least twice) leaves races but stays open for Version 6 recall. Plus the 2026-11-10 review's additions in the plan.
6. **Lighter chat turns:** fewer earlier messages with a short summary, the map context only when it changes, and supervised chat on Haiku 5.5 tested (the admin's call) with a switch back; kept only with no visible quality loss.
7. **A local tagger in shadow:** `llama-server` with Qwen3.5-4B at 4-bit (16 GB memory, about 16 GB disk free), beside Haiku on the same exchanges, reading the logs in place (the admin's call) and keeping only agree/disagree counts; local first once `answered` agrees 90%+ and `skip` misses nothing. Training only on people's labels, never on Claude's outputs without Anthropic's permission.
8. **Feedback and answer keys through Tell Lerni:** guidance notes from broad feedback ("more variety, fewer dinosaur questions" applies to every goal), read by the question writer and the morning plan; "harder" or "easier" becomes a proposed level change to tick; answer keys proposed as questions with two wrong choices, blind-checked, into the bank on a tick; a ✗'s why steers that goal's questions.
9. **Minimal CI** (moved before Version 5, the admin's call, 2026-11-10): on each PR, GitHub Actions runs only a few key integration tests (fakes only, no secrets, never an eval), marked in the suite, plus lint on changed files; the full suite stays in the commit gate.
10. **Versions 5–7** ([roadmap](roadmap.md)), gated (the admin's call, 2026-11-10): Version 5, suggested goals, built switched off until enough probe data (for example 10 🔭 taps), with a visible reason and dismissals remembered; Version 6, remembering, designed first and built once a goal's checked bank holds about 8, on the existing schedule (`sm2.py` or the fixed ladder; FSRS after about 500 reviews), with no ⭐ for recall; Version 7, its own release after a written safety plan: a distress flag to the educator, replies checked before they're shown or spoken, a filter for personal details typed, set-aside checks everywhere, session and daily limits, worrying ungraded bonus answers shown to the educator, and a way to reach the educator for consent.
11. **Version 8, away from home** (after Version 7, the admin's call, 2026-11-10; the admin's Tailscale setup has started): reach Lerni privately over Tailscale Serve from the family's devices, the iPad included; never Funnel or port forwarding. Ops first, development then production, tested on cellular (sign-in, Chat, Hold to talk, a race; page, first text, and first audio timed); the PR is the admin steps in the admin reference, with no tailnet names. Production deploys pause while away unless a deploy over SSH is tested.

How PRs are split:

- **One unit per PR:** one change (with the docs it changes), or one docs-only change, never two units in one PR.
- **In order:** each branch starts from `main` after the PR before it merges.
- **Each PR carries its own docs:** code manifest, todo, and progress for what it ships, and its version: the `vX.Y:` title and `version` in `pyproject.toml`.
- **Merged only by the admin,** after the "done when" is checked on the real devices.
- **The shipped version stays in use:** each PR says in a Deploying section whether it's safe to put on the home server while the family uses it, how, and the caveats ([admin reference](reference/admin.md#updating-the-home-server)).
- **When a PR merges:** tag `main` with its version, delete its row, and add a dated entry to [progress](progress.md). Work found along the way gets a new row or a task below, not a bigger PR.

Versions 1 and 2 also need sessions, not code: the educator sets goals, rehearses, and sits beside the supervised student (Educator and Student tasks above and below).

### Later

- [ ] **The win rate (after v3.33, about mid-November):** with about two weeks of results lines carrying `level`, compare right answers by level, and places, against the target (about 60% right, 1 race in 3 won); then decide whether to change the level steps (`UP_AT`, `DOWN_AT` in `concepts.py`) or the rivals' pace.
- [ ] Chat for everyone (split from one Chat, 2026-10-30): an independent student's Chat proposes goals for their own map and takes feedback about the app.
- [ ] A second backup place for a broken disk: an external drive (`lerni backup run --to …` in the agent) or Time Machine. The nightly copies (v3.20) are on the same disk.
- [ ] After a week of family use: compare each feature's Claude use (Chat, tagger, Upload, the Tell Lerni box) and decide whether any can move to a cheaper model.
- [ ] Try the voice with the students before deciding whether a hosted voice (Inworld, about $18 a month) is worth it; a hosted service means student audio leaves the house, so it needs the educator's agreement first.
- [ ] Tell Lerni box: PDFs (its Claude call takes text only; Upload on My MentalMap still reads PDFs).
- [ ] `feedback.summarize` is unused since v2.14 (the chat writes the note); remove it with its test, or use it for chat feedback.
- [ ] After the first supervised sessions, if useful: count redirects per session, and a "flag this reply" button for the adult nearby.
- [ ] Try Chat on the iPad and a phone with the keyboard open; then a VoiceOver and keyboard-only pass.

### Later: Version 3 Play and points

- [ ] Embeddings, later uses ([spec 10](../plans/specs/10-local-embeddings.md#later-uses-described-not-built)): Chat's goals ranked by the student's message (if wanted), the "same as" shortlist once items rest, and near-duplicate ideas grouped in `lerni stats`; the 2026-11-10 review's deferred uses, each with its trigger ([options](../plans/v4.1-repeats-by-theme.md#the-reviews-verdicts-on-more-embedding-uses)).
- [ ] A week after v3.40: read the server log's counts of questions dropped by meaning; add made-up Spanish pairs to the bake-off when a Spanish miss is seen.
- [ ] Pit stop: fill a toy car's fuel gauge with quarters, then the same amount with eighths (fixed math, no Claude calls); the educator sketches the scene first.
- [ ] An educator "reset points", and Games for independent students.
- [ ] Other games: Beat builder (rhythm and fractions), Recipe mixer (ratios), Build and balance.
- [ ] One race question a set that combines two goals (from v3.46, set aside when the morning plan took its idea lists, 2026-11-10).
- [ ] A "this question seems wrong" button that doesn't use up a race (the blind check catches most wrong keys since v3.14).
- [ ] Garage extras: read-aloud 🔊 on cards; a short "here are your keys" moment on buying (reduced motion respected); paint and a number plate bought with ⭐; shark, rocket or dinosaur bodies for students who aren't into cars; an educator preview of a student's race questions.
- [ ] Two weeks after v3.7: are Lerni's questions getting real answers, or are points just being hunted? `answered` is Claude's judgment, not a check, so spot-check it in `lerni logs`. Tune the points, or stop.
- [ ] Two weeks after v3.18 (about 2026-11-03): read the results log; is each goal at about 50–75% right? If not, change `UP_AT`/`DOWN_AT` or the level descriptions in `QUIZ_SYSTEM`.
- [ ] After a week of bonus rounds: read the results log's bonus tiers (how often nailed, partly, tried) and spot-check that grading is fair; tune `GRADE_SYSTEM` or the points if not.

### Later: Version 6 Remembering

- [ ] Personal personas: Lerni learns what each student likes over time (topics, examples, answer length), starting from the persona for their kind; visible to the student, and to the educator for a supervised student.
- [ ] Later, once the results log has months of data: embedding hints for proposals already on the map, "kind of" suggestions, and near-repeat race questions.

### Before anyone outside the family uses the app

- [ ] Delete for good, for real: erase the item from its map journal, results, and concepts (a `lerni forget` command); until then the screen says the history and nightly copies keep it (the admin's call, 2026-10-27).
- [ ] Shorten how long conversation logs are kept (a year now) and decide what else to keep less of.
- [ ] Replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).
- [ ] Files in Gradio's cache (uploads, any voice audio) are reachable by URL to anyone signed in; serve them only to their owner, or keep none.
- [ ] A short notice of where messages go and that answers can be wrong.
- [ ] A flood of sign-ins mustn't stall signed-in pages: run the password check off the request threads with a small limit.
- [ ] Maybe a daily cap per student.
- [ ] Run Lerni under its own standard macOS account, with only its data and Claude sign-in, and bind it to localhost once every device reaches it over Tailscale (deferred from away from home, 2026-11-10).

### Deferred review findings (small; family scale)

- [ ] **Race eval (v4.2–v4.4):** "level 5 still makes a race" and "1 or 2 bonus questions" each failed in 2 of 3 runs, though a level-5 rerun kept 13 of 15; if they keep failing, look at the bonus rate in production's results and the one-goal, one-interest eval map.
- [ ] **v4.4 review:** a minus after a letter ("x-3") still reads as a space, so it doesn't match "x - 3"; fix if sums with letters come up.
- [ ] **v4.3 review:** a broken points file resets the student quietly (moved aside, by design); list `*.broken-*` files in `lerni service status` so the admin sees it.
- [ ] **Outside reviews (2026-11-10):** restore refuses while a server started by hand still runs; set-aside by meaning re-checked when a held set is raced, not only when written; a failed blind check holds its set back and counts in the banner (before Version 7); a set-aside made during bonus grading reaches its feedback line (before Version 7); backups: leave `logs/` out of `--to` copies, warn on drives without file permissions, prune `.before-restore-*`, and `status` says STALE after 2 days; one embedder call at a time (a semaphore); the embedder's output parsing (noisy stdout, NaN); the morning plan's start-up and 05:00 runs racing `ran_today`; connections keyed by interest name, so a rename drops one; interest names and goal notes unfenced in the morning and area prompts; `logs.purge()` never runs on an idle server; a docs-drift pass (architecture on the blind check, learning concepts on areas, the student PRD's consent wording).
- [ ] **Chat:** Stop before the first word can be slow and a quick re-ask may say "Still answering"; the two chat panels allow 8 answers at once instead of 4 (share one concurrency id); a cancel can log "Exception ignored"; the new message isn't JSON like earlier turns; when Claude isn't set up the supervised screen greets over a disabled box; the guns redirect offered squirt guns (offer something unrelated).
- [ ] **Upload and feedback:** cap how big a .docx may expand when read, and show a friendly message for a malformed one; a file-read error can hide its cause; no server-side check for real names in proposals; "Tick what to add" shows when every idea is already on the map; `lerni feedback done` can lose an entry saved at the same moment and finds entries by position; editing feedback after checking keeps the old summary; Claude pads goal notes with restatements.
- [ ] **The map:** top interests rank by all-time days rather than the last 30; a faded explained goal can be listed twice in the block; the MentalMaps timer ticks on every page; an unreadable map file shows a Gradio error; `lerni logs` can fail if a purge runs mid-read.
- [ ] **Educator chat:** a proposal names its target, so an old one can change a newer item with the same name; Clear or a new student can be undone by a reply still arriving; 📎 notes are sent again every turn; removals are reported as "Added".
- [ ] **The educator's page (v3.25):** a student added, renamed, or archived in Settings shows in the menu and picker only after a reload; with two or more students the picker doesn't remember the last pick; an empty folded list reads "Goals (0)".
- [ ] **Tagging:** two quick answers' tags can land out of order, and a subject change counts against the newest bridge rather than the one in the answer before.
- [ ] **MentalMap list:** a redraw trusts the owner set by the last checked handler and doesn't re-check the viewer (every edit does).
- [ ] **Games:** v3.30 review: on a wrong last answer the finish fanfare and the spoken right answer overlap; v3.21 review: tapping a garage tile while a wrong answer's why shows skips to the next question (the waiting card lives only on screen); a tap within 0.8 s is dropped silently; v3.16 review: with the driven car gone from the garage file, the starter can be both the drawn car and the slow rival; the Sound switch shows "on" for a frame on the first page load while off; an all-caps rival name of about 18 letters runs a little past its label pill; the MentalMaps points line refreshes only on picking a student. Garage file: a car removed from it disappears from its owners (add a `retired` flag instead, and say so in the admin reference); one route-test path is rewritten by the test client; the picture route serves any signed-in account, has no `nosniff`, and caches a replaced picture for a day. `lift_car.swift`: a bad crop number crashes it, it keeps every foreground object (a person beside the car), writes full size, and may ignore a photo's rotation.
- [ ] **Groups:** a group ticked in the Tell Lerni box can bring back a removed name without Put back, and one failing member skips the rest; the tagger can link any two names on the map without seeing the existing groups, and "Not under" blocks one direction only.
- [ ] **Services (v3.11 review):** the crossed-data and port checks know only the default folders and ports (read the other agent file instead), and don't catch both servers run from one checkout.
- [ ] **Names (v3.12 review):** spellings that differ only in spaces and punctuation count as one, so a set-aside "he'll" also blocks "hell" and "its" blocks "it's" (it errs toward blocking); a merge that finds a group loop keeps the first link it sees, which may not be the true one.
- [ ] **Memory (v3.10 review):** a resting item named only in the tagger's `about` doesn't wake (harmless: the tagger sees only the map); the concept ledger rewrites its whole file on each right answer and is never trimmed (about 600 KB a year); the map block can keep "Goals to bridge toward" with every goal line too long to fit.
- [ ] **Right answers (v3.14 review):** `_number` reads a choice's first number, so with a sum given, "Car 2" or "0 to 60 in 3 s" can be dropped wrongly (never a wrong key let through); two choices with the same number aren't caught; `week()` groups by goal name, so a renamed goal splits; seconds include reading the last why.
- [ ] **Chat points (v3.7 review):** the ⭐ baseline is read when an answer ends, so a much faster tagger could add points before it and "+3" wouldn't show (read it when the answer starts); two answers close together announce only the second; "⭐ N +3" stays on the button until the next refresh; `games_tab` still types the header ⭐ as Markdown.
- [ ] **Garage (v3.5 review):** a driven car gone from the garage file leaves no tile saying "Driving" (the hero shows the starter); with no garage file a new player reads "Every car is yours! 🏆" over an empty Showroom; a cartoon car's Car facts holds only the ⚡ line (skip it); the Car facts line writes $2,500 instead of using `PRICE_PER_STAR`; car names go into the result line's Markdown unescaped; after buying on the finish screen the new car shows only on the next race; ⚡ 1–5 stands for only 3 race outcomes (⚡⚡⚡ to ⚡⚡⚡⚡⚡ race alike: use ⚡ 1–3 or a smooth boost); `usd: true` loads as $1 and `name: null` shows "None".
- [ ] **Names and races (v3.4 review):** a failed first Race tap makes a second waiting tap try Claude twice more (remember the failure for a few seconds); when the only goal is removed, its held questions still race; the Race catch-all logs nothing (log the error's type only); re-adding "shark" drops the removed "sharks" history; after Put back a kind can sit under both a group and that group's parent.
- [ ] **Safety:** nothing tells the educator when a student says they're hurt (a content-free "check in with the student" flag would); a sad-but-not-harm message ("my dog died") isn't clearly covered; the disclosure eval runs each case once and checks keywords.
- [ ] **Menu:** the closed drawer is still reachable by keyboard and VoiceOver.
- [ ] **Accounts:** two educators archiving each other leaves none (recover with `lerni student add`); password hashing runs inside the account write lock; a live session can guess its current password in Settings without the sign-in delay; a non-ASCII cookie gives a 500; an archived account is detectable by timing; `/signin` has no Origin check and `/signout` is a GET; the data folder is created 0755; a password change doesn't sign out other devices.
- [ ] **v3.44 review:** a morning call that fails is marked as run, so a restart that day doesn't retry it (retry once at the next start-up); a start-up at 5:00 can run two calls at once and save twice (make "ran today" atomic).
- [ ] **v3.42 review:** the one-car-comparison cap reads only the question's text and whole car names (not the choices, "the P1", or one name inside another); the 5:00 write-ahead sleeps in one stretch, so a clock change moves it an hour; held questions already a few races deep aren't rewritten at 5:00, so they keep the levels they were written at; a question Claude writes for a goal outside the set isn't checked against that goal's month of ideas; the Variety line's "asked before" counts spaced reviews too.
- [ ] **v3.31 review:** when the stricter answer check leaves too few questions, the agreed ones are thrown away and the next Race tap writes and checks a whole set again (hold them for the next try).
- [ ] **v3.7–v3.29 reviews (small):** a tagger `same_as` can fold an interest into a goal (allow interest to interest only); Chat's set-aside line lists 8 names and no aliases; journal lines grow large and nothing is trimmed; goal boxes, "missed lately", and reviews each define "got it" differently; `service status` exits 0 when stopped; `install` replaces the agent file before it starts; the educator's reword suggestion comes pre-ticked and hides the old notes; voice failures while running aren't logged, and Whisper's "Thank you." on near-silence reaches Claude; read-aloud: quick taps start several `say` runs, and `*` or `>` are read oddly; the race card still says more ⚡ moves the car farther; Rich markup in a log tail crashes the failure report; `usd: true` loads as $1.
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
