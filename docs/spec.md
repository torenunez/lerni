# Lerni — Technical Specification

> For vision and principles, see [mission.md](./mission.md)
> For roadmap and phases, see [roadmap.md](./roadmap.md)
> For Explore implementation contracts, see [`plans/`](../plans/) (normative for
> execution; this file holds product-facing Study + Explore contracts)

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

# AI Agents (Study — parked)

**Status**: parked. This section describes a Study Phase-2 design that is not
implemented. It is retained as a design record. Nothing here is a requirement,
and no provider or model named below is selected.

This design is separate from the Explore tutor capability documented later in
this file. Do not treat the two as the same runtime.

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
# Illustrative only. No provider or model is selected or required.
# The operator supplies a credential reference, never a literal key.
provider = "<operator-selected>"
model = "<operator-selected>"
```

---

# Tech Stack

## MVP
- **Language**: Python 3.11+
- **Database**: SQLite with `sqlite3` stdlib
- **CLI Framework**: `typer`
- **Notifications**: `osascript` (macOS native)
- **Config**: `tomllib` (Python 3.11+)

## Explore
- **UI**: Gradio, installed as an optional extra; the core install does not require it
- **Lesson content**: packaged TOML plus a curated SVG asset, loaded via `importlib.resources`
- **Telemetry**: a separate SQLite database, `sqlite3` stdlib
- **Curation**: portable CSV, `csv` and `json` stdlib

## Runtime capabilities (both modes)
No model, provider, SDK, or hosted service is required or selected. Text
generation, speech-to-text, and any additional harm gate are **replaceable
capabilities** chosen by explicit runtime qualification, loaded out-of-process,
and configured by an operator-owned profile that holds credential *references*
rather than credential values. An unqualified capability is disabled and the
authored fallback runs instead.

Provider-specific code lives in separately reviewed adapter distributions
outside the core package.

## Future
- **Graph DB**: Neo4j with `neo4j` driver
- **Visualization**: Plotly
- **Desktop App**: Tauri or Swift

---

# Open Questions

## Study (parked)

1. **Turn limit**: configurable per-session or global only?
2. **Transcript format**: JSON array or markdown?
3. **Grade suggestion**: should an expert agent suggest an SM-2 grade, or only give qualitative feedback?

## Explore (open)

4. **Deployment target**: undecided and deliberately deferred. The first slice is localhost-only. No hosting choice has been made.
5. **Curriculum metadata schema**: how much lesson metadata belongs in the curriculum database versus the packaged content, once more than one lesson exists.
6. **Study/Explore convergence**: whether the two modes should eventually share a concept store, and on what evidence. `ConceptEdge` semantics and lesson sequence are deliberately separate today; merging them prematurely would corrupt both.
7. **Spaced resurfacing for Explore**: whether SM-2 semantics fit a child's interest-driven return at all, or whether a different retention model is needed.
8. **Local capability adapters**: whether a fully local generation or speech engine can meet the qualification bar on ordinary family hardware.

---

# Product Modes

Lerni is one repository with two modes.

| | Study | Explore |
|---|---|---|
| Entry point | `study` (typer CLI) | `lerni-explore` (planned; local browser page) |
| Package | `src/lerni/` | `src/lerni/explore/` (planned) |
| Database | `~/.lerni/lerni.db` | separate Explore SQLite files under an operator-owned private root |
| Status | Feature-complete, maintenance-only | Active development |

**Reuse boundary.** Study and Explore share a repository and a language. They do
not share a database, a runtime, a scheduler, or an agent framework. Explore does
not read or write Study's database. Study's `Concept` and `ConceptEdge` models
describe domain relationships; they do not drive Explore's lesson sequence.

Unifying the two is the intended direction. It is not the current state, and it
will happen on evidence from a real pilot rather than by assumption.

**The concept graph is future curriculum structure, not a runtime controller.**
Neither Study's concept graph nor the planned Explore curriculum graph drives the
first slice. The first lesson is explicit packaged application data with an
authored sequence. The Explore curriculum graph arrives in Phase 2, after a pilot,
and even then it structures *authoring* and produces parent-reviewable
recommendation candidates — it does not select what the child sees next at
runtime. No graph traversal advances a session.

# Explore Architecture

**Package structure** (planned, `src/lerni/explore/`): immutable lesson domain and
canonical serialization; a strict packaged content catalog; a deterministic session
engine; runtime configuration and private path derivation; an out-of-process
capability boundary; safety, sanitization, and grounding; a local telemetry store
and data-lifecycle service; pure presenter callbacks; and a thin Gradio composition
layer over those callbacks.

**Runtime profile.** One strict, provider-neutral TOML file supplied by absolute
path — no home-directory or repository-relative discovery. It is operator-owned,
owner-readable only, size-bounded, and rejected on any unknown key. It holds
credential *references* of the form `env:VARIABLE_NAME`, never credential values.

**Immutable lesson content.** Lessons are frozen data structures loaded from
packaged TOML. Content carries a schema version, a content version, review
metadata, and hashes. Nothing at runtime mutates a lesson.

**Catalog validation.** The catalog is parsed strictly and rejects unknown fields,
unapproved content, and hash mismatches. Content that is not approved does not
reach a child.

**Deterministic state engine.** The application owns intro, teach, check, hint,
and completion. Transitions are a pure function of current state and validated
input. No generated text can cause a transition.

**Capability interfaces.** Tutor, speech-to-text, and additional harm-gate
capabilities are typed protocols. Implementations are loaded in a bounded helper
subprocess over a length-prefixed JSON frame protocol with an explicit codec
allowlist — no pickle, no arbitrary object graphs. Calls have deadlines; the
process group is terminated on timeout.

**Application-owned safety.** Policy runs locally and deterministically on
complete responses, never on partial streamed output.

**Local telemetry.** A separate SQLite database holding sanitized turns,
structured events, and parent observations.

**Gradio presentation.** Presenter callbacks are pure and independently testable.
Gradio is a thin composition layer bound to `127.0.0.1` with no share URL, and is
an optional install extra.

**Speech lifecycle.** Recordings live only under a managed private temporary path
and are cleaned up on every path — success, timeout, crash, and malformed output.

## Lesson Contract

A lesson package declares:

- **Schema version** — the structural version of the lesson format
- **Content version** — the version of this lesson's authored content
- **Review metadata** — which reviews were performed, on what date, against which exact content hash
- **Explicit sequence** — an ordered list of steps, owned by the author
- **Authored steps** — the text shown at each step, including the fallback text used when no tutor is available
- **Retrieval check and hints** — one check with choices, exactly one correct, plus an ordered progressive hint sequence and a reveal
- **Grounding facts and sources** — the bounded set of facts a tutor may draw on, each traceable to an approved source
- **Numeric claims** — recorded separately so they can be checked against generated output
- **Local curated asset reference** — a package-relative path plus the exact SHA-256 of the asset bytes

Lesson order comes from the authored sequence alone. It is never derived from
concept graph edges.

## Tutor Contract

Provider-neutral, described only by what crosses the boundary.

**Receives**: sanitized learner text; the current lesson snapshot with the answer
key removed; the reviewed facts in scope for the current step.

**Returns**: a bounded draft string, or a typed failure.

**Cannot**: read credentials from lesson data; determine whether an answer is
correct; advance, unlock, or complete anything; reveal or grade the retrieval
check; bypass the output gate; or cause a state transition.

The complete draft is gated before display. A rejected draft never reaches the
child and never reaches telemetry.

## Safety Contract

- **Deterministic policy precedence** — local rules decide first; an optional
  external check may only tighten a decision, never loosen one.
- **Best-effort redaction** — sanitization is applied before text leaves the
  application, and is described as best-effort rather than as a guarantee.
- **Grounding, citation, and numeric checks** — generated text must be supported
  by the current reviewed facts; numeric claims are checked against the recorded
  values.
- **Authored fallback** — always available; runs whenever a capability is absent,
  unqualified, slow, or failing.
- **Mandatory harm gate** — any generated, child-facing tutor output additionally
  requires a separately qualified input and output harm gate. Without one, the
  authored fallback stays active.

**Residual limitations.** These are prototype guardrails plus a present parent.
They are not moderation, not a compliance posture, and not a guarantee. A
provider's own safety behavior is not an application safety boundary. Sanitization
is heuristic and can miss. The turn cap bounds exposure; it does not eliminate it.

## Explore Telemetry Contract

- **Separate database** — its own SQLite file under the private runtime root.
  Explore never writes to Study's database.
- **Sanitized accepted turns** — or a fixed withholding marker when content was
  not persistable. Raw blocked text is never stored.
- **Structured events only** — enumerated event types with typed fields. No
  arbitrary JSON blobs, no exception detail, no stack traces.
- **Parent observations** — short sanitized notes entered by the parent.
- **Retention** — an operator-chosen number of days, or explicit manual retention.
  Purge runs at startup and maintenance; no wall-clock scheduler is promised.
- **Export** — JSON, written under a managed exports path.
- **Transactional deletion** — deleting a session removes every dependent row in
  one transaction.
- **Excluded** — child names, raw rejected content, audio of any kind,
  credentials, provider identifiers, and free-form JSON.

Telemetry is data-minimized. It is **not** anonymous, and it is not described as
PII-free. Managed wipe covers Lerni's registered local paths only; it cannot reach
OS backups, filesystem snapshots, or any external service's retained copies.

## Multimodal Contract

- **Reviewed visual assets** — curated, hash-pinned, with alt text and a recorded
  accessibility review.
- **Visible text first** — text is always authoritative and always present.
- **Optional browser read-aloud** — detected at runtime, off by default, enabled
  only by a parent. It never replaces visible text.
- **Optional microphone transcription** — push-to-talk only, never open-mic,
  enabled only by a parent after reviewing the audio route.
- **Transcript preview and edit** — the child sees and can correct the transcript
  before it is submitted; it then follows the same policy path as typed input.
- **Recording cleanup attempt** — on every path, including failure. Raw audio
  reaches the speech capability before transcript redaction; this is disclosed to
  parents rather than concealed.
- **No child image upload** — the child cannot send images into the system.

## Parent Curation and Curriculum Graph Contract

- **Workbook tabs and privacy exclusions** — a fixed ordered tab set covering
  interests, concepts, sources, facts, nudges, edges, assets, lessons, lesson
  steps, checks, choices, hints, reviews, and observations. No child name,
  identifier, birthday, school, location, transcript, audio, medical or
  behavioral label, or credential may appear in any tab.
- **Portable CSV bundle and manifest hashes** — the workbook is exported to UTF-8
  CSV with a manifest recording the SHA-256 of each exported file. CSV is the
  authoritative format; a spreadsheet tool is an optional editor.
- **Strict row and cross-tab validation** — offline, deterministic, and fully
  local. Spreadsheet validation is not a security boundary.
- **Approved-only activation** — only rows carrying required active review
  attestations can prime the graph or compile child-facing content.
- **Separate content database and import batches** — imports are staged as
  immutable batches; re-importing identical bytes is idempotent, and changed bytes
  under the same batch identity are rejected.
- **Distinct record types** — Interest, Concept, Fact, Nudge, Edge, Lesson, and
  LessonStep are separate records with separate semantics.
- **Graph relationship semantics** — an edge states a domain relationship between
  concepts. It does not state what to teach next.
- **Explicit lesson sequence independent of graph edges** — lesson order comes
  from authored step indices. One edge does not equal one tutor turn, and hop
  count is an authoring heuristic, not a difficulty measure.
- **Immutable lesson-version curriculum bindings** — telemetry binds to an exact
  lesson version and content hash so a record always means what it meant when written.
- **Separate parent-state database** — scope, readiness, recommendation decisions,
  and assignments live apart from telemetry and curriculum.
- **Parent-attested prerequisite readiness** — readiness is asserted by a human
  from actual observation, or left unknown. It is never inferred to unblock a
  recommendation.
- **Deterministic, explainable recommendation candidates** — every candidate
  carries the reason it was produced, reviewable before approval.
- **Mandatory parent approval before child visibility** — nothing becomes visible
  to a child automatically.
- **Aggregate observation export** — without transcripts or audio.
- **No Google API requirement** — Google Sheets is an optional editing convenience.
  The application never reads a live sheet. Future sheet-source adapters remain
  optional and are not part of the first version.
