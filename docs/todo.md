# Lerni — Backlog

Explore is active. Study work below is parked, not cancelled — it is kept so it
can be resumed if the Explore pilot does not justify continuing.

## Explore Phase 1 — Active

Mirrors the first-slice execution order. The implementation bundle is in
[`plans/`](../plans/); each item maps to a PR unit there.

- [ ] 1. **Environment qualification** — bind command variables, qualify required vs optional runtime tiers, record setup decisions outside the repo
- [ ] 2. **Documentation** — align the eight product documents around the two-mode model
- [ ] 3. **Lesson domain** — immutable lesson types and canonical serialization
- [ ] 4. **Catalog and approved content** — strict TOML catalog, corrected Chain-1 acceleration content, curated accessible SVG
- [ ] 5. **State engine** — deterministic intro / teach / check / hint / complete transitions
- [ ] 6. **Safety and grounding** — sanitization, deterministic input/output policy, fact and numeric grounding checks
- [ ] 7. **Tutor capability** — provider-neutral tutor contract, process boundary, authored fallback, mandatory harm gate for any generated child-facing output
- [ ] 8. **Telemetry** — separate Explore SQLite store, sanitized turns, parent observations, export, retention, transactional deletion, managed wipe
- [ ] 9. **Gradio visual and read-aloud** — readiness-gated localhost UI, curated visual, optional browser read-aloud
- [ ] 10. **Push-to-talk** — qualified speech-to-text port, bounded WAV capture, editable transcript, guaranteed cleanup
- [ ] 11. **Verification** — privacy boundary tests, distribution checks, failure injection, Study compatibility
- [ ] 12. **Parent-supervised pilot** — bounded first session, then an explicit decision whether to continue

## Explore Phase 2 — Parent Curation and Bounded Recommendations

**Gate**: starts only after item 12 and an explicit parent decision to continue.

- [ ] 13. **Curation workbook and dry-run CSV importer** — portable templates, strict offline validation, no activation
- [ ] 14. **Early approved graph priming and transparent parent recommendation candidates** — immutable batches, explicit activation, deterministic explainable candidates requiring parent approval

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
