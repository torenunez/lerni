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
├── .lerni/               # Project outputs (gitignored)
│   └── tmp/
├── docs/
│   ├── PRD.md            # Product requirements index
│   ├── mission.md        # Product vision
│   ├── roadmap.md        # Feature roadmap
│   ├── spec.md           # This file
│   └── specs/            # Feature specifications
│       └── {timestamp}-{feature}/
├── src/lerni/
│   ├── __init__.py
│   ├── cli.py            # CLI entry points
│   ├── models.py         # SQLAlchemy/dataclass models
│   ├── db.py             # Database operations
│   ├── sm2.py            # SM-2 algorithm
│   ├── review.py         # Review workflow
│   └── agents/           # AI agent orchestration
│       ├── __init__.py
│       ├── base.py       # Base agent class
│       ├── beginner.py   # Beginner agent logic
│       └── expert.py     # Expert agent logic
├── agents/               # Default agent prompt files
│   ├── beginner.md
│   └── expert.md
├── tests/
├── pyproject.toml
└── README.md
```

---

## Data Model

### `Topic`
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `title` | string | Topic name |
| `metadata` | JSON | Tags, domain, difficulty, prerequisites, related_topics, source_refs |
| `current_version_id` | UUID | FK to latest TopicVersion |
| `next_review_at` | datetime | When next review is due |
| `schedule_state` | JSON | SM-2 state: easiness_factor, interval, repetitions |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### `TopicVersion` (immutable)
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `topic_id` | UUID | FK to Topic |
| `raw_notes` | text | Step 1: What you know |
| `simple_explanation` | text | Step 2: Explain simply |
| `gaps_questions` | text | Step 3: Identified gaps |
| `final_explanation` | text | Step 4: Refined explanation |
| `analogies_examples` | text | Step 4: Analogies and examples |
| `metadata_snapshot` | JSON | Copy of metadata at version time |
| `created_at` | datetime | |

### `Review`
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `topic_id` | UUID | FK to Topic |
| `version_id` | UUID | FK to TopicVersion reviewed |
| `scheduled_for` | datetime | When it was due |
| `completed_at` | datetime | When completed |
| `status` | enum | pending, completed, skipped |
| `self_grade` | int | 0-5 (SM-2 scale) |
| `gaps_identified` | text | Gaps found during this review |
| `notes` | text | Optional review notes |
| `ai_session_id` | UUID | FK to AISession (if AI-assisted) |

### `AISession`
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `topic_id` | UUID | FK to Topic |
| `review_id` | UUID | FK to Review (optional) |
| `agent_type` | string | beginner, expert |
| `agent_mode` | string | socratic, eli5, analogy (for beginner) |
| `agent_config` | JSON | rigor level, custom params |
| `transcript` | JSON | Full conversation [{role, content, timestamp}] |
| `summary` | text | AI-generated session summary |
| `gaps_identified` | text | Gaps surfaced during session |
| `created_at` | datetime | |

### Metadata Fields
| Field | Type | Description |
|-------|------|-------------|
| `tags` | list[string] | Categorization tags |
| `domain` | string | Knowledge domain (e.g., "math", "programming") |
| `difficulty` | int | 1-5 scale |
| `prerequisites` | list[UUID] | Topic IDs that should be learned first |
| `related_topics` | list[UUID] | Connected topic IDs |
| `source_refs` | list[string] | Links or citations |

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

## Topic Management

```bash
# Create a new topic (sequential Feynman flow)
study new "Topic Title"
  # Prompts for: raw_notes → simple_explanation → gaps → final_explanation → analogies
  # Use --step <1-4> to start at a specific step

# Create topic with AI assistance
study new "Topic Title" --ai
  # After manual entry, beginner agent challenges your explanation

# Create topic with minimal info (quick capture)
study new "Topic Title" --quick
  # Only prompts for raw_notes (Step 1)

# Edit a topic (minor changes, no new version)
study edit <id>
  # Opens editor for current version fields

# Create a new version snapshot (meaningful revision)
study snapshot <id>
  # Creates a new immutable TopicVersion

# View a topic
study show <id>
  # Displays current version + metadata + review history

# View version history
study history <id>
  # Lists all versions with timestamps

# List all topics
study list
study list --domain <domain>
study list --tag <tag>
study list --due          # Only topics due for review

# Search topics
study search <query>

# Delete a topic
study delete <id>
```

## Review Management

```bash
# Show daily summary
study today
  # Lists topics due today and upcoming in next 7 days

# Start a review session (no AI)
study review
  # Presents due topics one by one
  # Shows content → prompts for gaps → prompts for grade

# Start AI-assisted review session
study review --ai
  # Uses beginner agent to challenge you, then expert to grade

# Review with specific agent mode
study review --ai --mode socratic    # Probing questions
study review --ai --mode eli5        # Roleplay confused beginner
study review --ai --mode analogy     # Push for real-world analogies

# Set expert rigor level (1=gentle, 5=harsh critic)
study review --ai --rigor 3

# Review a specific topic
study review <id>
study review <id> --ai --mode eli5 --rigor 4

# Skip a review
study skip <id>
```

## AI Agent Sessions (Standalone)

```bash
# Start a standalone session with beginner agent
study coach <id> --agent beginner --mode socratic
study coach <id> --agent beginner --mode eli5
study coach <id> --agent beginner --mode analogy

# Start a standalone session with expert agent
study coach <id> --agent expert --rigor 3

# View past AI sessions for a topic
study sessions <id>
  # Lists all AI sessions with timestamps and summaries

# View a specific session transcript
study session <session_id>
```

## Metadata & Links

```bash
# Update metadata
study meta <id> --tags "tag1,tag2"
study meta <id> --domain "mathematics"
study meta <id> --difficulty 3
study meta <id> --source "https://example.com"

# Link topics
study link <id1> <id2> --type prereq
study link <id1> <id2> --type related

# Unlink topics
study unlink <id1> <id2>
```

## Knowledge Graph

```bash
# Graph summary
study graph
  # Shows: total nodes, total edges, top tags, domains

# Topic connections
study graph <id>
  # Shows: prerequisites, related topics, shared-tag connections

# Export graph for visualization
study export-graph --format json
```

## Notifications

```bash
# Send macOS notification with today's summary
study notify

# Setup daily notifications
study notify --setup
  # Outputs crontab entry for daily reminders
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
