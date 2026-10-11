# Code manifest

What every code file does, in the order a request flows through it. When you add, remove, or rename a code file, update this list; a test fails if a file is missing here. The bigger picture is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Student app: what runs on the home server

**Starting the server**

| File | What it does |
|---|---|
| `src/lerni/commands/serve.py` | The `lerni serve` command: starts the student app, with a friendly message if Gradio isn't installed; `--cert` and `--key` serve HTTPS; `--label Development` marks a development server. |
| `src/lerni/student/web/serve.py` | Says which code is running (branch, commit, date), picks the Claude chat, tagger, and uploader if the `claude` CLI is installed, builds the app, says how to add the first educator if there's none and where the logs are, says whether voice is on (the speech tools are installed), and runs the web server (HTTPS with `--cert` and `--key`) (Ctrl-C stops it within 3 seconds). |
| `src/lerni/student/web/app.py` | Builds the server: the sign-in page, and one Gradio app at `/app/` that Gradio's `auth_dependency` re-checks on every request; wires the conversation to the map keeper (maps, tagger, logs), Upload to the uploader, and Feedback to `feedback.jsonl` and purges old logs at startup. Turns off Gradio's analytics, run history, API pages, and other extras, and sets the look (system fonts, 16px fields). With speech on, inlines `talk.js` and gives the held talk button its look. |
| `src/lerni/student/web/signin_page.py` | The sign-in page: a plain HTML form Safari can save, the signed cookie (`Secure` over HTTPS), Sign out (this device only), and sending signed-out visits to it; shows the running version small at the bottom. |
| `src/lerni/student/web/main.py` | The one app's page: "Signed in as" with Sign out, then tabs by role on load: a supervised student's conversation, full screen; Ask, My map, and My account; Maps and Students for educators. Nothing per-user or from the data is built into the layout. |

**The screens** (the only code that imports Gradio)

| File | What it does |
|---|---|
| `src/lerni/student/web/talk.js` | The browser side of Hold to talk: the button turns red while held, records a 16 kHz WAV (half a second to 30 seconds), sends the clip so far every 1.5 s for the preview, sends the whole clip on release, and plays each spoken sentence in order (Stop clears them). |
| `src/lerni/student/web/ask.py` | The conversation: an independent student's Ask tab (chat, one-line question box, Send that becomes Stop, New conversation; educators can try the supervised-student voice) and a supervised student's whole screen (chat, box, Send/Stop). One ongoing conversation per student; phone first. A supervised student always gets the supervised voice; the role is checked on the server. With speech on, a Hold to talk button: a live preview while it's held, what was heard becomes the student's message, and the answer is spoken a sentence at a time (Stop silences it). |
| `src/lerni/student/web/maps.py` | My map and Maps: the picture, the list, Add goal, Rename, Remove, Upload notes (Claude proposes, the person ticks; the file is deleted at once), and, on Maps, Feedback for the admin; the username a page asks for is checked against the viewer (Maps shows only supervised students); Maps redraws every 30 seconds. |
| `src/lerni/student/web/mapdraw.py` | Draws a map as inline SVG (at most 15 entries in a stable ring, three sizes, color-blind-safe green and coral, dashed bridges, every name escaped) and says the same in words. |
| `src/lerni/student/web/accounts.py` | The Students tab (add, reset password, archive) and an independent student's My account (name, and password with the current one); handlers take the server-resolved viewer and refuse other roles. |
| `src/lerni/student/web/__init__.py` | Marks the screens package; says it's the only place Gradio is imported. |

**The core** (standard library only; no Gradio, no provider SDKs)

| File | What it does |
|---|---|
| `src/lerni/student/interests.py` | Interest maps: entries (interests and goals), links, the rules for people's edits (add a goal or an interest, names, the 60-entry cap, remove for good) and for the tagger's observations, the map block for the prompt, and `MapStore` (one JSON file per student, one change at a time). |
| `src/lerni/student/tagging.py` | The tagger's instructions and schema, and `MapKeeper`: tags each exchange in the background, applies it under the map's lock unless a person changed the map or the conversation was cleared, and logs it. |
| `src/lerni/student/logs.py` | Conversation logs: each exchange and what the tagger did, one file per student per day, deleted after 7 days; the only place message text is saved. |
| `src/lerni/student/voice.py` | Voice: checks a spoken clip (a WAV of at most 30 seconds) and gets what was said; cuts Lerni's answer into clean sentences to speak (no markdown, emoji, or web addresses); a failed voice leaves the text. Keeps no audio. |
| `src/lerni/student/upload.py` | Upload: reads pasted notes and .txt/.md/.docx/.pdf files, the instructions and schema for Claude's proposals, and checks and adds the ticked interests and goals. |
| `src/lerni/student/feedback.py` | Educator feedback: saved one line per entry in `feedback.jsonl`, summarized by Claude with instructions never to carry it out, listed and closed only by `lerni feedback`. |
| `src/lerni/student/students.py` | Student accounts: usernames, kinds, scrypt password hashes, the data folder (`default_data_dir`), and `StudentStore` (one JSON file per student; archived in place, never reused). |
| `src/lerni/student/signin.py` | Signing in: checks passwords (with growing waits after wrong ones), issues a signed cookie, and re-reads the account on every request, so archive and reset sign out every device. |
| `src/lerni/student/jsonfiles.py` | Writes a JSON file atomically; shared by the plan and student stores. |
| `src/lerni/student/conversation.py` | Ask Lerni: each student's conversation in memory (last 20 turns, one reply at a time), and Claude's instructions: the starting persona for that kind of student, their map as information, then fixed safety rules; reports each finished or stopped exchange so the map can grow, never who is asking. |
| `src/lerni/student/__init__.py` | Marks the student package; states the standard-library-only rule. |

**Outside services** (the only code that imports provider SDKs)

| File | What it does |
|---|---|
| `src/lerni/student/adapters/claude_code.py` | Claude through the Claude Code CLI and the logged-in account (prototype; no API key): streams Ask Lerni's answers, tags each exchange for the map (a small model, JSON only), and proposes map entries from uploaded notes. Earlier turns go as JSON data, so a student can't fake one, and Stop cancels the call. No tools (except reading an uploaded PDF), no settings, and no saved transcripts. |
| `src/lerni/student/adapters/mac_speech.py` | Speech on the home server (a Mac): whisper.cpp's `whisper-cli` turns a clip into text and `say` speaks a sentence (AAC), both as commands, so nothing else needs to keep running. On only when both commands and the Whisper model are there; the clip's temp file is deleted at once. |
| `src/lerni/student/adapters/__init__.py` | Marks the adapters package. |

**Content shipped with the app**

| File | What it does |
|---|---|
| `src/lerni/student/personas/*.md` | Lerni's starting personas: `independent.md` and `supervised.md` (character, tone, answer length, and how to bridge toward goals; a style, never an age). Safety rules stay in `conversation.py`. |
| `src/lerni/student/personas/__init__.py` | Makes the personas folder loadable as package data. |

## Admin tool: the `lerni` command

| File | What it does |
|---|---|
| `src/lerni/cli.py` | The command-line entry point: registers every `lerni` command, and keeps `study` as a deprecated alias. |
| `src/lerni/__main__.py` | Lets `python -m lerni` run the same commands. |
| `src/lerni/__init__.py` | Package version. |
| `src/lerni/commands/question.py` | Create, edit, show, and delete study questions and their explanation history. |
| `src/lerni/commands/review.py` | The daily review: explain from memory, grade yourself, schedule the next review. |
| `src/lerni/commands/organize.py` | List, search, and tag questions; manage the admin's own concept tree. |
| `src/lerni/commands/feedback.py` | `lerni feedback` (open entries; `--summary` groups them with Claude) and `lerni feedback done N`; nothing here changes the app. |
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
| `scripts/eval_voice.py` | Voice evals: two real cases (a spoken sentence comes back word for word; a spoken question gets a short supervised answer), run by hand. |
| `scripts/eval_upload.py` | Upload evals: two real cases (an educator's notes with a made-up name, a person's own notes), run by hand. |
| `scripts/eval_supervised.py` | Supervised voice evals: three real cases (short and simple, a scary question, an excluded subject), run by hand. |

## Tests

Minimal on purpose: one happy path per module, plus a test for each safety guarantee. New tests come from bugs we fix (a regression test with each fix). All use fakes; none touch the network or `~/.lerni`.

| File | What it checks |
|---|---|
| `tests/student/test_students.py` | An account saves and checks its password; bad, reserved, and archived usernames are refused; an account saved before step 10 still loads. |
| `tests/student/test_interests.py` | People's goal edits are saved; a goal takes over an interest of the same name; a full map says so; the tagger only adds what the student said and never touches goals; the prompt block stays short. |
| `tests/student/test_tagging.py` | An exchange grows the map and is logged (a stopped one isn't tagged); a late result never undoes a person or a new conversation; logs older than 7 days are deleted. |
| `tests/student/test_mapdraw.py` | The map picture escapes names and draws at most 15 entries; the list says the same in words. |
| `tests/student/test_voice.py` | Answers are spoken a clean sentence at a time; bad clips are refused before transcribing; a failed voice keeps the text. |
| `tests/student/test_mac_speech.py` | The speech adapter runs whisper-cli and say, and leaves no clip behind. |
| `tests/student/test_upload.py` | Proposals are checked and only ticked ones are added (a clash is skipped and named); uploads are read or refused politely. |
| `tests/student/test_feedback.py` | Feedback is summarized, saved (with or without a summary), and closed, and never touches a map. |
| `tests/student/test_signin.py` | A cookie stops working after a reset; wrong passwords wait without signing anyone out. |
| `tests/student/test_conversation.py` | Answers stream in and history stays short; the map comes before the rules and never says who is asking; each exchange is reported, stopped or not; New conversation during a reply isn't undone. |
| `tests/student/test_claude_code_adapter.py` | Every Claude call (chat, tagger, uploader) runs with no tools, no settings, and no saved transcripts; the tagger and uploader have a turn for their JSON; a student can't forge an earlier turn; Stop cancels the call. |
| `tests/student/test_web_signin.py` | Signed-out visits go to the sign-in form; a right password opens the app; Sign out ends it; a first start says how to add the first account; the cookie is `Secure` only over HTTPS; a development server shows its label and production doesn't; the sign-in page says which version is running. |
| `tests/student/test_cli_student.py` | The admin adds the first educator account from the terminal, reads the conversation logs, and lists and closes feedback. |
| `tests/student/test_serve.py` | Ctrl-C stops the server within a few seconds, even with pages open; HTTPS needs both files. |
| `tests/student/test_web_roles.py` | Students can't manage accounts; a talked question is heard (only when signed in) and answered aloud in the right voice; cleared fields each get their own update; the page config carries no plans or other students' names; each role opens on a tab it can see; a supervised student signs in to the conversation; each student asks in their own voice; a map is reached only by its owner, or by an educator for a supervised student; upload and feedback check who is asking, and an upload is deleted even when refused. |
| `tests/student/test_core_imports.py` | The core imports only the standard library (never Gradio or a provider SDK). |
| `tests/student/test_distribution.py` | Builds the wheel and sdist, installs each outside the repo, and checks the personas ship byte for byte. |
| `tests/student/conftest.py` | Gives every test its own temporary data folder. |
| `tests/test_sm2.py` | Good reviews keep lengthening the interval. |
| `tests/test_cli_alias.py` | `study` still runs `lerni`, with a deprecation note. |
| `tests/test_code_manifest.py` | Every code and test file is listed in this manifest. |
| `tests/__init__.py`, `tests/student/__init__.py` | Mark the test packages. |
