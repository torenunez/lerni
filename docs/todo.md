# Lerni — Backlog

Explore is active. Study work below is parked, not cancelled — it is kept so it
can be resumed if Explore does not justify continuing. Completed work is recorded
in [`progress.md`](./progress.md), not here.

## Explore — Active

Milestones are defined in [`roadmap.md`](./roadmap.md). Implemented code, human
review, app qualification, and a student session are separate kinds of progress.

### M1 — Educator authoring and documentation (developer)
- [ ] Review and merge GitHub PR #2 (`educator-paths-v1` and document adoption)
- [ ] Collect educator feedback on the templates and adjust wording (not the schema) as needed

### M2 — First reviewed walkthrough (educator and parent)
- [ ] Choose a fitting interest and one concrete learning goal
- [ ] Sketch three to five activities; prepare and genuinely review the first
- [ ] Optional short walkthrough; private observations; revise one thing

### M3 — Authored local app slice (developer, then parent rehearsal)
- [ ] Environment qualification — bind command variables, qualify the runtime tier the slice needs, record setup decisions outside the repo
- [ ] Reconcile PR-03 runtime, PR-06 UI, and PR-08 verification specs for the reduced slice; write its acceptance checks (PRD APP-01–APP-08) before relying on them
- [ ] Translate one reviewed path step into one packaged lesson, with a separate path/step/revision mapping record
- [ ] Genuine exact-content attestations for that lesson (TOML `review.attestations`)
- [ ] Local UI: visible text, curated visuals and text alternatives, authored choices, hints, completion, parent Start/Stop/Reset, in-memory state
- [ ] Verify session ownership, Stop/Reset, approval and integrity checks, no persistent storage, no outbound requests, Study compatibility
- [ ] Adult rehearsal and parent authorization

### Later (M4–M6 and optional capabilities)
- [ ] M4 — student app session, second path from a different interest, follow-up recall
- [ ] M5 — `educator-paths-v1` delivery mapping, then strict import/compilation (PR-09) and curriculum persistence (PR-10)
- [ ] M6 — explainable recommendations from reviewed connections; reviewed graph-growth proposals (PR-11)
- [ ] Optional, each with its own qualification: deterministic safety/grounding and tutor capability (PR-04, PR-07A), telemetry lifecycle (PR-05), read-aloud, push-to-talk (PR-07)

## Study — Optional hardening

Study is feature-complete but not hardened. These are open.

### Tests
- [ ] Fix `tests/conftest.py` fixtures to use current models
- [ ] Add database layer tests (`db.py` CRUD operations)
- [ ] Add CLI integration tests (typer `CliRunner`)
- [ ] Manual end-to-end test: full Feynman workflow → review → grade cycle

### Code quality
- [ ] Clear ruff lint debt in `src/` — 99 violations as of 2026-08-23, 74 auto-fixable. Breakdown: 55 `UP045` (`Optional[X]` → `X | None`), 19 `E501` line length, 9 `F541` empty f-strings, 6 `B904` missing `raise ... from`, 6 `I001` import order, 3 assorted. None are correctness bugs. Needs its own PR — the pre-commit gate lints only staged files, so this debt is invisible until touched.
- [ ] Consolidate duplicate `get_lerni_dir()` into one module
- [ ] Add `study --version` flag
- [ ] Run mypy — fix type errors
- [ ] Review edge cases: empty DB, invalid UUIDs, concurrent access

## Study Phase 2 — Parked AI Agents and Skills

### Infrastructure
- [ ] Base agent class (`src/lerni/agents/base.py`) — API call abstraction, turn management, transcript capture
- [ ] `AISession` model for transcript storage
- [ ] Schema migration v4 — add `ai_sessions` table
- [ ] Prompt file loading with variable substitution (`{topic_title}`, `{simple_explanation}`, etc.)
- [ ] API key configuration in `config.toml`
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

## Study Phase 3–5 — Parked

### Analytics and export
- [ ] `study stats` — global statistics (total topics, reviews, average grade, streaks)
- [ ] `study stats <id>` — per-topic analytics
- [ ] Grade trend visualization (ASCII charts)
- [ ] `study export --all` — full JSON backup
- [ ] `study import` — restore from backup
- [ ] `study export-graph` — knowledge graph JSON

### Visualization
- [ ] Plotly HTML reports for grade progression
- [ ] Neo4j export for graph visualization
- [ ] `launchd` integration (persistent notifications replacing cron)
- [ ] Configurable reminder times

### Native apps
- [ ] macOS menu bar app (quick review access)
- [ ] iOS companion app (review on mobile)
- [ ] Interactive mindmap UI

### Additional agents
- [ ] Interviewer Agent — technical interview simulation
- [ ] Connector Agent — suggests links between topics

### Advanced features
- [ ] Rich media support (images, LaTeX)
- [ ] Local LLM support (ollama) for offline AI
- [ ] Collaborative features (share topic packs)
