# Code manifest

What every code file does, in the order a request flows through it. When you add, remove, or rename a code file, update this list; a test fails if a file is missing here. The bigger picture is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Student app: what runs on the home server

**Starting the server**

| File | What it does |
|---|---|
| `src/lerni/commands/serve.py` | The `lerni serve` command: starts the student app, with a friendly message if Gradio isn't installed. |
| `src/lerni/student/web/serve.py` | Picks the Claude chat and tagger if the `claude` CLI is installed, builds the app, says how to add the first educator if there's none and where the logs are, and runs the web server (Ctrl-C stops it within 3 seconds). |
| `src/lerni/student/web/app.py` | Builds the server: the sign-in page, and one Gradio app at `/app/` that Gradio's `auth_dependency` re-checks on every request; wires the conversation to the map keeper (maps, tagger, logs) and purges old logs at startup. Turns off Gradio's analytics, run history, API pages, and other extras, and sets the look (system fonts, the playful waiting screen). |
| `src/lerni/student/web/signin_page.py` | The sign-in page: a plain HTML form Safari can save, the signed cookie, Sign out (this device only), and sending signed-out visits to it. |
| `src/lerni/student/web/main.py` | The one app's page: "Signed in as" with Sign out, then tabs by role on load: a supervised student's waiting screen until step 9; Ask, My map, and My account; Maps and Students for educators. Nothing per-user or from the data is built into the layout. |

**The screens** (the only code that imports Gradio)

| File | What it does |
|---|---|
| `src/lerni/student/web/educator.py` | The old Guide, Sessions, and Learning plans tabs (plan table, activity-card form, Claude import). Not shown since step 7; removed in step 10. |
| `src/lerni/student/web/ask.py` | The Ask tab for independent students: chat, one-line question box (Enter sends), a Send button that becomes Stop while answering, New conversation; one ongoing conversation per student; phone first (the chat and the box grow with content); educators can try the supervised-student voice. The role is checked on the server. |
| `src/lerni/student/web/maps.py` | My map and Maps: the picture, the list, Add goal, Rename, Remove; the username a page asks for is checked against the viewer (Maps shows only supervised students); Maps redraws every 30 seconds. |
| `src/lerni/student/web/mapdraw.py` | Draws a map as inline SVG (at most 15 entries in a stable ring, three sizes, color-blind-safe green and coral, dashed bridges, every name escaped) and says the same in words. |
| `src/lerni/student/web/accounts.py` | The Students tab (add, reset password, archive) and an independent student's My account (name, and password with the current one); handlers take the server-resolved viewer and refuse other roles. |
| `src/lerni/student/web/guide.md` | The old educator instructions for the Guide tab. Not shown since step 7; removed in step 10. |
| `src/lerni/student/web/__init__.py` | Marks the screens package; says it's the only place Gradio is imported. |

**The core** (standard library only; no Gradio, no provider SDKs)

| File | What it does |
|---|---|
| `src/lerni/student/plans.py` | Learning plans: the data types (plan, activity, activity card), validation, and `PlanStore`, which saves one JSON file per plan on the home server. |
| `src/lerni/student/interests.py` | Interest maps: entries (interests and goals), links, the rules for people's edits (names, the 60-entry cap, remove for good) and for the tagger's observations, the map block for the prompt, and `MapStore` (one JSON file per student, one change at a time). |
| `src/lerni/student/tagging.py` | The tagger's instructions and schema, and `MapKeeper`: tags each exchange in the background, applies it under the map's lock unless a person changed the map or the conversation was cleared, and logs it. |
| `src/lerni/student/logs.py` | Conversation logs: each exchange and what the tagger did, one file per student per day, deleted after 7 days; the only place message text is saved. |
| `src/lerni/student/students.py` | Student accounts: usernames, kinds, scrypt password hashes, the data folder (`default_data_dir`), and `StudentStore` (one JSON file per student; archived in place, never reused). |
| `src/lerni/student/signin.py` | Signing in: checks passwords (with growing waits after wrong ones), issues a signed cookie, and re-reads the account on every request, so archive and reset sign out every device. |
| `src/lerni/student/jsonfiles.py` | Writes a JSON file atomically; shared by the plan and student stores. |
| `src/lerni/student/conversation.py` | Ask Lerni: each student's conversation in memory (last 20 turns, one reply at a time), and Claude's instructions: the starting persona for that kind of student, their map as information, then fixed safety rules; reports each finished or stopped exchange so the map can grow, never who is asking. |
| `src/lerni/student/plan_import.py` | Turns rough notes into a proposed plan: reads pasted text and uploads, defines what Claude must return (the schema and instructions), and validates Claude's answer. |
| `src/lerni/student/catalog.py` | Loads activity files and refuses anything unapproved or altered (hash checks). Lists approved activities and drafts, and loads drafts for educator-only preview. |
| `src/lerni/student/engine.py` | Runs one activity step by step: given the activity, its state, and a tap, returns the next state and what the screen may show (never the answer key). |
| `src/lerni/student/domain.py` | The shared data types for activities: steps, choices, hints, approvals, states, snapshots, and errors. |
| `src/lerni/student/canonical.py` | Turns content into exact, repeatable bytes so its hash never changes by accident. |
| `src/lerni/student/__init__.py` | Marks the student package; states the standard-library-only rule. |

**Outside services** (the only code that imports provider SDKs)

| File | What it does |
|---|---|
| `src/lerni/student/adapters/claude_code.py` | Claude through the Claude Code CLI and the logged-in account (prototype; no API key): drafts a plan from notes, streams Ask Lerni's answers, and tags each exchange for the map (a small model, JSON only). No tools (except reading an uploaded PDF), no settings, and no saved transcripts. |
| `src/lerni/student/adapters/__init__.py` | Marks the adapters package. |

**Content shipped with the app**

| File | What it does |
|---|---|
| `src/lerni/student/lessons/*.toml`, `assets/*.svg` | Activity files and their pictures. Today one draft: car acceleration. |
| `src/lerni/student/lessons/lesson_index.toml` | Generated list of activity files and their hashes. Never edit by hand. |
| `src/lerni/student/lessons/__init__.py` | Makes the lessons folder loadable as package data. |
| `src/lerni/student/personas/*.md` | Lerni's starting personas: `independent.md` and `supervised.md` (character, tone, answer length, and how to bridge toward goals; a style, never an age). Safety rules stay in `conversation.py`. |
| `src/lerni/student/personas/__init__.py` | Makes the personas folder loadable as package data. |
| `src/lerni/student/seed/*.json` | The example plans (cars, sharks) copied into an empty plan store. |
| `src/lerni/student/seed/__init__.py` | Makes the seed folder loadable as package data. |

## Admin tool: the `lerni` command

| File | What it does |
|---|---|
| `src/lerni/cli.py` | The command-line entry point: registers every `lerni` command, and keeps `study` as a deprecated alias. |
| `src/lerni/__main__.py` | Lets `python -m lerni` run the same commands. |
| `src/lerni/__init__.py` | Package version. |
| `src/lerni/commands/question.py` | Create, edit, show, and delete study questions and their explanation history. |
| `src/lerni/commands/review.py` | The daily review: explain from memory, grade yourself, schedule the next review. |
| `src/lerni/commands/organize.py` | List, search, and tag questions; manage the admin's own concept tree. |
| `src/lerni/commands/logs.py` | `lerni logs [USERNAME]`: the admin reads the last 7 days of conversations, each with what the tagger did, to check the maps. |
| `src/lerni/commands/student.py` | `lerni student add`, `reset-password`, `educator`, and `list`: the admin's way to add the first educator account and to recover; passwords at a hidden prompt. |
| `src/lerni/commands/notify.py` | macOS reminders for reviews that are due. |
| `src/lerni/commands/__init__.py` | Marks the commands package. |
| `src/lerni/db.py` | The admin tool's SQLite database in `~/.lerni/lerni.db`: tables and queries. |
| `src/lerni/models.py` | The admin tool's data types (questions, answers, concepts, reviews). |
| `src/lerni/sm2.py` | The SM-2 spaced-repetition formula that sets the next review date. |
| `src/lerni/config.py` | Reads `~/.lerni/config.toml`. |
| `src/lerni/editor.py` | Typing answers inline or in your text editor. |

## Scripts

| File | What it does |
|---|---|
| `scripts/eval_tagger.py` | Tagger evals: three real cases (an interest and a dislike, a bridge, a personal detail), run by hand with the admin's Claude account. |
| `scripts/generate_lesson_index.py` | Rebuilds `lesson_index.toml` from the real bytes after an activity or picture changes. It never approves anything. |

## Tests

Minimal on purpose: one happy path per module, plus a test for each safety guarantee. New tests come from bugs we fix (a regression test with each fix). All use fakes; none touch the network or `~/.lerni`.

| File | What it checks |
|---|---|
| `tests/student/test_engine.py` | A right answer completes; wrong answers move through the hints to the answer reveal. |
| `tests/student/test_catalog.py` | An approved file loads; content edited after approval, or approved without approvals, is refused. |
| `tests/student/test_catalog_listing.py` | Only approved, unaltered activities are listed; a draft preview is not a lesson; the car draft previews with its picture. |
| `tests/student/test_chain_1_content.py` | The car activity is refused while it's a draft. Two expected failures mark what passes once it's approved. |
| `tests/student/test_domain.py` | The snapshot type has no field for the answer key. |
| `tests/student/test_canonical.py` | The same content always gives the same bytes. |
| `tests/student/test_plans.py` | Plans save and load; examples seed once; plan ids can't escape the plans folder. |
| `tests/student/test_students.py` | An account saves and checks its password; bad, reserved, and archived usernames are refused. |
| `tests/student/test_interests.py` | People's goal edits are saved; a goal takes over an interest of the same name; a full map says so; the tagger only adds what the student said and never touches goals; the prompt block stays short. |
| `tests/student/test_tagging.py` | An exchange grows the map and is logged (a stopped one isn't tagged); a late result never undoes a person or a new conversation; logs older than 7 days are deleted. |
| `tests/student/test_mapdraw.py` | The map picture escapes names and draws at most 15 entries; the list says the same in words. |
| `tests/student/test_signin.py` | A cookie stops working after a reset; wrong passwords wait without signing anyone out. |
| `tests/student/test_conversation.py` | Answers stream in and history stays short; the map comes before the rules and never says who is asking; each exchange is reported, stopped or not; New conversation during a reply isn't undone. |
| `tests/student/test_claude_code_adapter.py` | Every Claude call (drafter, chat, tagger) runs with no tools, no settings, and no saved transcripts; the tagger has a turn for its JSON. |
| `tests/student/test_plan_import.py` | Rough notes become an unsaved plan; nothing is sent to Claude without consent. |
| `tests/student/test_web_signin.py` | Signed-out visits go to the sign-in form; a right password opens the app; Sign out ends it; a first start says how to add the first account. |
| `tests/student/test_cli_student.py` | The admin adds the first educator account from the terminal, and reads the conversation logs. |
| `tests/student/test_serve.py` | Ctrl-C stops the server within a few seconds, even with pages open. |
| `tests/student/test_web_roles.py` | Students can't manage accounts; cleared fields each get their own update; the page config carries no plans or other students' names; each role opens on a tab it can see; only independent students can ask; a map is reached only by its owner, or by an educator for a supervised student. |
| `tests/student/test_core_imports.py` | The core imports only the standard library (never Gradio or a provider SDK). |
| `tests/student/test_distribution.py` | The built package ships the activity files byte for byte (slow; needs `build`). |
| `tests/student/conftest.py` | Shared test data: a synthetic activity, and a temporary data folder for every test. |
| `tests/test_sm2.py` | Good reviews keep lengthening the interval. |
| `tests/test_cli_alias.py` | `study` still runs `lerni`, with a deprecation note. |
| `tests/test_code_manifest.py` | Every code and test file is listed in this manifest. |
| `tests/__init__.py`, `tests/student/__init__.py` | Mark the test packages. |
