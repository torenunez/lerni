# CLAUDE.md

Guidance for AI coding agents in this repository. Product context: [README](README.md).

## What's here

- `src/lerni/student/`: the student app's core: activity format, catalog, engine, learning plans, and the Claude import. Accounts, card activities, and sessions are planned ([design](plans/specs/03-student-accounts.md)).
- `src/lerni/` (the rest): the admin tool, the `lerni` command.
- `src/lerni/student/web/`: the Gradio screens (`lerni serve`), including the educator's in-app `guide.md`. From step 5, one app with sign-in and tabs by role. `scripts/`: the lesson index generator. The educator never uses the repo; everything for them lives in the app.
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

1. **Vocabulary.** The people are the **student**, the **educator**, and the **admin**. A student is a **supervised student** or an **independent student**, set by supervision, not age. Don't write child, kid, parent, adult, or supervisor, except "often a child" or "often an adult" as an example, never a definition. Exceptions: tree terms for concepts (a concept's parent or children), and older text kept as history (the log in `docs/progress.md`, `plans/later/`, the retired CSV templates in git history).
2. **No commit, push, branch, or pull request unless asked.**
3. **No hardcoded providers.** Model and speech services go behind a replaceable adapter; credentials only as `env:VAR` references, never literal values.
4. **Tests use fakes, and stay minimal.** No test calls a real model, service, or network. One happy path per module plus a test for each safety guarantee; add a regression test with each bug fix, not tests up front.
5. **Never fabricate approvals.** Student-facing content needs a recorded human approval tied to its exact content fingerprint: the educator's four checks for a supervised student, or the independent student's own "This is ready". The one exception is an independent student's own Explore freely switch, which they turn on themselves; its content is labeled unchecked. No agent or script writes an approval, review date, fingerprint, or Explore freely setting to make a check pass.
6. **Teaching order is not a graph edge.** Concept relationships say how ideas relate; activity order comes only from the order of activities in a learning plan.
7. **Check the tree before saying code exists.** Many planned modules are designed only.
8. **This repo is public.** Never write real names, family details, a real student's learning plan or observations, hostnames, IP addresses, network names, or personal paths. Say "the home server" or "the student". Private, machine-specific details live in the gitignored `CLAUDE.local.md`; use them, but never copy them into tracked files.
9. **Keep code reviewable.** When you add, remove, or rename a code file, update [docs/code-manifest.md](docs/code-manifest.md) (a test checks it). Comment non-obvious logic with short inline comments, one line at most.

## Docs

[PRDs](docs/prd/) · [Roadmap](docs/roadmap.md) · [To do](docs/todo.md) · [Progress](docs/progress.md) · [Architecture](docs/ARCHITECTURE.md) · [Admin tool reference](docs/reference/admin.md)
