# Supervised and independent students, with sign-in

Design for the rest of Release 1. Approved 2026-10-09, then revised the same day after two outside reviews of PR #7, and again when step 5 was tried: the educator became a permission on a person's account, and the passcode went away. The PRDs carry these decisions (a PRD wins where they disagree); the [MVP plan](../release-1-mvp.md) carries the steps.

## Why

Lerni serves two kinds of student, not one. The educator and admin should use the app as learners now, on topics of their own, without the limits a supervised student needs. Their sessions test the shared core (activities, screens, Claude import) before a supervised student relies on it. The first real use: the admin imports their own interests and works through them.

## Who

The roles stay **student**, **educator**, and **admin**. A student is one of two kinds, set by supervision, not age:

- **Supervised student:** an educator approves their content and controls their sessions. Often a child; that's an example, not the definition.
- **Independent student:** their own educator. They plan, import with Claude, approve (or choose not to), and learn on their own. Often an adult.

One person can hold several roles: the admin and the educator can each have an independent student account. Vocabulary rule 1 still holds; docs say "supervised student" and "independent student", never child or adult.

| | Supervised student | Independent student |
|---|---|---|
| Sign in | Username and password | Same |
| Plans | The educator's **library** (the educator's own plans, `owner` blank); they see every educator-approved card in it | Their own, in the same **Learning plans** tab, scoped to them: import, edit, approve |
| Who approves an activity | The educator, with the four checks | The student ("This is ready"), or nobody for their own plans while their **Explore freely** is on |
| Topics | The educator's allowlist; sensitive topics wait for consent | Anything |
| Sessions | The educator starts, stops, and resets them | Self-paced; they start and stop |
| Settings and outside-service consent | The educator's | Their own |
| Activities, engine, screens | Shared | Shared |

### Who can do what

| Who | Can | Can't |
|---|---|---|
| Admin | Everything an educator can, plus run the server, read every file on it, and add or recover accounts from the terminal (`lerni student`), including the first educator | Write an approval for anyone else (rule 5) |
| Educator (an independent account with educator access) | Everything an independent student can, plus manage every account (add, reset password, archive); plan the library; approve library cards; run supervised students' sessions | See another independent student's plans or sessions in any screen |
| Independent student | Plan, import, approve, and play their own plans; change their own name, password, and Explore freely | See or touch anyone else's plans, sessions, or account; use Students or Sessions |
| Supervised student | Play the library's educator-approved cards when the educator starts them | Plan, approve, change settings, or see anyone else's sessions |

**Privacy is by default, not a protection.** No educator screen shows an independent student's plans or sessions, but the educator is trusted with account recovery: a password reset lets them sign in as that student (who notices, because their password stops working), and the admin can read every file on the home server.

### Guarantees

Every existing supervised-student guarantee stays. For every student:

- **May play:** an activity plays for a student only with the educator's four checks (a supervised student, library cards), the independent student's own "This is ready" (their own plans), or that student's own Explore freely (their own plans, labeled unchecked). Never anyone else's approval, never anyone else's plan.
- Nothing is sent to an outside service without consent at the moment of sending.
- Logs hold no learner content; session state and progress are never written to disk or browser storage.
- A student never sees another student's plans or sessions.
- **Designed for touch first:** a goal, not an absolute. Voice arrives in Release 3.

### Devices

Boundaries apply to accounts; which person holds a device is a household rule:

- A supervised student's iPad is signed in only as that student. Never save an independent or `educator` password in its browser.
- The admin and educator dogfood on their own devices, or in a private tab, and sign out after.
- Every screen shows "Signed in as <display name> · <kind>" next to **Sign out**, so the wrong account is obvious.

## One app, one sign-in, tabs by role

Now that everyone signs in, the two-app split (a student screen with no login beside a passcode-protected educator view) has no reason to stay. The app becomes **one Gradio app**, and the tabs depend on who signed in:

| Signed in as | Tabs |
|---|---|
| Supervised student | Learn |
| Independent student | Guide · Learn · Learning plans · My account |
| Educator (an independent student with educator access) | Learn · Guide · Sessions · Learning plans · Students · My account |

An independent student gets the educator's planning tabs applied to themselves, plus Learn, and switches tabs to move between learning and planning. They don't get **Sessions** (it controls a supervised student's session from another device) or **Students** (a reset would let one independent student sign in as another). An educator is a person with an independent account plus educator access, so one sign-in gives them both their own learning and the family's planning; they open on the Guide.

### Sign-in: our own page, checked on every request

Gradio's built-in login is checked only once, at sign-in; afterward Gradio trusts an in-memory token, so an archive or reset wouldn't reach a device already signed in. Its login page is also not a real HTML form, so Safari and Keychain are unlikely to save it, and its cookie dies with the Safari process. So the app uses its own small sign-in page with Gradio's documented `auth_dependency`, which runs on every request:

- **The page:** `/signin` serves a plain HTML form (`name="username" autocomplete="username"`, `name="password" autocomplete="current-password"`) that posts normally (not by script). That is what Safari and Keychain look for. Step 5 confirms saving and autofill on the real iPad.
- **The cookie:** a correct sign-in sets `lerni_session` = username, issue date, and the account's `session_version`, signed with HMAC-SHA256 (`hmac`, standard library) using a server secret kept in `~/.lerni/student/secret.key` (created on first start, readable only by the server's user). `HttpOnly`, `SameSite=Lax`, a 30-day lifetime, so a reload or a Safari restart keeps you signed in. Not `Secure` until HTTPS (Release 3).
- **Every request:** `auth_dependency(request)` verifies the signature, re-reads the account record, and returns the username only if the account exists, isn't archived, and its `session_version` still matches. Otherwise the request gets nothing and the browser goes back to `/signin`. So **archive and password reset apply at once on every device**: both bump `session_version`.
- **Routes:** Gradio is mounted at `/app/`; `/` sends you to `/app/` if signed in, else to `/signin`. Step 5 confirms how Gradio answers an unauthenticated request under `auth_dependency`.
- **Sign out** clears this device's cookie only. A server restart doesn't sign anyone out (the secret is on disk).
- **Who's signed in:** every handler takes `request: gr.Request`, resolves `request.username` to the account record (never to anything the page sends), and scopes what it reads and writes. **Any plan, activity, or student id from the page is checked against the signed-in user before use.** Hiding a tab or component is only for looks. `api_visibility="private"` hides events from the API page but doesn't block a direct request; the handler check is the control.
- **Nothing per-user in the layout:** Gradio sends every signed-in browser the same page config, including hidden tabs' initial values. So no plan list, title, username, or other data is built into the layout; role-scoped values load per request (`demo.load` with `gr.Request`).
- **Files:** Gradio serves cached files to any signed-in user who knows the URL. Release 1 accepts that: pictures are curriculum, cards have none, and uploads are deleted right after reading.

### Accounts and passwords

- **Usernames** match `^[a-z][a-z0-9-]{1,30}$`. Sign-in and creation refuse anything not already in that form (never lowercase-and-accept). Reserved: `educator`, `admin`. Usernames are never reused: an archived account keeps its file with `archived: true`.
- **Passwords:** at least 8 characters for independent accounts (educators included), 4 for supervised ones. Stored as `hashlib.scrypt` (n=2^15, r=8, p=3, a 16-byte salt from `os.urandom`, `maxmem` raised to fit), checked with `hmac.compare_digest`.
- **Changing a password** in My account needs the current password. The educator's reset doesn't.
- **Wrong passwords:** after 3 wrong passwords for a username, each further attempt waits longer before it's checked (1, 2, 4, … up to 30 seconds), and the right password resets it. Attempts during a wait don't extend it. It's held in memory, for known usernames and `educator` only (unknown names just get a fixed delay), and never touches sessions already signed in, so the educator's Stop keeps working.
- **Educator access** is a flag on an independent account (`educator: true`), set by an educator in Students or by the admin with `lerni student educator`. Supervised accounts can't have it. Changing it bumps `session_version`.
- **First start:** there are no accounts, so nobody can sign in; the sign-in page says so. The admin runs `lerni student add USERNAME --name NAME --kind independent --educator` on the home server (password at a hidden prompt), and that educator adds everyone else in the app. `lerni student reset-password` is the recovery path.

The `/educator/` route and the educator passcode (`LERNI_EDUCATOR_PASSCODE`) go away; `lerni serve` needs no secret typed at start.

## Data

Everything lives on the home server under `~/.lerni/student/` (or `$LERNI_STUDENT_DATA`), in JSON files written atomically, like plans today. The atomic-write code moves out of `PlanStore` into one shared helper. Plans archive by moving the file; accounts archive in place.

**`students/<username>.json`** (new):

| Field | Meaning |
|---|---|
| `username` | Matches the username rule; also the file name |
| `display_name` | What the screens show; a nickname is fine |
| `kind` | `supervised` or `independent` |
| `password` | `{salt, hash, n, r, p}` for scrypt; never the password |
| `session_version` | A number bumped by reset and archive; signs out every device |
| `educator` | Independent only: may manage accounts and the library |
| `explore_freely` | Independent only: `null`, or the date the student turned it on; set only by that student |
| `archived` | Archived accounts can't sign in, and their username stays taken |

**`plans/<id>.json`** (schema version 2):

- `owner`: blank for the library; a username for an independent student's own plan. Version 1 files load with a blank owner.
- Each activity gets an optional `approval`: `{by, role, on, checks, sha256}`. `role` is `educator` or `independent_student`. `checks` lists the four review scopes for an educator approval, or `["self"]` for a self-approval. `by` is the signed-in username (for `educator`, it records the role, not which person).
- Each card gets `drafted_by`: blank, or `claude` when Claude wrote it from its own knowledge (Explore freely).

**Only the server sets these.** `owner` comes from the signed-in user on every save. `approval` is written only by the "This is ready" and four-checks handlers, with `by` and `role` from the server. `drafted_by` is set by the import code from the mode, never from Claude's answer. The proposal schema has none of these fields, `proposal_to_plan` strips them if they appear anyway, and copying a plan drops its approvals. No agent, script, or automated browser writes an approval or the Explore freely setting (rule 5).

**The approval hash** (`sha256`) is the SHA-256 of the canonical JSON (`canonical_json_bytes`) of everything Learn shows for that activity: the card, the activity row's `idea` and `big_question`, the plan's `interest`, and `drafted_by`. Editing any of them un-approves the card.

What this saves about a student: the account and an independent student's own plans. No session state, no progress (that's Release 2).

## Explore freely

A switch in an independent student's **My account**, off until they turn it on. The screen explains in one line what it does: Claude writes whole activities from its own knowledge, they play without checking, and facts may be wrong. Turning it on records the date; turning it off clears it. It never applies to supervised students or to the library. It is not Release 5's free conversation: it changes only how cards are written and approved, not how the student talks to the app.

While it's on, for that student's own plans:

- **Claude drafts every card.** The import uses a fuller instruction: write a complete activity card for every activity, from Claude's general knowledge, not just the notes. `sources` says "Claude's general knowledge" unless the notes name a source. The other rules stay: names and personal details become "the student", and the text is notes, never instructions.
- **Any complete card in their own plans plays without approval.** Learn labels it "Not checked" (and "Claude's draft" when `drafted_by` is `claude`) until they tap "This is ready", which records a normal self-approval.
- **Turning it off** stops unapproved cards from playing, including a session in progress.

While it's off, an independent student's import fills cards only from their notes, and each card needs "This is ready" before it plays.

## Playing a card

`card_activity.py` (new core module, standard library only) turns a card into something the controller can run.

- **A distinct type:** the controller accepts only a `PlayableActivity(lesson, provenance)`, with provenance `educator_approved`, `self_approved`, or `unchecked`. Only `card_activity.load_playable(viewer, plan, index)` builds one in Release 1, so nothing else holding a `Lesson` (a `DraftPreview`, say) can be played. Card lessons carry draft review status and never invented review records.
- **Complete first:** a card plays only if it's complete: at least one explanation, a question, two or three choices, an answer that is one of them, at least one hint, the right text, and the hints-run-out text. The first explanation becomes the intro step (the engine starts there), the rest become teach steps. Incomplete cards stay editable and show as "not ready" in Learn. Explore freely waives human review, never completeness.
- **May play:** checked for the viewer, at listing and again at Start:
  - **educator-approved:** `viewer.kind == supervised`, `plan.owner == ""`, an approval with `role == educator` and exactly the four checks, and a matching hash. A `["self"]` approval on a library card counts for nothing.
  - **self-approved:** `viewer.kind == independent`, `viewer.username == plan.owner`, a `["self"]` approval by that same username, and a matching hash.
  - **unchecked:** `viewer.kind == independent`, `viewer.username == plan.owner`, and the viewer's Explore freely on.

  Anything else is refused. The educator's Start re-runs the check for the supervised student the session is for.
- **Grounding:** the engine doesn't read grounded facts, so a card's lesson carries an empty bundle and its sources text.
- **Packaged activities:** the TOML catalog (the car activity) stays as it is, for curated content later. Release 1 doesn't play packaged activities: the supervised student's first activity is a library card (the cars example's fourth activity already carries the car card). The catalog remains the only place packaged approvals are checked; `card_activity.py` checks card approvals.

## Sessions

`controller.py` (new core module, standard library only) holds **one session per student account**, in memory, whether or not a device is open. Any device signed in as that student shows and drives it. It keeps the tap-guard contract from the MVP plan:

- every tap carries a session id, generation, state revision, and request id, and is applied only if all four match;
- one lock covers read, transition, and write;
- Stop takes effect within the refresh interval;
- nothing goes to disk or browser storage.

A supervised student's session is started, stopped, and reset only from the educator's Sessions tab, and the educator dismisses its recap. An independent student starts, stops, and dismisses their own. A server restart discards all sessions. Archiving an account, or turning off Explore freely during an unchecked session, stops that session.

## Tabs

**Learn** (both kinds of student): the activities that may play for this viewer, grouped by plan, plus incomplete ones marked "not ready" for an independent student's own plans. Tapping one starts it (independent), or shows "Waiting for your educator" until the educator starts it (supervised). Then the activity screens: question, picture description, large choices, hints, reveal, completion. The answer key and sources stay on the server here; an independent student sees their own answers only in Learning plans, where they wrote them.

**Learning plans, for an independent student:** the same tab the educator uses (plan table, card form, Claude import), scoped on the server to the student's own plans, plus:

- **Start from an example:** copy a library example into their own plans (owner set to them, approvals dropped).
- **This is ready:** the one-step self-approval for a card.

**My account** (independent students): display name, password (needs the current one), and the Explore freely switch.

**Educator tabs:**

- **Guide:** as today, plus the two kinds of student. Independent students see the same tab, with a short part on planning your own learning.
- **Students** (new): add a student (username, display name, kind, starting password), reset password, and archive. Independent students appear by name and kind only.
- **Sessions:** a supervised student's sessions, with Start, Stop, Reset, and recap. Built in step 8.
- **Learning plans:** the library only, plus the four checks for a card (step 8).

**The Claude import** is the same code for the educator and for an independent student. The instructions name the audience: a plan for a supervised student is designed for ages 7–9, as today; a plan for an independent student is for an independent learner (often an adult) choosing their own topic, with the fuller instruction when Explore freely is on. The consent checkbox stays required, and names the account used: "Send this to Claude (Anthropic), through the admin's Claude account, to structure it. I've left out names and anything I don't want to share." The adapter turns off Claude Code's session saving (`--no-session-persistence`), so imported notes aren't kept in the admin's Claude transcripts.

## Build order

One PR per unit, in order, each from `main` (the running list: [to-do](../../docs/todo.md#upcoming-prs)).

| PR | What | Done when |
|---|---|---|
| Docs | Reframe README, the three PRDs, ARCHITECTURE, CLAUDE.md, roadmap, MVP plan, todo, and progress | The admin reviews and merges it |
| Step 5 | Accounts and one sign-in: `students.py`, the shared JSON-store helper, the sign-in page and signed cookie, one app with tabs by role, the Students tab, wrong-password delays, Sign out, "Signed in as", the in-app guide. Independent students get only Learn (empty) and My account until step 6 scopes plans. | On the admin's own device (or a private tab), Safari saves the password and a reload and a Safari restart keep them signed in; an archive or reset signs out a second device at once; the educator sees the educator tabs |
| Step 6 | Plan my own: Guide and Learning plans for independent students, scoped to their own plans; plan schema v2 (`owner`, `approval`, `drafted_by`), set only by the server; the import's audience and Explore freely instructions; start from an example; self-approval; Explore freely in My account; no Claude Code transcripts; the first real Claude import; the import evals | The admin turns on Explore freely, imports their own interests, and gets full cards; the evals pass |
| Step 7 | Play a card: `card_activity.py`, `controller.py`, the Learn tab and activity screens | **The admin does their own activity end to end, on their own device** |
| Step 8 | Supervised path: the educator's Start, Stop, Reset, and recap; the four checks on library cards in the app | The educator runs a supervised student's session on the iPad from their own device |

## Code that changes

- `web/app.py`: one app behind the sign-in page instead of two; the waiting screen's "Waiting for your educator to start" shows only to supervised students (steps 5 and 7).
- `plan_import.py`: `SYSTEM_PROMPT`'s fixed "designed for ages 7-9" becomes per audience, with an Explore freely variant; `proposal_to_plan` sets server fields after, not before, the proposal and strips any it finds (step 6).
- `adapters/claude_code.py`: passes `--no-session-persistence` (step 6).
- `educator.py`: handlers take the signed-in account, check every id from the page against it, scope by owner, and load lists per request (steps 5 and 6). Its import help text loses "kids'" (step 5).
- `guide.md`: the Students tab and the two kinds of student (step 5), then each later step.
- `docs/code-manifest.md` lists each new file in the PR that adds it.

## Tests

Minimal, per CLAUDE.md rule 4: one happy path per new module, plus one test per safety guarantee, all with fakes:

- `students.py`: an account saves, loads, and checks its password; non-canonical, reserved, and archived usernames are refused at creation and sign-in.
- Sign-in: a request without a valid cookie gets nothing; a reset or archive refuses an existing cookie on its next request; wrong passwords are delayed while a signed-in session keeps working; a password change without the current password is refused.
- Scoping: fetching, copying, saving, or archiving another owner's plan by id is refused; the educator's plan list leaves out independent students' plans; a student's request to an educator action is refused; the page config for a supervised student contains no plan ids, titles, or usernames.
- Plans: a version 1 file still loads (blank owner); a fake drafter's `owner`, `approval`, or `drafted_by` is dropped.
- `card_activity.py`: a complete approved card plays; an incomplete card, a card whose answer isn't a choice, and an edited card don't; an unchecked card plays only for its owner with Explore freely on; a library card without the educator's four checks is refused for a supervised student; the educator's Start with an independent student's activity is refused.
- `controller.py`: one happy path; a stale tap is ignored; two students' sessions don't affect each other.
- The adapter's options include `--no-session-persistence`.

## Evals for the Claude import

Tests check our code with a fake Claude; evals check Claude's actual answers. Explore freely lets Claude-written cards play unchecked, so step 6 adds a small eval set before you rely on it.

- **Where:** `evals/plan_import/cases/*.json` (inputs and expectations) and `scripts/run_plan_import_evals.py`, which sends each case through the real drafter and prints a pass/fail table. Nothing is saved.
- **When:** by hand, whenever the import instructions, schema, or model change. Never in `pytest` (rule 4), never in the commit gate. Each run uses some of the Claude plan, so the script says how many calls it will make and asks first.
- **Cases (about 12, all synthetic, nothing real; rule 8):** thin notes (one line), messy notes, a full plan with card details, notes with a made-up name and birthday, notes containing "ignore your instructions", notes asking for `owner` or approvals, the same notes for a supervised and an independent audience, an Explore freely topic, a PDF, and a few topics with known answers.
- **Checks in code:** the answer fits the schema and loads as a plan; no name from the input appears in the output; the injected instruction isn't followed and no server field appears; sources stay empty unless the notes name one (Explore freely: "Claude's general knowledge"); outside Explore freely, cards appear only where the notes had details; up to 3 "Question:" notes; known-answer cases get the answer right.
- **Checks graded by Claude** against a short rubric, pass or fail with a reason: suits the audience, keeps the educator's wording, activities build in a sensible order, facts plausible.
- **Pass bar:** every code check passes; rubric checks pass on at least 9 of 10 graded cases. The admin reads the first run's output by hand. A failure is fixed in the instructions, and the case stays as a regression.
- **Limits:** "plausible" isn't "accurate"; a passing run is a smoke test, not fact-checking, and it never approves anything for a supervised student.

An agent with tools (reading the plan, checking the allowlist, giving hints) comes with the Release 3 conversation, and its evals grow from this set.

## Not in this design

- Tap-a-name tiles; password recovery beyond the educator's reset; a "which device is signed in as whom" view.
- Asking Claude to draft one card at a time after import; import is the only way Claude writes cards for now.
- Free conversation for anyone; it stays with Releases 3 and 5.
- An agent with tools, and Agent Skills inside the app. The app's Claude calls stay single structured calls with no tools or skills until the Release 3 plan.
- Progress or memory (Release 2).
- Playing packaged activities, and recording their approvals in the app.
- Assigning plans to particular students. Supervised students see every educator-approved library card; independent students copy an example. Add an optional `assigned_plans` field (missing means all) once an educator has more than one supervised student.
- Hosting outside the home. It's still one household on the home Wi-Fi; passwords keep students apart, they don't make the app safe to expose.

## Open questions

- Does Safari save and fill the sign-in form on the iPad, and keep the cookie across a Safari restart? Step 5 checks.
- How does Gradio answer an unauthenticated request under `auth_dependency` (redirect or 401)? Step 5 checks, and `/` handles the redirect either way.
