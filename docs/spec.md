# Lerni — Technical Specification

> For vision and principles, see [mission.md](./mission.md)
> For roadmap and phases, see [roadmap.md](./roadmap.md)

---

# Architecture

## Directory Structure

### User Data (`~/.lerni/`)
```
~/.lerni/
├── lerni.db          # SQLite database
├── config.toml       # User preferences
├── agents/           # User-customized agent prompts (overrides defaults)
│   ├── beginner.md
│   └── expert.md
├── transcripts/      # Saved AI session transcripts
└── exports/          # Graph exports, backups
```

### Project Repository
```
lerni/
├── docs/
│   ├── mission.md        # Product vision
│   ├── roadmap.md        # Feature roadmap
│   ├── spec.md           # This file
│   └── todo.md           # Full backlog
├── src/lerni/
│   ├── __init__.py
│   ├── __main__.py       # python -m lerni entry point
│   ├── cli.py            # CLI app + command registration (typer)
│   ├── models.py         # Dataclass models
│   ├── db.py             # SQLite schema, connections, repository classes
│   ├── sm2.py            # SM-2 algorithm
│   ├── config.py         # Config loading (config.toml)
│   ├── editor.py         # External editor integration
│   └── commands/         # CLI command implementations
│       ├── question.py   # new, edit, snapshot, show, history, delete
│       ├── review.py     # review, skip, today
│       ├── organize.py   # list, search, assign, meta, concept subcommands
│       └── notify.py     # macOS notifications
├── tests/
├── pyproject.toml
└── README.md
```

---

## Data Model (v3 — concept-based knowledge graph)

### `Concept`
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `name` | string | Canonical name (unique) |
| `aliases` | JSON list | Alternative names for fuzzy matching |
| `description` | text | Optional description |
| `created_at` | datetime | |

### `ConceptEdge`
| Field | Type | Description |
|-------|------|-------------|
| `from_concept_id` | UUID | FK to source Concept |
| `to_concept_id` | UUID | FK to target Concept |
| `relationship` | enum | parent, prerequisite, related |

### `Question`
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `concept_id` | UUID | FK to Concept (nullable for inbox/uncategorized) |
| `prompt` | string | The question text shown during review |
| `current_answer_id` | UUID | FK to latest Answer |
| `next_review_at` | datetime | When next review is due |
| `schedule_state` | JSON | SM-2 state: easiness_factor, interval, repetitions |
| `difficulty` | int | 1-5 scale |
| `source_refs` | JSON list | URLs, books, citations |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### `Answer` (immutable)
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `question_id` | UUID | FK to Question |
| `raw_notes` | text | Step 1: What you know |
| `simple_explanation` | text | Step 2: Explain simply |
| `gaps_questions` | text | Step 3: Identified gaps |
| `final_explanation` | text | Step 4: Refined explanation |
| `analogies_examples` | text | Step 4: Analogies and examples |
| `created_at` | datetime | |

### `Review`
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `question_id` | UUID | FK to Question |
| `answer_id` | UUID | FK to Answer reviewed |
| `scheduled_for` | datetime | When it was due |
| `completed_at` | datetime | When completed |
| `status` | enum | pending, completed, skipped |
| `self_grade` | int | 0-5 (SM-2 scale) |
| `attempted_explanation` | text | What user wrote from scratch during review |
| `recalled_from_memory` | bool | True if user could explain without seeing answer |
| `gaps_identified` | text | Gaps found during this review |
| `notes` | text | Optional review notes |
| `ai_session_id` | UUID | FK to AISession (Phase 2, NULL for now) |

### `AISession` (Phase 2 — not yet implemented)
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `question_id` | UUID | FK to Question |
| `review_id` | UUID | FK to Review (optional) |
| `agent_type` | string | beginner, expert |
| `agent_mode` | string | socratic, eli5, analogy (for beginner) |
| `agent_config` | JSON | rigor level, custom params |
| `transcript` | JSON | Full conversation [{role, content, timestamp}] |
| `summary` | text | AI-generated session summary |
| `gaps_identified` | text | Gaps surfaced during session |
| `created_at` | datetime | |

---

## SM-2 Algorithm

### Grade Scale (0-5)
| Grade | Meaning | Effect |
|-------|---------|--------|
| 0 | Complete blackout | Reset to beginning |
| 1 | Incorrect, but recognized answer | Reset to beginning |
| 2 | Incorrect, but easy to recall | Reset to beginning |
| 3 | Correct with serious difficulty | Maintain interval |
| 4 | Correct with hesitation | Increase interval |
| 5 | Perfect response | Increase interval significantly |

### Algorithm
```
After each review:
1. Update easiness factor (EF):
   EF' = EF + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
   EF' = max(1.3, EF')  # Minimum EF is 1.3

2. Calculate next interval:
   If grade < 3: reset repetitions to 0, interval = 1 day
   Else:
     If repetitions == 0: interval = 1 day
     If repetitions == 1: interval = 6 days
     Else: interval = previous_interval * EF

3. Increment repetitions (if grade >= 3)
```

### Initial State
- `easiness_factor`: 2.5
- `interval`: 0
- `repetitions`: 0

---

# CLI Command Reference

## Question Management (Implemented)

```bash
# Create a new question (sequential Feynman flow)
study new "Question prompt"
  # Prompts for: raw_notes → simple_explanation → gaps → final_explanation → analogies

# Create question with minimal info (quick capture)
study new "Question prompt" --quick
  # Only prompts for raw_notes (Step 1)

# Edit a question (minor changes, no new version)
study edit <id>
  # Opens editor for current answer fields

# Create a new answer snapshot (meaningful revision)
study snapshot <id>
  # Creates a new immutable Answer

# View a question
study show <id>
  # Displays current answer + metadata + review history

# View answer history
study history <id>
  # Lists all answer versions with timestamps

# Delete a question
study delete <id>
```

## Organization (Implemented)

```bash
# List questions
study list
study list --concept <name>   # Filter by concept
study list --due              # Only questions due for review

# Search questions
study search <query>

# Assign question to concept
study assign <id> <concept>

# Update metadata
study meta <id> --difficulty 3 --source "https://..."
```

## Knowledge Graph (Implemented)

```bash
# Create a concept
study concept new "Concept Name"

# List all concepts
study concept list

# Show concept details
study concept show <id>

# Link concepts
study concept link <id1> <id2> --type prereq
study concept link <id1> <id2> --type related
study concept link <id1> <id2> --type parent

# Unlink concepts
study concept unlink <id1> <id2>

# Delete a concept
study concept delete <id>
```

## Review Management (Implemented)

```bash
# Show daily summary
study today
  # Lists questions due today and upcoming in next 7 days

# Start a review session
study review
  # Presents due questions one by one
  # Shows content → prompts for gaps → prompts for grade

# Review a specific question
study review <id>

# Skip a review
study skip <id>
```

## Notifications (Implemented)

```bash
# Send macOS notification with today's summary
study notify

# Setup daily notifications
study notify --setup
  # Outputs crontab entry for daily reminders
```

## AI-Assisted Review (Phase 2 — not yet implemented)

```bash
# Start AI-assisted review session
study review --ai
study review --ai --mode socratic    # Probing questions
study review --ai --mode eli5        # Roleplay confused beginner
study review --ai --mode analogy     # Push for real-world analogies
study review --ai --rigor 3          # Expert rigor level (1-5)

# Standalone agent sessions
study coach <id> --agent beginner --mode socratic
study coach <id> --agent expert --rigor 3

# View past AI sessions
study sessions <id>
study session <session_id>
```

## Analytics & Export (Phase 3 — not yet implemented)

```bash
study stats                    # Global statistics
study stats <id>               # Per-question analytics
study export --all             # Full JSON backup
study import                   # Restore from backup
study export-graph             # Knowledge graph JSON
```

---

# AI Agents

## Overview

AI agents are **opt-in** and activated via the `--ai` flag. They enhance the Feynman workflow by:
1. **Challenging** your explanations (Beginner Agent)
2. **Grading** your understanding (Expert Agent)

## Agent Activation

```bash
# Global disable (in config.toml)
[ai]
enabled = false  # Disables all AI features

# Per-command activation
study review --ai              # Enable AI for this session
study review                   # No AI, pure self-assessment
```

## Beginner Agent

**Purpose**: Challenge you to explain simply and clearly

**Modes**:
| Mode | Behavior |
|------|----------|
| `socratic` | Asks probing "why" and "how" questions |
| `eli5` | Roleplays as confused beginner, asks for simpler explanations |
| `analogy` | Pushes for real-world analogies and concrete examples |

**Session Flow** (3-5 turns default):
1. Agent reads your simple_explanation
2. Agent asks clarifying questions based on mode
3. You respond with improved explanations
4. Agent identifies remaining unclear areas
5. Session ends with summary of gaps surfaced

## Expert Agent

**Purpose**: Grade your understanding and identify gaps

**Rigor Levels**:
| Level | Persona |
|-------|---------|
| 1 | Gentle coach - encouraging, frames gaps as "areas to explore" |
| 2 | Supportive mentor - balanced feedback |
| 3 | Fair evaluator - direct but constructive (default) |
| 4 | Rigorous reviewer - points out all inaccuracies |
| 5 | Harsh critic - assumes expert audience, no hand-holding |

**Session Flow**:
1. Agent reviews your final_explanation and analogies
2. Agent asks you to explain specific concepts
3. Agent grades responses (suggests SM-2 grade)
4. Agent provides detailed feedback on gaps
5. Session ends with recommended grade and gap summary

## Agent Configuration

### Prompt Files

Agents are defined in markdown prompt files:
- Default: `<repo>/agents/beginner.md`, `<repo>/agents/expert.md`
- User override: `~/.lerni/agents/beginner.md`

### Prompt File Format

```markdown
# Agent: Beginner (Socratic Mode)

## System Prompt
You are a curious student trying to learn {topic_title}. Your goal is to...

## Variables
- {topic_title}: The topic being studied
- {simple_explanation}: User's simple explanation
- {gaps_questions}: Previously identified gaps

## Behavior
- Ask 1-2 probing questions per turn
- Focus on "why" and "how" questions
- ...
```

### Config Options (`config.toml`)

```toml
[ai]
enabled = true
default_mode = "socratic"
default_rigor = 3
max_turns = 5
save_transcripts = true

[ai.api]
# User provides their own API key
provider = "anthropic"  # or "openai"
model = "claude-sonnet-4-20250514"
```

---

# Tech Stack

## MVP
- **Language**: Python 3.11+
- **Database**: SQLite with `sqlite3` stdlib
- **CLI Framework**: `typer`
- **Notifications**: `osascript` (macOS native)
- **Config**: `tomllib` (Python 3.11+)

## AI Agents
- **LLM**: Anthropic Claude API (user provides key)
- **Fallback**: OpenAI API support
- **Prompt Management**: Markdown files with variable substitution

## Future
- **Graph DB**: Neo4j with `neo4j` driver
- **Visualization**: Plotly
- **Desktop App**: Tauri or Swift

---

# Open Questions

1. **Turn Limit**: Should 3-5 turns be configurable per-session or global only?
2. **Transcript Format**: JSON array vs markdown for readability?
3. **Grade Suggestion**: Should expert agent suggest SM-2 grade, or just provide qualitative feedback?
4. **Offline Agents**: Explore local LLM support (ollama) for fully offline AI?
