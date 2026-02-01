# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lerni is a local-first, privacy-preserving learning system combining the Feynman Technique (learning by teaching) with spaced repetition (SM-2). Currently in documentation/design phase—implementation not yet begun.

## Tech Stack

- **Python 3.11+** (uses `tomllib` from stdlib)
- **CLI**: typer
- **Database**: SQLite (stdlib `sqlite3`)
- **Notifications**: `osascript` (macOS native)
- **AI**: Anthropic Claude API or OpenAI (optional, user-provided keys)

## Build/Test Commands

Not yet configured. When implemented:
```bash
pytest                          # Run all tests
pytest tests/test_sm2.py -v     # Run single test file
pytest -k "test_name"           # Run specific test
```

## Project Structure

```
src/lerni/
├── cli.py            # CLI entry points (typer)
├── models.py         # Data models
├── db.py             # Database operations
├── sm2.py            # SM-2 algorithm
├── review.py         # Review workflow
└── agents/           # AI agent orchestration
    ├── base.py       # Base agent class
    ├── beginner.py   # Beginner agent logic
    └── expert.py     # Expert agent logic

agents/               # Default agent prompt files (markdown)
~/.lerni/             # User data (db, config, custom prompts, transcripts)
```

## Architecture

### Data Model
- **Topic**: Main learning unit with metadata (tags, domain, difficulty, prerequisites)
- **TopicVersion**: Immutable snapshots of the 4-step Feynman process
- **Review**: Tracks review sessions with SM-2 state and self-grades (0-5)
- **AISession**: Optional AI coaching transcripts

### Core Algorithms
- **Feynman Technique**: 4-step workflow (raw notes → simple explanation → gaps → refined explanation + analogies)
- **SM-2**: Easiness factor starts at 2.5 (min 1.3), grades 0-5, interval calculation per spec

### AI Agents
- **Beginner Agent** (`agents/beginner.md`): 3 modes (Socratic, ELI5, Analogy), 5-turn sessions, gap identification
- **Expert Agent** (`agents/expert.md`): 5 rigor levels (1=Gentle to 5=Harsh), grade recommendation

## Design Principles

1. **Local-First**: No cloud sync; privacy paramount
2. **Feynman-Centric**: AI enhances but never replaces core learning process
3. **Opt-In AI**: Requires explicit `--ai` flag and user API keys
4. **Immutable Versions**: All topic revisions are versioned snapshots

## CLI Commands (Planned)

```bash
study new "Title"              # 4-step Feynman flow
study new "Title" --quick      # Quick capture (step 1 only)
study new "Title" --ai         # With beginner agent review
study edit <id>                # Minor edits
study snapshot <id>            # Create new version
study list [--domain|--tag|--due]
study today                    # Daily summary
study review [<id>] [--ai]     # Review with optional AI
study coach <id> --agent <beginner|expert> [--mode|--rigor]
```

## Key Documentation

- `docs/spec.md` - Complete technical specification (data models, CLI, algorithms)
- `docs/mission.md` - Product vision and core beliefs
- `docs/roadmap.md` - 5-phase development roadmap

## Implementation Roadmap

- **Phase 1 (MVP)**: Core system without AI - data layer, Feynman workflow, SM-2
- **Phase 2**: AI agents with transcript storage
- **Phase 3**: Analytics and export
- **Phase 4**: Visualization (Plotly, Neo4j)
- **Phase 5**: Native apps
