# CLAUDE.md

Guidance for AI coding agents in this repository. Product context: [README](README.md).

## What's here

- `src/lerni/student/`: the student app's core: accounts, sign-in, Ask Lerni's conversation, and the interest map (`interests.py`, `tagging.py`, `logs.py`) (built; [design](plans/specs/04-interest-map.md)). The older activity path (activity format, catalog, engine, learning plans, the plan import) is off the screens and removed in step 10.
- `src/lerni/` (the rest): the admin tool, the `lerni` command.
- `src/lerni/student/web/`: the Gradio screens (`lerni serve`), One app with sign-in and tabs by role. `scripts/`: the lesson index generator (removed in step 10). The educator never uses the repo; everything for them lives in the app.
- `docs/prd/`: the source of truth for requirements, one PRD per role. `plans/`: one build plan per release ([release-1-mvp.md](plans/release-1-mvp.md) is current); `plans/later/` holds older designs for reference. A PRD wins where they disagree.

Python 3.11+, standard library first; typer and rich for the CLI; SQLite for admin data in `~/.lerni/`.

## Commands

```bash
.venv/bin/python -m pytest -q          # all tests
.venv/bin/python -m ruff check <files> # lint; src/ has known pre-existing debt
.venv/bin/python scripts/generate_lesson_index.py   # after changing a lesson file or asset
```

The commit gate (`.claude/hooks/quality-gate.sh`) lints staged Python and runs the full test suite; it skips tests when only Markdown is staged. Never commit `.claude/settings.local.json`. Cursor users run the same gate by enabling `.githooks/` once per clone: `git config core.hooksPath .githooks`.

## Rules

1. **Vocabulary.** The people are the **student**, the **educator**, and the **admin**. A student is a **supervised student** or an **independent student**, set by supervision, not age. Don't write child, kid, parent, adult, or supervisor, and don't describe a student by age: the experience is simple and engaging for people of all ages. Exceptions: tree terms for concepts (a concept's parent or children), and older text kept as history (the log in `docs/progress.md`, `plans/later/`, `plans/specs/02-lesson-core.md`, the retired CSV templates in git history).
2. **No commit, push, branch, or pull request unless asked.** Pull requests follow the running list in [docs/todo.md](docs/todo.md#upcoming-prs): one unit each, in order, each from `main`.
3. **No hardcoded providers.** Model and speech services go behind a replaceable adapter; credentials only as `env:VAR` references, never literal values.
4. **Tests use fakes, and stay minimal.** No test calls a real model, service, or network. One happy path per module plus a test for each safety guarantee; add a regression test with each bug fix, not tests up front. This holds even when a plan or skill says to write tests first. Evals too: start with 2–3 cases and add one per problem seen.
5. **Only people set goals.** Goals and their notes come only from a signed-in educator (or an independent student for their own map), set by the server from their tap (including goals Claude proposed on Upload that a person ticked). The agent and the tagger only record interests, time, and links. Feedback is summarized for the admin, never acted on. No agent, script, or automated browser adds a goal or acts on feedback.
6. **Conversation text is kept only in the 7-day logs.** On disk: accounts, interest maps, feedback, and the conversation logs on the home server, deleted after 7 days. Never message text anywhere else (other files, server output, browser storage), and never in the repo.
7. **Check the tree before saying code exists.** Many planned modules are designed only.
8. **This repo is public: never commit anything private.** That means real names or usernames, family details, a real student's interest map, feedback, or observations, hostnames, IP addresses, network names, personal paths, and any password, passcode, API key, token, or secret file (such as `secret.key`). Check every diff for them before committing; the commit check also refuses any word listed in the gitignored `.private-words` file (one per line) and any `secret.key`. Say "the home server" or "the student". Private, machine-specific details live in the gitignored `CLAUDE.local.md`; use them, but never copy them into tracked files.
9. **Keep code reviewable, and screens short.** In-app text is for one family: just enough to get going, friendly, no fine print (no disclaimers or notices in the family prototype; add them to the to-do list for before anyone else uses it). Details belong in the PRDs, not the screens. Forms clear after a successful save and keep their values after an error. Screens are phone first: before calling a screen change done, check it at phone size with the on-screen keyboard up (Safari in the iOS Simulator once Xcode is installed; until then a phone-size browser, and the admin confirms on the real device). Fields use 16px text so iPhone Safari doesn't zoom. When you add, remove, or rename a code file, update [docs/code-manifest.md](docs/code-manifest.md) (a test checks it). Comment all code concisely: short inline comments, one line at most, above a block or at the end of a line.

## Docs

[PRDs](docs/prd/) · [Roadmap](docs/roadmap.md) · [To do](docs/todo.md) · [Progress](docs/progress.md) · [Architecture](docs/ARCHITECTURE.md) · [Admin tool reference](docs/reference/admin.md)
