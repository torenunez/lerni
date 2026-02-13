# Lerni — Backlog

## Bugs & Known Issues

All resolved.

## Phase 1: Polish & Hardening

### Documentation Sync
- [ ] Update `CLAUDE.md` project overview, structure, and data model names
- [ ] Update `README.md` status section and feature list
- [ ] Check off completed items in `docs/roadmap.md`
- [ ] Rewrite `docs/spec.md` data model to match v3 schema (`Concept`, `ConceptEdge`, `Question`, `Answer`)
- [ ] Update `docs/spec.md` CLI reference to match implemented commands (`concept` subgroup, `assign`, etc.)

### Tests
- [ ] Fix `tests/conftest.py` fixtures to use current models
- [ ] Add database layer tests (`db.py` CRUD operations)
- [ ] Add SM-2 algorithm tests (`sm2.py`)
- [ ] Add CLI integration tests (typer CliRunner)
- [ ] Manual end-to-end test: full Feynman workflow → review → grade cycle

### Code Quality
- [ ] Consolidate duplicate `get_lerni_dir()` into one module
- [ ] Add `study --version` flag
- [ ] Run mypy — fix type errors
- [ ] Run ruff — fix lint issues
- [ ] Review edge cases: empty DB, invalid UUIDs, concurrent access

## Phase 2: AI Agents

### Infrastructure
- [ ] Base agent class (`src/lerni/agents/base.py`) — API call abstraction, turn management, transcript capture
- [ ] `AISession` model for transcript storage
- [ ] Schema migration v4 — add `ai_sessions` table
- [ ] Prompt file loading with variable substitution (`{topic_title}`, `{simple_explanation}`, etc.)
- [ ] API key configuration in `config.toml` (Anthropic / OpenAI)
- [ ] Default prompt files (`agents/beginner.md`, `agents/expert.md`)

### Beginner Agent
- [ ] Socratic mode — probing "why" and "how" questions
- [ ] ELI5 mode — confused beginner roleplay
- [ ] Analogy mode — push for real-world examples
- [ ] 3–5 turn session management with configurable limit

### Expert Agent
- [ ] Rigor levels 1–5 (Gentle → Harsh)
- [ ] Gap identification from final explanation
- [ ] SM-2 grade suggestion

### CLI Integration
- [ ] `--ai` flag on `study review`
- [ ] `--mode` option (socratic, eli5, analogy)
- [ ] `--rigor` option (1–5)
- [ ] `study coach <id> --agent <beginner|expert>` — standalone sessions
- [ ] `study sessions <id>` — list AI sessions for a topic
- [ ] `study session <session_id>` — view transcript

### Tests
- [ ] Unit tests for agent base class (mock API)
- [ ] Integration tests for beginner/expert agents
- [ ] CLI tests for `--ai` flag and agent commands

## Phase 3: Analytics & Export

- [ ] `study stats` — global statistics (total topics, reviews, average grade, streaks)
- [ ] `study stats <id>` — per-topic analytics
- [ ] Grade trend visualization (ASCII charts)
- [ ] `study export --all` — full JSON backup
- [ ] `study import` — restore from backup
- [ ] `study export-graph` — knowledge graph JSON

## Phase 4: Visualization

- [ ] Plotly HTML reports for grade progression
- [ ] Neo4j export for graph visualization
- [ ] `launchd` integration (persistent notifications replacing cron)
- [ ] Configurable reminder times

## Phase 5: Future Ideas

### Native Apps
- [ ] macOS menu bar app (quick review access)
- [ ] iOS companion app (review on mobile)
- [ ] Interactive mindmap UI

### Additional Agents
- [ ] Interviewer Agent — technical interview simulation
- [ ] Connector Agent — suggests links between topics

### Advanced Features
- [ ] Rich media support (images, LaTeX)
- [ ] Local LLM support (ollama) for offline AI
- [ ] Collaborative features (share topic packs)
