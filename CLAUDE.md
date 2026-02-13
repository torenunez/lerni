# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lerni is a local-first, privacy-preserving learning system combining the Feynman Technique (learning by teaching) with spaced repetition (SM-2). Phase 1 MVP is complete — core data layer, Feynman workflow, SM-2 scheduling, concept graph, and CLI are implemented.

## Tech Stack

- **Python 3.11+** (uses `tomllib` from stdlib)
- **CLI**: typer + rich
- **Database**: SQLite (stdlib `sqlite3`)
- **Notifications**: `osascript` (macOS native)
- **AI**: Anthropic Claude API or OpenAI (optional, user-provided keys) — planned for Phase 2

## Build/Test Commands

```bash
pytest                          # Run all tests
pytest tests/test_sm2.py -v     # Run single test file
pytest -k "test_name"           # Run specific test
```

## Project Structure

```
src/lerni/
├── __init__.py
├── __main__.py       # python -m lerni entry point
├── cli.py            # CLI app + command registration (typer)
├── models.py         # Data models (Concept, ConceptEdge, Question, Answer, Review)
├── db.py             # SQLite schema, connection handling, repository classes
├── sm2.py            # SM-2 spaced repetition algorithm
├── config.py         # Config loading (config.toml), get_lerni_dir()
├── editor.py         # External editor integration
└── commands/         # CLI command implementations
    ├── question.py   # new, edit, snapshot, show, history, delete
    ├── review.py     # review, skip, today
    ├── organize.py   # list, search, assign, meta, concept subcommands
    └── notify.py     # macOS notifications

tests/                # Pytest test suite
docs/                 # Specifications and roadmap
~/.lerni/             # User data (db, config)
```

## Architecture

### Data Model (v3 schema)
- **Concept**: Knowledge graph node (name, aliases, description). Forms a DAG with typed edges.
- **ConceptEdge**: Typed relationship between concepts (parent, prerequisite, related)
- **Question**: Study card attached to a concept. Carries SM-2 schedule state.
- **Answer**: Immutable Feynman snapshot (raw_notes, simple_explanation, gaps_questions, final_explanation, analogies_examples)
- **Review**: Review session record with self-grade (0-5), gaps, notes

### Core Algorithms
- **Feynman Technique**: 4-step workflow (raw notes -> simple explanation -> gaps -> refined explanation + analogies)
- **SM-2**: Easiness factor starts at 2.5 (min 1.3), grades 0-5, interval calculation per spec

### AI Agents (Phase 2 — not yet implemented)
- **Beginner Agent** (`agents/beginner.md`): 3 modes (Socratic, ELI5, Analogy), 5-turn sessions, gap identification
- **Expert Agent** (`agents/expert.md`): 5 rigor levels (1=Gentle to 5=Harsh), grade recommendation

## Design Principles

1. **Local-First**: No cloud sync; privacy paramount
2. **Feynman-Centric**: AI enhances but never replaces core learning process
3. **Opt-In AI**: Requires explicit `--ai` flag and user API keys
4. **Immutable Versions**: All answers are versioned snapshots

## CLI Commands (Implemented)

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

## Key Documentation

- `docs/spec.md` - Technical specification (data models, CLI, algorithms)
- `docs/mission.md` - Product vision and core beliefs
- `docs/roadmap.md` - 5-phase development roadmap
- `docs/todo.md` - Full backlog with known issues

## Implementation Roadmap

- **Phase 1 (MVP)**: Core system without AI - data layer, Feynman workflow, SM-2 — **complete**
- **Phase 2**: AI agents with transcript storage
- **Phase 3**: Analytics and export
- **Phase 4**: Visualization (Plotly, Neo4j)
- **Phase 5**: Native apps
