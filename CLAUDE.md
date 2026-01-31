# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lerni is a local-first, privacy-preserving learning system that combines the Feynman Technique (learning by teaching) with spaced repetition (SM-2 algorithm). It includes optional AI agents for coaching. The project is currently in the documentation/design phase with implementation not yet begun.

## Tech Stack

- **Language**: Python 3.11+ (uses `tomllib` from stdlib)
- **CLI**: typer
- **Database**: SQLite (stdlib `sqlite3`)
- **Notifications**: `osascript` (macOS native)
- **AI**: Anthropic Claude API or OpenAI (optional, user-provided keys)

## Build/Test Commands

Not yet configured. When implemented, expect:
- pytest for testing
- Standard Python tooling (pyproject.toml)

## Architecture

### Data Layer
- **Topic**: Main learning unit with metadata (tags, domain, difficulty, prerequisites)
- **TopicVersion**: Immutable snapshots tracking the 4-step Feynman process
  - Step 1: Raw notes (what you know)
  - Step 2: Simple explanation
  - Step 3: Identified gaps/questions
  - Step 4: Refined explanation + analogies
- **Review**: Tracks review sessions with SM-2 state and self-grades (0-5 scale)
- **AISession**: Optional AI coaching transcripts

### User Data Location
All user data stored in `~/.lerni/`:
- `lerni.db` - SQLite database
- `config.toml` - User preferences (copied from `config.example.toml`)
- `agents/` - User customizations of agent prompts
- `transcripts/` - Saved AI session transcripts

### Core Algorithms
- **Feynman Technique**: 4-step teaching-yourself workflow
- **SM-2**: Spaced repetition with easiness factor (starts 2.5, min 1.3), quality grades 0-5

### AI Agents
Located in `agents/`:
- **beginner.md**: 3 modes (Socratic, ELI5, Analogy) - 5 turns, gap identification
- **expert.md**: 5 rigor levels (1=Gentle to 5=Harsh Critic) - 5 turns, grade recommendation

## Key Documentation

- `docs/spec.md` - Complete technical specification (data models, CLI commands, algorithms)
- `docs/mission.md` - Product vision and core beliefs
- `docs/roadmap.md` - 5-phase development roadmap (MVP → AI → Analytics → Visualization → Native apps)
- `docs/PRD.md` - Product requirements index

## Design Principles

1. **Local-First**: No cloud sync; privacy is paramount
2. **Feynman-Centric**: AI enhances but never replaces the core learning process
3. **Opt-In AI**: AI features require explicit `--ai` flag and user API keys
4. **Immutable Versions**: All topic revisions are versioned snapshots

## CLI Structure (Planned)

```bash
# Topic management
study new "Title"              # 4-step Feynman flow
study new "Title" --quick      # Quick capture (step 1 only)
study new "Title" --ai         # With beginner agent review
study edit <id>                # Minor edits
study snapshot <id>            # Create new version
study list [--domain|--tag|--due]

# Review & assessment
study today                    # Daily summary
study review [<id>] [--ai]     # Review with optional AI coaching
study coach <id> --agent <beginner|expert> [--mode|--rigor]

# Knowledge graph
study graph [<id>]
study export-graph --format json
```

## Implementation Roadmap

- **Phase 1 (MVP)**: Core system without AI - data layer, Feynman workflow, SM-2
- **Phase 2**: AI agents with transcript storage
- **Phase 3**: Analytics and export
- **Phase 4**: Visualization (Plotly, Neo4j)
- **Phase 5**: Native apps
