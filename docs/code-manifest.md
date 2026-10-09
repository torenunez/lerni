# Code manifest

What every code file does, in the order a request flows through it. When you add, remove, or rename a code file, update this list; a test fails if a file is missing here. The bigger picture is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Student app: what runs on the home server

**Starting the server**

| File | What it does |
|---|---|
| `src/lerni/commands/serve.py` | The `lerni serve` command: reads its options and starts the student app, with a friendly message if Gradio isn't installed. |
| `src/lerni/student/web/serve.py` | Reads the educator passcode from its environment variable, picks the Claude drafter if the `claude` CLI is installed, builds the app, and runs the web server. |
| `src/lerni/student/web/app.py` | Builds the server: the student screen at `/` (no login) and the educator view at `/educator/` behind the passcode. Turns off Gradio's analytics, run history, API pages, and other extras, and sets the look (system fonts, the playful waiting screen). |

**The screens** (the only code that imports Gradio)

| File | What it does |
|---|---|
| `src/lerni/student/web/educator.py` | The educator view's tabs: Guide, Sessions, and Learning plans (plan table, activity-card form, and the Claude import). Its handlers are plain functions so they can be tested without a browser. |
| `src/lerni/student/web/guide.md` | The educator's instructions, shown in the Guide tab. Not code, but shipped with it. |
| `src/lerni/student/web/__init__.py` | Marks the screens package; says it's the only place Gradio is imported. |

**The core** (standard library only; no Gradio, no provider SDKs)

| File | What it does |
|---|---|
| `src/lerni/student/plans.py` | Learning plans: the data types (plan, activity, activity card), validation, and `PlanStore`, which saves one JSON file per plan on the home server. |
| `src/lerni/student/students.py` | Student accounts: usernames, kinds, scrypt password hashes, and `StudentStore` (one JSON file per student; archived in place, never reused). |
| `src/lerni/student/signin.py` | Signing in: checks passwords (with growing waits after wrong ones), issues a signed cookie, and re-reads the account on every request, so archive and reset sign out every device. |
| `src/lerni/student/jsonfiles.py` | Writes a JSON file atomically; shared by the plan and student stores. |
| `src/lerni/student/plan_import.py` | Turns rough notes into a proposed plan: reads pasted text and uploads, defines what Claude must return (the schema and instructions), and validates Claude's answer. |
| `src/lerni/student/catalog.py` | Loads activity files and refuses anything unapproved or altered (hash checks). Lists approved activities and drafts, and loads drafts for educator-only preview. |
| `src/lerni/student/engine.py` | Runs one activity step by step: given the activity, its state, and a tap, returns the next state and what the screen may show (never the answer key). |
| `src/lerni/student/domain.py` | The shared data types for activities: steps, choices, hints, approvals, states, snapshots, and errors. |
| `src/lerni/student/canonical.py` | Turns content into exact, repeatable bytes so its hash never changes by accident. |
| `src/lerni/student/__init__.py` | Marks the student package; states the standard-library-only rule. |

**Outside services** (the only code that imports provider SDKs)

| File | What it does |
|---|---|
| `src/lerni/student/adapters/claude_code.py` | Sends the educator's notes to Claude through the Claude Code CLI and the logged-in account (prototype; no API key), with no tools (except reading an uploaded PDF) and no settings, and returns the structured plan. |
| `src/lerni/student/adapters/__init__.py` | Marks the adapters package. |

**Content shipped with the app**

| File | What it does |
|---|---|
| `src/lerni/student/lessons/*.toml`, `assets/*.svg` | Activity files and their pictures. Today one draft: car acceleration. |
| `src/lerni/student/lessons/lesson_index.toml` | Generated list of activity files and their hashes. Never edit by hand. |
| `src/lerni/student/lessons/__init__.py` | Makes the lessons folder loadable as package data. |
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
| `tests/student/test_signin.py` | A cookie stops working after a reset; wrong passwords wait without signing anyone out. |
| `tests/student/test_plan_import.py` | Rough notes become an unsaved plan; nothing is sent to Claude without consent. |
| `tests/student/test_web_skeleton.py` | The student screen is open; the educator view refuses requests without the passcode and opens with it. |
| `tests/student/test_core_imports.py` | The core imports only the standard library (never Gradio or a provider SDK). |
| `tests/student/test_distribution.py` | The built package ships the activity files byte for byte (slow; needs `build`). |
| `tests/student/conftest.py` | Shared test data: a synthetic activity, and a temporary data folder for every test. |
| `tests/test_sm2.py` | Good reviews keep lengthening the interval. |
| `tests/test_cli_alias.py` | `study` still runs `lerni`, with a deprecation note. |
| `tests/test_code_manifest.py` | Every code and test file is listed in this manifest. |
| `tests/__init__.py`, `tests/student/__init__.py` | Mark the test packages. |
