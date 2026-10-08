# Release 1 MVP: build plan

The smallest app a student can try: one approved activity on an iPad, answered by tapping, with the educator beside them controlling it from their own device. Requirements: [student PRD, Release 1](../docs/prd/student.md#release-1-answer-questions-about-something-you-love) and [educator PRD, Release 1](../docs/prd/educator.md#release-1-seed-approve-and-supervise). Where this plan and a PRD disagree, the PRD wins.

## Already built

- `PackageLessonCatalog` (`src/lerni/student/catalog.py`): loads an activity only if it is approved and its files match their recorded fingerprints.
- `DeterministicLessonEngine` (`src/lerni/student/engine.py`): `initial_state`, `transition`, and `snapshot` run the question, hint, reveal, and completion steps. `snapshot` never exposes the answer key.
- One draft activity: `chain_1_acceleration` (cars), with its picture.

## To build

Build in this order, in parallel with the educator's content work. Steps 1–4 need no approved content: step 1 runs empty, and steps 2–4 are tested with synthetic activities and previewed with the draft car activity. Only the student's first session waits for an approved activity.

1. **Walking skeleton: the app runs, and you can log in.** `lerni serve` starts the app on the home server (an always-on Mac), bound to all network addresses rather than only `localhost`, so other devices can reach it. Done when the educator logs in from their own phone or laptop and sees "No approved activities yet", and the iPad shows the student's waiting screen.
   - **Login:** the educator view asks for a passcode. The admin sets it as an `env:VAR` reference, never in a file. The student screen has no login; it only shows what the educator starts. Gradio's built-in login over plain HTTP on the home network is acceptable for this prototype.
   - **Server setup:** allow the virtual environment's Python through the macOS firewall ahead of time, since the server may be started remotely where nobody sees the prompt, and keep it running in `tmux`.
   - **Network boundary:** plain HTTP is fine because there is no microphone, but that says nothing about who can reach the app, so set it deliberately:
     - Trusted home network only. No port forwarding, and never Gradio's `share=True` public links.
     - Gradio's usage analytics off (`GRADIO_ANALYTICS_ENABLED=False`), and only the activity's pictures exposed as files.
     - Before the first session, check that the app makes no outbound requests and writes nothing to disk.
2. **Activity listing and draft preview.** The catalog can load an activity by ID but can't list them yet. Add a method that returns only activities that load successfully as approved; a raw index entry is never treated as approved. Add a separate preview load that checks the file's fingerprints but not the approvals, for the educator view only.
3. **Session controller.** Owns the one live session, in memory, shared by two pages. The contract:
   - Each session has an ID and a generation number that Start and Reset increase. Every tap carries the session ID, the generation, the state revision it was drawn from, and a request ID.
   - A tap is applied only if all four match the current session and the request ID is new. Anything else (late, repeated, from an earlier session, or from a screen drawn before Stop) is ignored.
   - Each update is atomic: one lock around read, transition, and write, because Gradio can run separate event handlers at the same time.
   - Stop ends interaction at once and keeps the recap in memory until the educator dismisses it. Reset discards the session and the recap, and so does a server restart. Because the session lives on the server, reloading either page shows the live session again; a page that disconnects simply stops receiving updates.
   - Nothing is written to disk, and logs hold no student content.
4. **Two pages, two devices.** The student screen on the iPad and the educator view on the educator's own phone or laptop, both served by the same app. Session state lives in the controller on the server, not in per-page Gradio state, so both pages see the same session. The student screen refreshes on a short timer so that Stop takes effect without the student tapping.
   - **Student screen:** a waiting screen until Start; then the current step's question, the picture with its text alternative, and large tappable choices; then hints, the answer reveal, completion, and a "tell your educator why" prompt. Touch only.
   - **Educator view:** approved activities, with Start, Stop, and Reset, and the recap (choices picked, hints used, time taken), discarded after viewing. Drafts appear in a separate list marked DRAFT; the educator can run one as a preview on their own device so they can try it before approving. A draft is never sent to the student screen.

Gradio is an optional extra (`pip install -e ".[student]"`), never a core dependency. New code goes under `src/lerni/student/`.

## Tests

Use fakes and synthetic activities; no network. Cover:

- unapproved or altered activities never appear;
- every engine path through the screen: right, wrong with hints, hints exhausted;
- two taps at once, a tap racing Stop or Reset, repeated and late taps, reload, and disconnect;
- the educator view controlling the student screen, the student screen unable to open the educator view, and the passcode required;
- a draft preview never reaching the student screen;
- nothing is saved to disk, and no outbound requests are made.

## Before a student uses it

- The educator approves one activity (the car activity is the quickest: [review sheet](runbooks/chain-1-source-review.md)), and the admin records the four approvals in its file.
- The educator rehearses the whole activity on the iPad, including Stop and Reset, then authorizes student use.

## Not in this release

Voice, AI replies, remembering, accounts, HTTPS, hosting outside the home, spreadsheet import, and suggestions.
