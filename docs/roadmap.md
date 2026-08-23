# Lerni — Roadmap

Lerni has two tracks. **Study** is feature-complete and receives fixes only.
**Explore** is where active development happens.

Study Phases 2–5 below are parked, not cancelled. They remain documented so
the work is recoverable if the Explore pilot does not justify continuing.

---

# Study Track

**Status**: Phase 1 complete and maintenance-only. Phase 1 hardening items in
[`todo.md`](./todo.md) remain open — feature-complete is not the same as hardened.

## Phase 1: MVP (Core System)

**Goal**: Fully functional local study system without AI

### Data Layer
- [x] SQLite database setup (`~/.lerni/lerni.db`)
- [x] Concept model (knowledge graph nodes)
- [x] ConceptEdge model (typed relationships: parent, prerequisite, related)
- [x] Question model with SM-2 schedule state
- [x] Answer model (immutable Feynman snapshots)
- [x] Review model with SM-2 state

### Feynman Workflow
- [x] `study new` - Full 4-step flow
- [x] `study new --quick` - Quick capture (step 1 only)
- [x] `study edit` - Minor edits without versioning
- [x] `study snapshot` - Create new version

### Review System
- [x] SM-2 algorithm implementation
- [x] `study review` - Review session workflow
- [x] `study skip` - Skip and reschedule
- [x] `study today` - Daily summary

### Organization
- [x] `study list` - List with filters (concept, due)
- [x] `study search` - Full-text search
- [x] `study show` / `study history` - View question and answers
- [x] `study meta` - Update metadata
- [x] `study assign` - Assign question to concept
- [x] `study concept new/list/show/link/unlink/delete` - Knowledge graph management

### Notifications
- [x] `study notify` - macOS notification
- [x] `study notify --setup` - Cron setup instructions

---

## Phase 2: AI Agents

**Status**: maintenance-only — parked while Explore is active. Not deleted; not scheduled.

**Goal**: Optional AI-assisted coaching

### Infrastructure
- [ ] AISession model for transcript storage
- [ ] API key configuration — operator-selected, credential reference only
- [ ] Prompt file loading and variable substitution

### Beginner Agent
- [ ] Socratic mode - Probing questions
- [ ] ELI5 mode - Confused beginner roleplay
- [ ] Analogy mode - Push for real-world examples
- [ ] 3-5 turn session management

### Expert Agent
- [ ] Rigor levels 1-5
- [ ] Gap identification
- [ ] Grade suggestion

### CLI Integration
- [ ] `--ai` flag for review command
- [ ] `--mode` and `--rigor` options
- [ ] `study coach` - Standalone agent sessions
- [ ] `study sessions` / `study session` - View transcripts

---

## Phase 3: Analytics & Export

**Status**: maintenance-only — parked while Explore is active. Not deleted; not scheduled.

**Goal**: Insights and data portability

- [ ] `study stats` - Global statistics
- [ ] `study stats <id>` - Per-topic analytics
- [ ] Grade trend visualization (ASCII charts)
- [ ] `study export --all` - Full JSON backup
- [ ] `study import` - Restore from backup
- [ ] `study export-graph` - Knowledge graph JSON

---

## Phase 4: Visualization

**Status**: maintenance-only — parked while Explore is active. Not deleted; not scheduled.

**Goal**: Rich visual interfaces

- [ ] Plotly HTML reports for grade progression
- [ ] Neo4j export for graph visualization
- [ ] launchd integration (persistent notifications)
- [ ] Configurable reminder times

---

## Phase 5: Future Ideas

**Status**: maintenance-only — parked while Explore is active. Not deleted; not scheduled.

**Documented for later consideration**:

### Native Apps
- macOS menu bar app (quick review access)
- iOS companion app (review on mobile)
- Interactive mindmap UI

### Additional Agents
- **Interviewer Agent** - Technical interview simulation
- **Connector Agent** - Suggests links between topics

### Advanced Features
- Rich media support (images, LaTeX)
- Local LLM support (ollama) for offline AI
- Collaborative features (share topic packs)

---

# Explore Track

**Status**: active.

Explore is sequenced as a deterministic core first, capabilities second, and
content curation only after a real parent-supervised pilot has happened. Each
phase gate is a human decision, not a code milestone.

The full implementation bundle lives in [`plans/`](../plans/).

## Explore Phase 1A — Deterministic safe slice

**Goal**: a child can complete one reviewed lesson with no AI, no microphone,
and no network.

- [ ] Environment qualification (required vs optional runtime tiers)
- [ ] Documentation alignment
- [ ] Immutable lesson model
- [ ] Strict TOML lesson catalog
- [ ] Corrected, reviewed acceleration lesson content
- [ ] Deterministic intro / teach / check / hint / complete state machine
- [ ] Application-owned input, output, and grounding policies
- [ ] Local sanitized telemetry with parent export, deletion, and retention
- [ ] Gradio localhost UI
- [ ] Curated, accessible visual asset
- [ ] Optional browser read-aloud
- [ ] Typed input as the universal fallback
- [ ] Tutor capability contract with authored fallback (no live adapter required)

Phase 1A is account-free and authored-only. Qualifying a real tutor / harm-gate
adapter is **1A+** (see PR-07A in `plans/`), required before any LLM pilot — not
part of the deterministic safe-slice acceptance.

## Explore Phase 1B — Push-to-talk

**Goal**: a child can speak instead of typing, without audio being retained.

- [ ] Speech-to-text capability protocol
- [ ] Bounded microphone recording under a managed private path
- [ ] Selected adapter qualification
- [ ] Editable transcript preview before submission
- [ ] Guaranteed cleanup attempt on every path, including failure
- [ ] No audio fields in the telemetry schema or export
- [ ] Typed fallback under every failure mode

## Explore Phase 2 — Content and parent curation

**Gate**: begins only after the first pilot and an explicit parent decision to continue.

- [ ] Chains 2–4 fact sheets
- [ ] Portable spreadsheet workbook — interests, concepts, sources, facts, nudges, edges, lessons, lesson steps, observations
- [ ] Manual CSV export with manifest and hash validation
- [ ] Dry-run import, staged batches, and explicit activation
- [ ] Early local curriculum graph, with domain edges kept separate from lesson sequence
- [ ] Content approval workflow
- [ ] Parent curation interface
- [ ] Explicit lesson-to-concept mapping
- [ ] Schema decision for curriculum metadata
- [ ] Deterministic next-lesson rules
- [ ] Transparent, parent-only, graph-backed recommendation candidates
- [ ] Separate parent state for scope, readiness, decisions, and assignments
- [ ] Garage — only if the first pilot supports the need

## Explore Phase 3 — Retention and recommendation

- [ ] Delayed recall checks
- [ ] Careful integration with spaced scheduling, only if the semantics genuinely fit
- [ ] Evidence-informed and adaptive recommendation experiments, only after the bounded Phase-2 rules have been evaluated
- [ ] Parent approval required before any recommendation becomes child-visible
- [ ] Bilingual content and richer speech work
- [ ] Privacy and legal review before any broader access
