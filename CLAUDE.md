# CLAUDE.md

Guidance for AI coding agents in this repository. Product context: [README](README.md).

## What's here

- `src/lerni/student/`: the student app's core: activity format, catalog, and engine. The app itself is not built.
- `src/lerni/` (the rest): the admin tool, the `lerni` command.
- `curation/`: educator authoring templates and examples. `scripts/`: the curation checker and lesson index generator.
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

1. **Vocabulary.** The people are the **student**, the **educator**, and the **admin**. Don't write child, kid, parent, adult, or supervisor. Tree terms for concepts (a concept's parent or children in the admin tool) are fine.
2. **No commit, push, branch, or pull request unless asked.**
3. **No hardcoded providers.** Model and speech services go behind a replaceable adapter; credentials only as `env:VAR` references, never literal values.
4. **Tests use fakes.** No test calls a real model, service, or network.
5. **Never fabricate approvals.** Student-facing content needs recorded human approvals tied to its exact content fingerprint. No agent writes an approval, review date, or fingerprint to make a check pass.
6. **Teaching order is not a graph edge.** Concept relationships say how ideas relate; activity order comes only from authored sequence numbers.
7. **Check the tree before saying code exists.** Many planned modules are designed only.
8. **This repo is public.** Never write real names, family details, a real student's learning plan or observations, hostnames, IP addresses, network names, or personal paths. Say "the home server" or "the student".

## Docs

[PRDs](docs/prd/) · [Roadmap](docs/roadmap.md) · [To do](docs/todo.md) · [Progress](docs/progress.md) · [Architecture](docs/ARCHITECTURE.md) · [Admin tool reference](docs/reference/admin.md) · [Curation](curation/README.md)
