# Release 1 MVP: build plan

The smallest app a student can try: one approved activity on an iPad, answered by tapping, with the educator beside them. Requirements: [student PRD, Release 1](../docs/prd/student.md#release-1-answer-questions-about-something-you-love) and [educator PRD, Release 1](../docs/prd/educator.md#release-1-seed-approve-and-supervise). Where this plan and a PRD disagree, the PRD wins.

## Already built

- `PackageLessonCatalog` (`src/lerni/student/catalog.py`): loads an activity only if it is approved and its files match their recorded fingerprints.
- `DeterministicLessonEngine` (`src/lerni/student/engine.py`): `initial_state`, `transition`, and `snapshot` run the question, hint, reveal, and completion steps. `snapshot` never exposes the answer key.
- One draft activity: `chain_1_acceleration` (cars), with its picture.

## To build

1. **Session controller.** Owns one in-memory session: start, the student's taps, stop, reset. Stop and Reset take effect at once; a delayed, repeated, or earlier-session tap is ignored. Nothing is written to disk, and logs hold no student content.
2. **Student screen.** Shows the current step's question, the picture with its text alternative, and large tappable choices; then hints, the answer reveal, completion, and a "tell your educator why" prompt. Touch only.
3. **Educator view.** Lists approved activities only, with Start, Stop, and Reset, and shows the recap (choices picked, hints used, time taken) when an activity ends. The recap is discarded after viewing.
4. **Running it for the iPad.** A `lerni` command, or a short script, starts the app on the home server (an always-on Mac), bound to all network addresses rather than only `localhost`, so the iPad can reach it. The iPad opens it in Safari on the same Wi-Fi. No microphone in this release, so plain HTTP is fine. Allow the virtual environment's Python through the macOS firewall ahead of time, since the server may be started remotely where nobody sees the prompt, and keep it running in `tmux`.

Gradio is an optional extra (`pip install -e ".[student]"`), never a core dependency. New code goes under `src/lerni/student/`.

## Tests

Use fakes and synthetic activities; no network. Cover:

- unapproved or altered activities never appear;
- every engine path through the screen: right, wrong with hints, hints exhausted;
- Stop and Reset at any point, and late or repeated taps after them;
- nothing is saved to disk.

## Before a student uses it

- The educator approves one activity (the car activity is the quickest: [review sheet](runbooks/chain-1-source-review.md)), and the admin records the four approvals in its file.
- The educator rehearses the whole activity on the iPad, including Stop and Reset, then authorizes student use.

## Not in this release

Voice, AI replies, remembering, accounts, HTTPS, hosting outside the home, spreadsheet import, and suggestions.
