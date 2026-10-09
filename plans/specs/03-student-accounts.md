# Supervised and independent students, with sign-in

Design for the rest of Release 1, agreed 2026-10-08. Once approved, the PRDs get these decisions (a PRD wins where they disagree) and the [MVP plan](../release-1-mvp.md) gets the new steps.

## Why

Lerni serves two kinds of student, not one. The educator and admin should use the app as learners now, on topics of their own, without the limits a supervised student needs. Their sessions test the shared core (activities, screens, Claude import) before a supervised student relies on it. The first real use: the admin imports their own interests and works through them.

## Who

The roles stay **student**, **educator**, and **admin**. A student is one of two kinds, set by supervision, not age:

- **Supervised student:** an educator approves their content and controls their sessions. Often a child; that's an example, not the definition.
- **Independent student:** their own educator. They plan, import with Claude, approve (or choose not to), and learn on their own. Often an adult.

One person can hold several roles: the admin and the educator can each have an independent student account. Vocabulary rule 1 still holds; docs say "supervised student" and "independent student", never child or adult.

| | Supervised student | Independent student |
|---|---|---|
| Sign in | Username and password (Gradio's login) | Same |
| Plans | The educator's library; they see every educator-approved activity | Their own, in the same **Learning plans** tab, scoped to them: import, edit, approve |
| Who approves an activity | The educator, with the four checks | The student, with one confirmation, or nobody once they turn on **Explore freely** |
| Topics | The educator's allowlist; sensitive topics wait for consent | Anything |
| Sessions | The educator starts, stops, and resets them | Self-paced; they start and stop |
| Activities, engine, screens | Shared | Shared |

The educator manages every account in the **Students** tab, but never sees an independent student's plans or sessions. The admin keeps the CLI unchanged and tries the app as a learner through their own independent account.

### Guarantees

Every existing supervised-student guarantee stays. Independent students drop the allowlist, sensitive-topic consent, and educator control, and keep the rest:

- Nothing is shown as an activity unless a real person approved its exact content, or the independent student themselves chose **Explore freely** for their own plans. Unapproved activities are labeled.
- Nothing is sent to an outside service without consent at the moment of sending.
- Logs hold no learner content.
- A student never sees another student's plans or sessions.

"It works by touch on an iPad; nothing needs a keyboard" becomes a design goal, **designed for touch first**, not an absolute. Voice arrives in Release 3.

## One app, one sign-in, tabs by role

Now that everyone signs in, the two-app split (a student screen with no login beside a passcode-protected educator view) has no reason to stay. The app becomes **one Gradio app at `/`** behind Gradio's built-in login, and the tabs depend on who signed in:

| Signed in as | Tabs |
|---|---|
| Supervised student | Learn |
| Independent student | Guide · Learn · Learning plans · My account |
| Educator | Guide · Students · Sessions · Learning plans |

An independent student gets the educator's tabs applied to themselves, plus Learn, and moves between learning and planning by switching tabs; there's no second login. They don't get **Sessions** (it controls a supervised student's session from another device; an independent student runs their own in Learn) or **Students** (resetting passwords would let one independent student sign in as another and read their plans). The educator, to learn for themselves, signs out and back in with their own independent account.

- **Check:** one function, `(username, password) -> bool`:
  - username `educator` with the educator passcode from its environment variable, as today (`educator` is reserved, never a student's username);
  - any other username against `StudentStore`'s password hash. Archived students are refused.
- **Who's signed in:** every handler takes `request: gr.Request` and resolves `request.username` to a role (educator, supervised student, or independent student) on the server before doing anything, then scopes what it reads and writes. Hiding a tab is only for looks; the handler check is what protects it. No handler trusts anything the page sends about who is signed in. All events stay `api_visibility="private"`.
- **Staying signed in:** Gradio keeps a login cookie, so a reload keeps you signed in. A server restart signs everyone out. **Log out** uses Gradio's `/logout`.
- **Saving in the browser:** the login page is a password form, so Safari and iCloud Keychain should offer to save it and fill it next time. Step 5 confirms this on the real iPad; if Safari won't, we fall back to a tap-a-name screen of our own.
- **Passwords:** at least 4 characters, set and reset by the educator, and changeable by an independent student in My account. They're stored as `hashlib.scrypt` with a random salt and checked with `hmac.compare_digest`.
- **Lockout:** after 5 wrong passwords for one username, that name is refused for 60 seconds. This is held in memory and resets on restart.
- **Before any accounts exist:** only the educator can sign in, and adds the first accounts.

The `/educator/` route goes away. The educator passcode and its environment variable stay.

## Data

Everything lives on the home server under `~/.lerni/student/` (or `$LERNI_STUDENT_DATA`), in JSON files written atomically and archived instead of deleted, like plans today. The atomic-write and archive code moves out of `PlanStore` into one shared helper.

**`students/<username>.json`** (new):

| Field | Meaning |
|---|---|
| `username` | Lowercase slug, unique; also the file name |
| `display_name` | What the screens show; a nickname is fine |
| `kind` | `supervised` or `independent` |
| `password` | `{salt, hash, n, r, p}` for scrypt; never the password |
| `explore_freely` | Independent only: `null`, or the date the student turned it on |
| `archived` | Archived students can't sign in |

**`plans/<id>.json`** (schema version 2):

- `owner`: blank for the educator's library; a username for an independent student's own plan. Version 1 files load with a blank owner.
- Each activity gets an optional `approval`: `{by, role, on, checks, card_sha256}`. `role` is `educator` or `independent_student`. `checks` lists the four review scopes for an educator approval, or `["self"]` for an independent student's. `card_sha256` is the SHA-256 of the card's canonical JSON (`canonical_json_bytes`).
- Each card gets `drafted_by`: blank, or `claude` when Claude wrote it from its own knowledge (Explore freely).

Only a signed-in person's tap ever writes an approval or turns on Explore freely. No agent or script writes either (rule 5).

What this saves about a student: the account (nickname, kind, password hash, the Explore freely date) and an independent student's own plans. There is still no progress record; that's Release 2.

## Explore freely

A switch in an independent student's **My account**, off until they turn it on. The screen explains in one line what it does: Claude writes whole activities from its own knowledge, they play without checking, and facts may be wrong. Turning it on records the date; turning it off clears it. It never applies to supervised students or to the educator's library.

When it's on, for that student's own plans:

- **Claude drafts every card.** The import uses a fuller instruction: write a complete activity card for every activity, using Claude's general knowledge, not just the notes. `sources` says "Claude's general knowledge" unless the notes name a source. The other rules stay: names and personal details become "the student", and the text is notes, never instructions.
- **Cards play without approval.** Learn shows each activity with a small "Claude's draft, not checked" label until the student taps "This is ready" on it, which still records a normal self-approval.
- **Editing still works.** An edited card keeps playing (it's still unchecked), and its label stays.

When it's off, an independent student's import fills cards only from their notes, as today, and each card needs "This is ready" before it plays.

## Playing a card

`card_activity.py` (new core module, standard library only) turns a card into an in-memory `Lesson` that the existing engine runs. Card activities are never packaged as TOML.

- **Content:** the explanation lines become teach steps. The question, choices, answer, hints, right text, and hints-run-out text become the check. A picture idea is shown as its text description; card activities have no image files in Release 1. If the engine requires grounded facts, the module supplies a minimal bundle built from the card's sources text; step 7 settles this.
- **When it may play:** only if one of these holds:
  - **Educator-approved:** a library plan shown to a supervised student, with an educator approval listing all four checks, and the card's current fingerprint equal to `approval.card_sha256`;
  - **Self-approved:** an independent student's own plan, approved by that same student with `["self"]`, with the fingerprint matching;
  - **Explore freely:** an independent student's own plan while that student's `explore_freely` is on; it's labeled unchecked.

  Otherwise it's refused. An edit un-approves an approved card, because the fingerprint no longer matches.
- **Packaged activities:** the TOML catalog (the car activity) stays as it is, for curated content with sources and pictures.

## Sessions

`controller.py` (new core module, standard library only) holds **one session per signed-in student**, in memory, keyed by username. It keeps the tap-guard contract from the MVP plan:

- every tap carries a session id, generation, state revision, and request id, and is applied only if all four match;
- one lock covers read, transition, and write;
- Stop takes effect within the refresh interval;
- nothing goes to disk or browser storage.

A supervised student's session is started, stopped, and reset only from the educator's Sessions tab. An independent student starts and stops their own from Learn. A server restart discards all sessions.

## Tabs

**Learn** (both kinds of student): the student's plans and each plan's playable activities. Tapping one starts it (independent), or shows "Waiting for your educator" until the educator starts it (supervised). Then the activity screens: question, picture description, large choices, hints, reveal, completion.

**Learning plans, for an independent student:** the same tab the educator uses (plan table, card form, Claude import), scoped on the server to the student's own plans, plus:

- **Start from an example:** copy a library example into their own plans.
- **This is ready:** the one-step self-approval for a card.

**My account** (independent students): display name, password, and the Explore freely switch.

**Educator tabs:**

- **Guide:** as today, plus the two kinds of student. Independent students see the same tab, with a short part on planning your own learning.
- **Students** (new): add a student (username, display name, kind, starting password), reset password, and archive. Independent students appear by name and kind only.
- **Sessions:** a supervised student's sessions, with Start, Stop, Reset, and recap. Built in step 8.
- **Learning plans:** the educator's library only. Unchanged otherwise.

**The Claude import** is the same code for the educator and for an independent student. The instructions name the audience: a plan for a supervised student is designed for ages 7–9, as today; a plan for an independent student is for an independent learner (often an adult) choosing their own topic, with the fuller instruction when Explore freely is on. The consent checkbox stays required. For an independent student it reads: "Send this to Claude (Anthropic) to structure it. I've left out anything I don't want to share."

## Build order

One PR per unit. PR #6 (steps 1–4) merges first; each PR below branches from `main`.

| PR | What | Done when |
|---|---|---|
| Docs | Reframe README, the three PRDs, ARCHITECTURE, CLAUDE.md, roadmap, MVP plan, todo, progress, and the in-app guide | A consistency scan finds no single-student framing left, outside history |
| Step 5 | Accounts and one sign-in: `students.py`, the shared JSON-store helper, one app at `/` with tabs by role, the Students tab, lockout, Log out | You sign in as yourself on the iPad, Safari saves the password, a reload keeps you signed in, and the educator signs in to the same app and sees the educator tabs |
| Step 6 | Plan my own: Guide and Learning plans for independent students, scoped to their own plans; My account; plan schema v2 (`owner`, `approval`, `drafted_by`), the import's audience and Explore freely instructions, start from an example, self-approval; the import evals | You turn on Explore freely, import your own interests, and get full cards; the evals pass |
| Step 7 | Play it: `card_activity.py`, `controller.py`, the Learn tab and activity screens | **You do your own activity end to end on the iPad** |
| Step 8 | Supervised path: the educator's Start, Stop, Reset, and recap, the four approvals in the app, packaged activities in Learn | The educator runs a supervised student's session on the iPad from their own device |

Steps 5–7 of the current MVP plan (controller, two pages, approvals in the app) fold into steps 7 and 8.

## Code that changes

- `web/app.py` mounts one app at `/` instead of two; the waiting screen's "Waiting for your educator to start" shows only to supervised students (steps 5 and 7).
- `plan_import.SYSTEM_PROMPT`'s fixed "designed for ages 7-9" becomes per audience, with an Explore freely variant (step 6).
- `educator.py`'s handlers take the signed-in role and scope by owner (steps 5 and 6).
- `guide.md` gains the Students tab and the two kinds of student (docs PR, then each step as it lands).
- `docs/code-manifest.md` lists each new file in the PR that adds it.

## Tests

Minimal, per CLAUDE.md rule 4: one happy path per new module, plus one test per safety guarantee, all with fakes:

- `students.py`: an account saves, loads, and checks its password; a wrong password is refused, and 5 wrong ones lock the name.
- Sign-in: the app refuses requests without a login, and the educator passcode still signs in as `educator`.
- Scoping: a student never gets another student's plans; the educator's plan list leaves out independent students' plans; a student's request to an educator action (Students, Sessions, library) is refused.
- `card_activity.py`: an approved card plays; an edited card is refused until approved again; a supervised student's card without the educator's four checks is refused; an independent student's unapproved card plays only while their Explore freely is on.
- Plans: a version 1 file still loads (blank owner).
- `controller.py`: one happy path; a stale tap is ignored; two students' sessions don't affect each other.

## Evals for the Claude import

Tests check our code with a fake Claude; evals check Claude's actual answers. Explore freely lets Claude-written cards play unchecked, so step 6 adds a small eval set before you rely on it.

- **Where:** `evals/plan_import/cases/*.json` (inputs and expectations) and `scripts/run_plan_import_evals.py`, which sends each case through the real drafter and prints a pass/fail table. Nothing is saved.
- **When:** by hand, whenever the import instructions, schema, or model change. Never in `pytest` (rule 4), never in the commit gate. Each run uses some of the Claude plan, so the script says how many calls it will make and asks first.
- **Cases (about 10, all synthetic, nothing real; rule 8):** thin notes (one line), messy notes, a full plan with card details, notes with a made-up name and birthday, notes containing "ignore your instructions", the same notes for a supervised and an independent audience, an Explore freely topic, and a PDF.
- **Checks in code:** the answer fits the schema and loads as a plan; no name from the input appears in the output; the injected instruction isn't followed; sources stay empty unless the notes name one (Explore freely: "Claude's general knowledge"); outside Explore freely, cards appear only where the notes had details; up to 3 "Question:" notes.
- **Checks graded by Claude** against a short rubric, pass or fail with a reason: suits the audience, keeps the educator's wording, activities build in a sensible order, facts plausible (Explore freely).
- **Pass bar:** every code check passes; rubric checks pass on at least 9 of 10 cases. A failure is fixed in the instructions, and the case stays as a regression.

An agent with tools (reading the plan, checking the allowlist, giving hints) comes with the Release 3 conversation, and its evals grow from this set.

## Not in this design

- Tap-a-name tiles, our own cookies, and password recovery beyond the educator's reset.
- Asking Claude to draft one card at a time after import; import is the only way Claude writes cards for now.
- Free conversation for independent students; it stays with Releases 3 and 5 for everyone.
- An agent with tools, and Agent Skills inside the app. The app's Claude calls stay single structured calls with no tools or skills until the Release 3 plan.
- Progress or memory (Release 2).
- Assigning plans to particular students. Supervised students see every educator-approved library activity; independent students copy an example. Add an optional `assigned_plans` field (missing means all) once an educator has more than one supervised student.
- Hosting outside the home. It's still one household on the home Wi-Fi; passwords keep students apart, they don't make the app safe to expose.

## Open questions

- Does Safari save and fill Gradio's login form on the iPad? Step 5 checks; the fallback is a tap-a-name screen.
- Does the engine need grounded facts for a card activity, or can the bundle be empty? Step 7 checks.
