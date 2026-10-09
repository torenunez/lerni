# Release 1 MVP: build plan

The smallest app a student can try: sign in, pick an activity, and answer by tapping. The admin tries it first as an independent student, on their own interests; then a supervised student does one educator-approved library card on an iPad, with the educator beside them controlling it from their own device. Steps 5–8 follow the [student accounts design](specs/03-student-accounts.md). Requirements: [student PRD, Release 1](../docs/prd/student.md#release-1-answer-questions-about-something-you-love) and [educator PRD, Release 1](../docs/prd/educator.md#release-1-seed-approve-and-supervise). Where this plan and a PRD disagree, the PRD wins.

## Already built

- `PackageLessonCatalog` (`src/lerni/student/catalog.py`): loads an activity only if it is approved and its files match their recorded fingerprints.
- `DeterministicLessonEngine` (`src/lerni/student/engine.py`): `initial_state`, `transition`, and `snapshot` run the question, hint, reveal, and completion steps. `snapshot` never exposes the answer key.
- One draft activity: `chain_1_acceleration` (cars), with its picture.

## To build

Build in this order, one PR per step from step 5, in parallel with the educator's content work. Steps 1–4 are built and merged. Steps 5–7 need no educator-approved content: an independent student approves their own. Only a supervised student's first session waits for an approved activity.

1. **Walking skeleton: the app runs, and you can log in.** *(Built. Step 5 replaces the two apps with one app and sign-in for everyone.)* `lerni serve` starts the app on the home server (an always-on Mac), bound to all network addresses rather than only `localhost`, so other devices can reach it. Done when the educator logs in from their own phone or laptop and sees "No approved activities yet", and the iPad shows the student's waiting screen.
   - **Two apps, one server** (superseded by step 5). The student screen and the educator view are two Gradio apps mounted on separate routes of one server, sharing the controller. Gradio's login protects a whole app, not one tab, so only the educator app gets it. The passcode is set by the admin as an `env:VAR` reference, never in a file. Every educator handler (Start, Stop, Reset, recap, preview, draft pictures) checks it on the server; every event is hidden from the API page (`api_visibility="private"`; that hides, it doesn't protect). The student screen has no login.
   - **Done also means:** a browser without the passcode can use the student screen but cannot call any educator action directly, even knowing its URL. Test this here, before building the activity screens.
   - **Dependencies:** add the `[student]` extra to `pyproject.toml` with Gradio pinned to a current release; check Gradio's security advisories when choosing the version.
   - **Server setup:** allow the virtual environment's Python through the macOS firewall ahead of time, since the server may be started remotely where nobody sees the prompt, and keep it running in `tmux`.
   - **Network boundary:** plain HTTP is fine because there is no microphone, but that says nothing about who can reach the app, so set it deliberately:
     - Trusted home network only. No port forwarding, and never Gradio's `share=True` public links.
     - Gradio's usage analytics off (`GRADIO_ANALYTICS_ENABLED=False`, set before Gradio is imported) and browser run history off on both apps (`run_history=False` where supported).
     - Serve only the pictures the current screen needs, never a whole folder; Gradio's allowed-path lists expose everything in them.
     - Use a theme with local fonts, so the iPad loads nothing from outside.
     - Before the first session, check that the student screen makes no outbound requests (the educator's Claude import is the only one), and that nothing about the student is written to disk, logs, or browser storage.
2. **Activity listing and draft preview.** *(Built.)* The catalog can load an activity by ID but can't list them yet. Add a method that returns only activities that load successfully as approved; a raw index entry is never treated as approved. Add a separate preview load that checks the file's fingerprints but not the approvals, for the educator view only, and returns a distinct draft type that the live session refuses. The draft car activity has blank picture hashes, so the preview load checks its pictures against the generated index instead; the approved loader stays as strict as it is.
3. **Learning plans in the educator view.** *(Built.)* The educator plans only in the app, never in files. A **Learning plans** tab holds an interest, a goal, and 3–12 activities in teaching order (start from, idea to learn, why it's a good next step, big question), and an **activity card** form for each activity, with "Still missing" notes. Plans are saved on the home server in `~/.lerni/student/plans/` (or `$LERNI_STUDENT_DATA`), one JSON file each, written atomically and archived rather than deleted. They are curriculum, not student data. Two examples (cars and sharks) are copied in when the store is empty, for the educator to edit or copy. A **Guide** tab holds the educator's instructions, so the educator never needs the repository. Core: `src/lerni/student/plans.py`; screens: `src/lerni/student/web/educator.py` and `guide.md`.
4. **Import a rough plan with Claude.** *(Built; a real call is made in step 6.)* In the Learning plans tab the educator pastes notes in any shape or uploads a .txt, .md, .docx, or .pdf; Claude proposes a structured plan (filling activity cards only where the notes already have details); the educator saves or discards it, and nothing is saved before that. A required checkbox confirms the notes go to Claude (Anthropic) and contain no names or personal details. For the prototype the call goes through the Claude Code CLI on the home server and the Claude account it's logged into (no API key): no tools, no settings or CLAUDE.md files, an empty working folder, and for a PDF, permission to read only that file. An API-key adapter replaces it before anyone outside the household uses the app. Core: `src/lerni/student/plan_import.py`; adapter: `src/lerni/student/adapters/claude_code.py`.
5. **Accounts and one sign-in.** *(Built; [step plan](release-1-step-5-accounts.md).)* Student accounts (`students.py`); our own sign-in page and signed cookie, re-checked on every request through Gradio's `auth_dependency`; one app with tabs by role; educator access as a flag on a person's independent account (no passcode), with `lerni student` for the first educator and recovery; the Students tab; wrong-password delays; "Signed in as" and Sign out (this device only); the in-app guide. Independent students get only Learn (empty) and My account until step 6 scopes plans. Done when, on the admin's own device (or a private tab), Safari saves the password and a reload and a Safari restart keep them signed in; an archive or reset signs out a second device at once; and the educator sees the educator tabs.
6. **Plan my own.** Independent students get Guide, Learning plans (scoped to their own plans), and Explore freely in My account; plan schema v2 (`owner`, `approval`, `drafted_by`), set only by the server; the adapter's transcript saving off; the import's audience and Explore freely instructions; start from an example; "This is ready" self-approval; the first real Claude import; and the [import evals](specs/03-student-accounts.md#evals-for-the-claude-import). Done when the admin turns on Explore freely, imports their own interests, gets full cards, and the evals pass.
7. **Play a card.** `card_activity.py` checks that a card is complete and may play for this viewer, and builds a playable activity; `controller.py` holds one session per signed-in student; the Learn tab and the activity screens (question, picture description, large choices, hints, reveal, completion). Done when the admin does their own activity end to end on their own device. The controller keeps this contract:
   - Each session has an ID and a generation number that Start and Reset increase. Every tap carries the session ID, the generation, the state revision it was drawn from, and a request ID.
   - A tap is applied only if all four match the current session and the request ID is new. Anything else (late, repeated, from an earlier session, or from a screen drawn before Stop) is ignored.
   - Each update is atomic: one lock around read, transition, and write, because Gradio can run separate event handlers at the same time.
   - Stop: once it commits, the server accepts no more input, and the student screen shows Stop within 2 seconds (the refresh interval sets this; test it on the real iPad). A response drawn from an older state never redraws the screen after Stop or Reset. The recap stays in memory until the educator dismisses it. Reset discards the session and the recap, and so does a server restart. Because the session lives on the server, reloading either page shows the live session again; a page that disconnects stops receiving updates and shows the live session (or the waiting screen) when it reconnects.
   - No session state or progress is written to disk or browser storage, and logs hold no learner content.
   - Preview sessions are separate from the live session. Preview while an activity is live either runs in isolation or is refused; the live session never changes.
   - One session per student account, open device or not; any device signed in as that student shows and drives it, and two students never affect each other.
8. **The supervised path.** The educator's Sessions tab with Start, Stop, Reset, and the recap for a supervised student; the four checks recorded in the app on library cards, tied to the content hash; trying a card before approving it, only on the educator's own sign-in. The supervised student's screen refreshes on a short timer so that Stop takes effect without a tap. Done when the educator runs a supervised student's session on the iPad from their own device.

Gradio is an optional extra (`pip install -e ".[student]"`), never a core dependency. `students.py`, `card_activity.py`, and `controller.py` go in `src/lerni/student/` (standard library only); the screens go in `src/lerni/student/web/`, the only place that imports Gradio.

## Tests

Use fakes and synthetic activities; no network. Keep them minimal (CLAUDE.md rule 4); the list for steps 5–8 is in the [design](specs/03-student-accounts.md#tests). Cover:

- an activity plays only with the right approval for the viewer (or that student's own Explore freely), and incomplete or altered cards never play;
- every engine path through the screen: right, wrong with hints, hints exhausted;
- two taps at once, a tap racing Stop or Reset, repeated and late taps, reload, and disconnect;
- the educator controlling a supervised student's screen; every request refused without a sign-in, and every educator action refused for a student;
- a student never reaching another student's plans or sessions;
- a card the educator is trying never reaching a student's screen, even while a session is live;
- Stop shown on the iPad within the bound, including Stop between refreshes, delayed or reordered responses, and disconnect then reconnect;
- the core modules importing nothing outside the standard library and `lerni.student`;
- no session state or progress saved to disk or browser storage, no learner content in logs, and no outbound requests from the activity screens.

## Before a supervised student uses it

- The educator approves one library card in the app (the cars example's car card is the quickest; its science can be checked with the [review sheet](runbooks/chain-1-source-review.md)).
- The educator rehearses the whole activity on the iPad and their own device, including Stop and Reset, then authorizes student use.

## Not in this release

Voice, AI replies to the student, remembering, playing packaged activities, assigning plans to particular students, HTTPS, hosting outside the home, spreadsheet import, and suggestions.
