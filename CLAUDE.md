# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lerni is a local-first, privacy-preserving learning system. **One repository, two modes:**

- **Study** — adult Feynman + SM-2 spaced-repetition CLI. **Phase 1 feature-complete; maintenance-only.** Fixes and hardening, no new features.
- **Explore** — child interest-to-fundamentals experience, parent-supervised, localhost only. **Active development.** The lesson core exists (PR-02: domain, canonical encoder, catalog, engine, packaged draft content). Everything else — runtime boundary, safety, tutor, telemetry, UI, audio — is still only the design in `plans/` and the contracts in `docs/spec.md`. No lesson has been human-reviewed, so nothing is child-visible.

Feature-complete is not hardened. Study has SM-2 test coverage; the database layer and CLI are untested, and `src/` carries ruff debt. See `docs/todo.md`.

## Tech Stack

- **Python 3.11+** (uses `tomllib`, `enum.StrEnum` from stdlib)
- **CLI**: typer + rich
- **Database**: SQLite (stdlib `sqlite3`)
- **Notifications**: `osascript` (macOS native)
- **Explore UI** (planned): Gradio, as an optional extra — never a core dependency
- **Runtime capabilities** (planned): no required model, provider, or SDK

## Build/Test Commands

```bash
pytest                          # Run all tests
pytest tests/test_sm2.py -v     # Run single test file
pytest -k "test_name"           # Run specific test
ruff check src/                 # Lint (known pre-existing debt)
mypy src/                       # Type check
```

Use ordinary Python tooling. Prefer `python -m <tool>` from the project
virtualenv so behavior does not depend on what happens to be on `PATH`.

## Project Structure

This is the **actual** tree. Do not assume modules exist because a document
mentions them.

```
src/lerni/            # Study — implemented
├── __init__.py
├── __main__.py       # python -m lerni entry point
├── cli.py            # CLI app + command registration (typer)
├── models.py         # Concept, ConceptEdge, Question, Answer, Review
├── db.py             # SQLite schema, connections, repository classes
├── sm2.py            # SM-2 spaced repetition algorithm
├── config.py         # Config loading (config.toml), get_lerni_dir()
├── editor.py         # External editor integration
└── commands/
    ├── question.py   # new, edit, snapshot, show, history, delete
    ├── review.py     # review, skip, today
    ├── organize.py   # list, search, assign, meta, concept subcommands
    └── notify.py     # macOS notifications

src/lerni/explore/    # Explore — lesson core implemented (PR-02)
├── __init__.py
├── domain.py         # Immutable lesson, source, fact, step, check, review types
├── canonical.py      # Strict canonical-JSON encoder for payload identity
├── catalog.py        # importlib.resources loading, schema/hash verification, child filtering
├── engine.py         # Deterministic intro/teach/check/hint/complete transitions
└── lessons/          # Packaged content: lesson_index.toml, chain_1_acceleration.toml, assets/

agents/               # Study Phase-2 prompt drafts (beginner.md, expert.md) — parked, unused
tests/                # Pytest suite — test_sm2.py, test_curation_templates.py, tests/explore/ (6 modules)
scripts/              # generate_lesson_index.py; validate_curation_templates.py (offline drafting checker)
curation/             # Educator authoring — start at curation/README.md
├── schemas/          # educator-paths-v1.json column inventory
├── templates/        # educator-paths-v1/ (current); v1/ (legacy partial delivery draft)
└── examples/         # educator-paths-v1-draft/ (six draft paths); chain-1-v1-draft/ (legacy)
docs/                 # Mission, PRD, spec, roadmap, todo, progress
plans/                # Explore implementation bundle
├── cursor_master_plan.plan.md   # sequence, dependencies, gates, PR index
├── human-track.md    # what educators/parents must do; plain language, dev section at end
├── prs/              # execution units, in order
├── specs/            # normative technical contracts
└── runbooks/         # procedures a human performs (setup, source review, priming)
~/.lerni/             # Study user data (db, config)
.claude/              # Claude Code configuration (primary agent tooling)
├── settings.json     # Hook registrations (tracked)
├── settings.local.json  # Machine-specific permissions (gitignored)
└── hooks/            # quality-gate.sh, auto-format.sh, pre-commit-quality.sh, study-summary.sh
.cursor/rules/        # Thin Cursor rules — defer here, not duplicate standing rules
.githooks/            # Optional git pre-commit hook (enable per clone; see Agent Tooling)
```

**Remaining `src/lerni/explore/` modules are planned, not written.** Per `plans/`:
`contracts.py`,
`runtime_config.py`, `capability_runner.py`, `capability_supervisor.py`,
`capability_worker.py`, `readiness.py`, `policy.py`, `sanitization.py`,
`grounding.py`, `tutor_service.py`, `plugin_loader.py`, `qualification.py`,
`telemetry_store.py`, `data_lifecycle.py`, `export.py`, `bootstrap.py`,
`presenter.py`, `visuals.py`, `ui.py`, `launch.py`.

### `.claude/` hooks

- `quality-gate.sh` — shared commit gate: lints **staged** Python files with
  ruff and runs the **full** pytest suite. Lint is staged-only because `src/`
  carries pre-existing violations; tests are full-suite because regressions are not
  local to a diff. Tools resolve from `.venv/bin` first, then `PATH`. Missing
  ruff (when Python is staged) or missing pytest **fails closed**; tool stdout/
  stderr is shown, not swallowed.
- `pre-commit-quality.sh` (PreToolUse/Bash) — calls the shared gate before any
  `git commit` and denies the commit on failure. Missing `jq` also denies.
- `auto-format.sh` (PostToolUse/Edit|Write) — formats after edits (venv-aware).
- `study-summary.sh` (SessionStart) — prints due-review summary (needs `sqlite3`).

`settings.json` is tracked and portable. `settings.local.json` is machine-specific
and gitignored — never commit it.

## Agent Tooling

**Primary: Claude Code (~90%).** Hooks in `.claude/` handle session context,
auto-format, and commit gates. This file is the single source of truth for both
agents.

**Secondary: Cursor (~10%).** `.cursor/rules/lerni.mdc` is a thin pointer here —
do not duplicate standing rules in Cursor. Use Plan mode with
`plans/cursor_master_plan.plan.md` for Explore sequencing; use native Cursor
agents sparingly for review or isolated tasks.

**Active Explore work:** milestones M1–M6 in [`docs/roadmap.md`](docs/roadmap.md)
own the order; `plans/prs/` are work packages beneath them (plan PR-02 ≠ GitHub
PR #2). M1 (educator authoring + doc adoption) is on
`explore/curation-templates` (GitHub PR #2, unmerged). Next developer unit: M3, the authored local app
slice — start by reconciling the PR-03/PR-06/PR-08 specs for that reduced slice
(see the master plan's 2026-09-25 revision). The Chain-1 lesson is still draft
with zero attestations.

**Shared commit gate for Cursor commits:** run `.claude/hooks/quality-gate.sh`
before committing, or enable the git hook once per clone:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .claude/hooks/quality-gate.sh
```

### Machine-local setup (not tracked in git)

Several paths this tooling touches live **outside the repository** or are
**gitignored**. Reviewers and new clones should expect to configure these locally;
they are intentionally not part of the commit.

| Location | Purpose | How it is set |
|---|---|---|
| `.git/config` | Activates `.githooks/pre-commit` | `git config core.hooksPath .githooks` (once per clone) |
| `.claude/settings.local.json` | Claude Code tool permissions | Created by Claude Code on your machine; gitignored |
| `~/.lerni/` | Study database and `config.toml` | Created by `study` CLI usage; never committed |
| `.venv/` | Project virtualenv (`ruff`, `pytest`) | `python -m venv .venv && pip install -e .[dev]`; gitignored |
| `jq` (PATH) | Parses Claude Code PreToolUse JSON | Install via Homebrew/apt; commit hook denies if missing |
| `sqlite3` (PATH) | Used by `study-summary.sh` | Usually system-provided on macOS |
| Cursor user settings | Global IDE rules, models, API keys | Cursor app settings; not in this repo |

Tracked in git: `.claude/settings.json` (hook registrations), `.claude/hooks/*`,
`.githooks/pre-commit`, and `.cursor/rules/lerni.mdc`. Everything else in the
table is operator-scoped.

## Architecture

### Study data model (v3 schema)
- **Concept**: knowledge graph node (name, aliases, description). Forms a DAG with typed edges.
- **ConceptEdge**: typed relationship between concepts (parent, prerequisite, related)
- **Question**: study card attached to a concept. Carries SM-2 schedule state.
- **Answer**: immutable Feynman snapshot (raw_notes, simple_explanation, gaps_questions, final_explanation, analogies_examples)
- **Review**: review session record with self-grade (0–5), gaps, notes

### Core algorithms
- **Feynman Technique**: 4-step workflow (raw notes → simple explanation → gaps → refined explanation + analogies)
- **SM-2**: easiness factor starts at 2.5 (min 1.3), grades 0–5, interval calculation per spec

### Explore (planned)
Reviewed lesson content in packaged TOML; a deterministic intro/teach/check/hint/
complete state machine owned by the application; capabilities loaded
out-of-process behind typed protocols; deterministic local input/output policy and
grounding; a separate local SQLite telemetry store with parent export, retention,
and deletion. See `docs/spec.md` and `plans/`.

## Standing Rules

These apply to any work in this repository.

1. **Runtime adapters are selected by qualification, never hardcoded.** Do not add
   a provider SDK, model ID, endpoint, or account identifier to core code. Text
   generation, speech-to-text, and harm gates are replaceable capabilities chosen
   by an operator-owned runtime profile. Credentials appear only as `env:VAR`
   references — never literal values in TOML, source, tests, logs, or telemetry.

2. **Tests use deterministic fakes. No live model, service, or network call.** A
   test that requires a credential or reaches a provider is not an acceptable test.

3. **Child-facing content requires human approval.** Lesson text, facts, and visual
   assets must carry recorded review attestations tied to an exact content hash
   before a child can see them. Never fabricate an attestation, a review date, or a
   hash to make a check pass.

4. **Lesson order is separate from `ConceptEdge`.** A graph edge states a domain
   relationship between concepts. A lesson step states what to teach next. These
   are different things — conflating them corrupts both. Lesson sequence comes from
   authored step indices only.

5. **No commit unless explicitly requested.** Do not commit, push, create a branch,
   or open a pull request on the user's behalf without being asked directly.

6. **Do not overstate safety.** Never write "child-safe", "COPPA compliant",
   "anonymous", "PII-free", or "forensic deletion". Explore's controls are
   prototype guardrails plus a supervising parent.

7. **Do not claim code exists until it does.** Explore's lesson core is built; the
   remaining modules listed under Project Structure are designed only. Check the
   tree before describing a module as existing.

## Design Principles

1. **Local-First**: no cloud sync; privacy paramount
2. **Feynman-Centric**: AI enhances but never replaces the core learning process
3. **Opt-In AI**: requires explicit configuration and operator-supplied credentials
4. **Immutable Versions**: answers and lesson content are versioned snapshots
5. **Application owns progression**: reviewed content and deterministic logic decide what happens next — not a model

## Study CLI Reference (Implemented)

```bash
# Question workflow
study new "Title"              # 4-step Feynman flow
study new "Title" --quick      # Quick capture (step 1 only)
study edit <id>                # Minor edits
study snapshot <id>            # Create new answer version
study show <id>                # View question details
study history <id>             # View answer versions
study delete <id>              # Delete question

# Review
study review [<id>]            # Review session
study skip <id>                # Skip and reschedule
study today                    # Daily summary

# Organization
study list [--concept|--due]   # List questions
study search <query>           # Full-text search
study assign <id> <concept>    # Assign question to concept
study meta <id>                # Update metadata

# Knowledge graph
study concept new "Name"       # Create concept
study concept list             # List concepts
study concept show <id>        # Show concept details
study concept link <a> <b>     # Link concepts
study concept unlink <a> <b>   # Unlink concepts
study concept delete <id>      # Delete concept

# Notifications
study notify                   # macOS notification
study notify --setup           # Cron setup instructions
```

## Parked: Study Phase-2 AI Agents and Skills

Designed, not implemented, and not scheduled while Explore is active. Retained as
a design record in `docs/spec.md` and `docs/todo.md`.

- **Beginner Agent** (`agents/beginner.md`): 3 modes (Socratic, ELI5, Analogy), 5-turn sessions, gap identification
- **Expert Agent** (`agents/expert.md`): 5 rigor levels (1=Gentle to 5=Harsh), grade recommendation
- **AI Skill Modules**: Feynman Coach, Spaced Repetition Analyzer, Knowledge Graph Builder, Study Session Generator

This design is separate from the Explore tutor capability. Do not treat them as
the same runtime.

## Key Documentation

- `docs/mission.md` — vision, two modes, core beliefs
- `docs/PRD.md` — product requirements and safety boundaries
- `docs/spec.md` — technical specification and Explore contracts
- `docs/roadmap.md` — Study Track and Explore Track
- `docs/todo.md` — active Explore backlog, parked Study work
- `docs/progress.md` — dated implementation log
- `plans/` — Explore implementation bundle
- `curation/` — educator path authoring (`educator-paths-v1`); spec in `plans/specs/08c-educator-path-authoring.md`
