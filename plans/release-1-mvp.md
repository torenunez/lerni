# Release 1 MVP: build plan

The smallest app a student can try: one approved activity on an iPad, answered by tapping, with the educator beside them controlling it from their own device. Requirements: [student PRD, Release 1](../docs/prd/student.md#release-1-answer-questions-about-something-you-love) and [educator PRD, Release 1](../docs/prd/educator.md#release-1-seed-approve-and-supervise). Where this plan and a PRD disagree, the PRD wins.

## Already built

- `PackageLessonCatalog` (`src/lerni/student/catalog.py`): loads an activity only if it is approved and its files match their recorded fingerprints.
- `DeterministicLessonEngine` (`src/lerni/student/engine.py`): `initial_state`, `transition`, and `snapshot` run the question, hint, reveal, and completion steps. `snapshot` never exposes the answer key.
- One draft activity: `chain_1_acceleration` (cars), with its picture.

## To build

Build in this order, in parallel with the educator's content work. Steps 1–4 need no approved content: step 1 runs empty, and steps 2–4 are tested with synthetic activities and previewed with the draft car activity. Only the student's first session waits for an approved activity.

1. **Walking skeleton: the app runs, and you can log in.** `lerni serve` starts the app on the home server (an always-on Mac), bound to all network addresses rather than only `localhost`, so other devices can reach it. Done when the educator logs in from their own phone or laptop and sees "No approved activities yet", and the iPad shows the student's waiting screen.
   - **Two apps, one server.** The student screen and the educator view are two Gradio apps mounted on separate routes of one server, sharing the controller. Gradio's login protects a whole app, not one tab, so only the educator app gets it. The passcode is set by the admin as an `env:VAR` reference, never in a file. Every educator handler (Start, Stop, Reset, recap, preview, draft pictures) checks it on the server; no handler is exposed as a public API endpoint (`api_name=False` on everything). The student screen has no login.
   - **Done also means:** a browser without the passcode can use the student screen but cannot call any educator action directly, even knowing its URL. Test this here, before building the activity screens.
   - **Dependencies:** add the `[student]` extra to `pyproject.toml` with Gradio pinned to a current release; check Gradio's security advisories when choosing the version.
   - **Server setup:** allow the virtual environment's Python through the macOS firewall ahead of time, since the server may be started remotely where nobody sees the prompt, and keep it running in `tmux`.
   - **Network boundary:** plain HTTP is fine because there is no microphone, but that says nothing about who can reach the app, so set it deliberately:
     - Trusted home network only. No port forwarding, and never Gradio's `share=True` public links.
     - Gradio's usage analytics off (`GRADIO_ANALYTICS_ENABLED=False`, set before Gradio is imported) and browser run history off on both apps (`run_history=False` where supported).
     - Serve only the pictures the current screen needs, never a whole folder; Gradio's allowed-path lists expose everything in them.
     - Use a theme with local fonts, so the iPad loads nothing from outside.
     - Before the first session, check that the app makes no outbound requests and writes nothing to disk, logs, or browser storage.
2. **Activity listing and draft preview.** The catalog can load an activity by ID but can't list them yet. Add a method that returns only activities that load successfully as approved; a raw index entry is never treated as approved. Add a separate preview load that checks the file's fingerprints but not the approvals, for the educator view only, and returns a distinct draft type that the live session refuses. The draft car activity has blank picture hashes, so the preview load checks its pictures against the generated index instead; the approved loader stays as strict as it is.
3. **Session controller.** Owns the one live session, in memory, shared by two pages. The contract:
   - Each session has an ID and a generation number that Start and Reset increase. Every tap carries the session ID, the generation, the state revision it was drawn from, and a request ID.
   - A tap is applied only if all four match the current session and the request ID is new. Anything else (late, repeated, from an earlier session, or from a screen drawn before Stop) is ignored.
   - Each update is atomic: one lock around read, transition, and write, because Gradio can run separate event handlers at the same time.
   - Stop: once it commits, the server accepts no more input, and the student screen shows Stop within 2 seconds (the refresh interval sets this; test it on the real iPad). A response drawn from an older state never redraws the screen after Stop or Reset. The recap stays in memory until the educator dismisses it. Reset discards the session and the recap, and so does a server restart. Because the session lives on the server, reloading either page shows the live session again; a page that disconnects stops receiving updates and shows the live session (or the waiting screen) when it reconnects.
   - Nothing is written to disk or browser storage, and logs hold no student content.
   - Preview sessions are separate from the live session. Preview while an activity is live either runs in isolation or is refused; the live session never changes.
4. **Two pages, two devices.** The student screen on the iPad and the educator view on the educator's own phone or laptop, both served by the same app. Session state lives in the controller on the server, not in per-page Gradio state, so both pages see the same session. The student screen refreshes on a short timer so that Stop takes effect without the student tapping.
   - **Student screen:** a waiting screen until Start; then the current step's question, the picture with its text alternative, and large tappable choices; then hints, the answer reveal, completion, and a "tell your educator why" prompt. Touch only.
   - **Educator view:** approved activities, with Start, Stop, and Reset, and the recap (choices picked, hints used, time taken), discarded after viewing. Drafts appear in a separate list marked DRAFT; the educator can run one as a preview on their own device so they can try it before approving. A draft is never sent to the student screen.

5. **Planning in the educator view.** Forms in the educator view replace the CSV plan sheet and the Markdown activity card: the educator sets up a learning plan (an interest, a goal, and 3–5 activities in order) and fills in an activity card for the next activity. Both are saved on the home server; they are curriculum, not student data. At first the admin turns a saved card into an activity file and runs the checks; automatic packaging comes once the form is stable. The educator then previews the activity and records the four approvals in the educator view, each tied to the activity's content hash, so nobody types approvals into a file.

Gradio is an optional extra (`pip install -e ".[student]"`), never a core dependency. The controller goes in `src/lerni/student/controller.py` (standard library only); the screens go in `src/lerni/student/web/`, the only place that imports Gradio.

## Tests

Use fakes and synthetic activities; no network. Cover:

- unapproved or altered activities never appear;
- every engine path through the screen: right, wrong with hints, hints exhausted;
- two taps at once, a tap racing Stop or Reset, repeated and late taps, reload, and disconnect;
- the educator view controlling the student screen, and every educator action refusing a request without the passcode;
- a draft preview never reaching the student screen, even while an activity is live; draft pictures refused without the passcode, even by exact filename;
- Stop shown on the iPad within the bound, including Stop between refreshes, delayed or reordered responses, and disconnect then reconnect;
- the core modules importing nothing outside the standard library and `lerni.student`;
- nothing saved to disk, logs, or browser storage, and no outbound requests.

## Before a student uses it

- The educator approves one activity (the car activity is the quickest: [review sheet](runbooks/chain-1-source-review.md)), and the admin records the four approvals in its file.
- The educator rehearses the whole activity on the iPad and their own device, including Stop and Reset, then authorizes student use.

## Not in this release

Voice, AI replies, remembering, accounts, HTTPS, hosting outside the home, spreadsheet import, and suggestions.
