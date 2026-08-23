# Progress Log

## 2025-01-31

### Done
- Reviewed existing documentation (spec.md, roadmap.md, PRD.md, agent prompts)
- Created implementation plan for Phase 1 MVP
- Established progress tracking workflow

### Decisions
- Using stdlib dataclasses over Pydantic (no external deps for Phase 1)
- Raw SQL with Repository pattern (simple, swappable later)
- UUID4 for IDs (offline-safe)
- Metadata stored as JSON columns (flexible schema)
- tomllib for config (Python 3.11+ stdlib)

### Implementation Order
1. pyproject.toml + directory structure
2. models.py (Topic, TopicVersion, Review)
3. sm2.py (algorithm)
4. db.py (schema, repositories)
5. config.py, editor.py
6. CLI commands (topic → review → organize → notify)

### Blockers
- None

---

## 2025-01-31 (continued)

### Done
- Created pyproject.toml with dependencies (typer, rich, pytest, mypy, ruff)
- Set up src/lerni/ directory structure with commands/ subpackage
- Implemented all Phase 1 modules:
  - `models.py` - Topic, TopicVersion, Review, ScheduleState, TopicMetadata dataclasses
  - `sm2.py` - SM-2 algorithm with 35 passing tests
  - `db.py` - SQLite schema, connection management, repositories
  - `config.py` - TOML config loading
  - `editor.py` - External editor integration
  - `cli.py` - Main typer app with command routing
  - `commands/topic.py` - new, edit, snapshot, show, history, delete
  - `commands/review.py` - review, skip, today
  - `commands/organize.py` - list, search, meta, link, unlink
  - `commands/notify.py` - macOS notifications via osascript
- Created Python 3.11 virtual environment (.venv)
- All 35 SM-2 tests passing
- CLI verified working: `study --help`, `study list`, `study today`

### Files Created
```
src/lerni/
├── __init__.py
├── __main__.py
├── cli.py
├── commands/
│   ├── __init__.py
│   ├── topic.py
│   ├── review.py
│   ├── organize.py
│   └── notify.py
├── models.py
├── db.py
├── sm2.py
├── config.py
└── editor.py

tests/
├── __init__.py
├── conftest.py
└── test_sm2.py

pyproject.toml
```

### Next
- Test full Feynman workflow (`study new "Topic"`)
- Add more integration tests for CLI commands
- Consider adding database tests

---

## 2025-01-31 (Review Flow Redesign)

### Done
- Redesigned review workflow based on user feedback:
  - Topics now structured as **questions** (not just titles)
  - Review shows question + metadata but **hides previous answer**
  - User attempts explanation from scratch via editor
  - If can't recall, THEN show previous answer and identify gaps
  - Track `attempted_explanation` and `recalled_from_memory` per review

### Schema Changes (v1 → v2)
- Added `question` column to `topics` table
- Added `attempted_explanation` and `recalled_from_memory` to `reviews` table
- Migration auto-populates existing topics with "Explain: {title}"

### Files Modified
- `models.py` - Added `question` to Topic, `attempted_explanation`/`recalled_from_memory` to Review
- `db.py` - Schema v2, migration logic, updated repositories
- `commands/topic.py` - `study new` now requires question prompt, `study show` displays question
- `commands/review.py` - Complete rewrite with 2-stage recall flow

### New Review Flow
1. **Stage 1**: Show question + metadata (hide answer)
   - User writes explanation from scratch in editor
   - If recalled: grade 3-5
2. **Stage 2** (only if couldn't recall): Show previous answer
   - User identifies gaps
   - Grade 0-2

### Testing
- Database migration verified working
- Existing topics migrated with default question
- Interactive review flow ready for manual testing

### Next
- Manual testing of `study new` and `study review` in terminal

---

## 2025-01-31 (Schema Restructure)

### Done
Major schema restructure based on data model discussion:

1. **New entity: Concept** - Knowledge graph nodes with typed relationships (DAG)
   - Supports multiple parents (e.g., Decorators → Python AND Design Patterns)
   - Relationship types: parent, prerequisite, related
   - Aliases for fuzzy matching

2. **Renamed entities:**
   - Topic → Question (the study card, prompt shown during review)
   - TopicVersion → Answer (versioned Feynman content)

3. **Removed:**
   - TopicMetadata (replaced by Concept relationships)
   - Title field (merged into question prompt)

### Schema Changes (v2 → v3)

**New tables:**
- `concepts` (id, name, aliases, description)
- `concept_edges` (from_concept_id, to_concept_id, relationship)

**Renamed tables:**
- `topics` → `questions`
- `topic_versions` → `answers`

**Migration:**
- Existing topics migrated to questions
- Existing topic_versions migrated to answers
- Questions initially uncategorized (concept_id = NULL)

### Files Modified/Created
- `models.py` - New Concept, ConceptEdge, renamed Question/Answer
- `db.py` - Schema v3, migration, new repositories (ConceptRepository, ConceptEdgeRepository, QuestionRepository, AnswerRepository)
- `commands/question.py` - New file (replaces topic.py)
- `commands/review.py` - Updated for Question/Answer terminology
- `commands/organize.py` - Added concept management commands
- `commands/notify.py` - Updated for QuestionRepository
- `cli.py` - New command routing with concept subgroup

### New CLI Commands

```bash
# Question commands
study new                    # Create question with Feynman workflow
study show <id>              # Show question and answer
study assign <id> <concept>  # Assign question to concept

# Concept commands
study concept new "Name"     # Create concept
study concept list           # Show concept tree
study concept show "Name"    # Show concept details
study concept link A B --type parent|prerequisite|related
study concept unlink A B
study concept delete "Name"
```

### Testing
- CLI help verified
- Migration v2→v3 successful
- Concept tree display working (shows DAG with multiple parents)
- Concept relationships (parent, prerequisite) working
- Question filtering by concept working

### Next
- Manual testing of `study new` and `study review` in terminal
- Add database tests for new schema

---

## 2026-08-23 (Explore Pivot — Documentation Alignment)

### Decisions

- **Pivot to Explore-first.** Development focus moves from Study to Explore: a
  parent-supervised, localhost experience taking a child from an existing interest
  (fast cars) down to a fundamental idea (average acceleration).
- **Study is maintenance-only.** Phase 1 stays feature-complete and compatible.
  Phases 2–5 are parked, not deleted. Study's `study` entry point and database
  schema are unchanged by this work.
- **First-slice boundary selected.** The first slice is deterministic and
  account-free: reviewed lesson content, an application-owned state machine, local
  policy and grounding, local telemetry with parent controls, and a localhost UI.
  FastAPI, NetworkX, shared Study database state, token streaming, hosting, and the
  garage concept are all deferred — none contributes to the first learning signal.
- **Provider- and model-neutral capability architecture.** No model, provider, SDK,
  or hosted service is required or named. Tutor, speech-to-text, and harm-gate
  capabilities are replaceable adapters selected by explicit runtime qualification,
  loaded out-of-process, configured with `env:` credential references. With none
  configured, the lesson completes on authored content.
- **Read-aloud first, push-to-talk second.** Browser read-aloud is cheap and
  optional, so it lands with the first usable build. Audio *input* is a separate
  concern and follows immediately behind, through an isolated speech-to-text
  adapter — it does not block the lesson core.
- **Local telemetry, separate database.** Sanitized turns, structured events, and
  parent observations go to their own Explore SQLite file under an operator-owned
  private root. No child name, no raw blocked text, no audio, no credentials. Parent
  controls retention, export, and deletion. Explicitly not described as anonymous.

### Correction

The draft framing "that 0–60 number has a name: acceleration" is **scientifically
wrong** and has been corrected throughout. A 0–60 figure is *elapsed time*.
Acceleration is change in velocity over time. The lesson now teaches the
distinction rather than collapsing it, and the fact sheet avoids mutable
leaderboard claims.

### Lesson sequence vs. concept graph

These are now explicitly separate. A `ConceptEdge` states a domain relationship
("this concept requires that prerequisite"). A lesson step states pedagogy ("teach
this next"). Treating one graph edge as one tutor turn would corrupt both models,
so the first slice uses an explicit authored lesson sequence and defers graph
integration entirely. Hop count is recorded as an authoring heuristic, not a
difficulty measure.

### Done

- Restored the `.claude/` hooks and `settings.json` lost to a working-tree reset,
  and repaired the pre-commit quality gate, which had never passed: it called bare
  `ruff` and `pytest` (present only in `.venv/bin`) and linted all of `src/`, which
  carries 99 pre-existing style violations. Lint is now scoped to staged Python
  files; pytest still runs the full suite.
- Imported the 29-file Explore implementation bundle into `plans/` under version
  control, so plan revisions become reviewable history.
- Aligned all eight product documents on the two-mode model: `docs/mission.md` and
  `docs/PRD.md` rewritten, `docs/roadmap.md` merged into Study Track / Explore
  Track, `docs/todo.md` reordered Explore-first with Study work parked,
  `docs/spec.md` extended with the Explore contracts, `README.md` and `CLAUDE.md`
  updated.
- Corrected `CLAUDE.md`, which documented `src/lerni/agents/` and `src/lerni/skills/`
  modules that do not exist on disk. The tree now reflects reality.

### Status

**Documentation only. No Explore code exists.** This entry records a design
decision and a documentation change, not an implementation. `src/lerni/explore/`
has not been created.

Commits were made on branch `explore/pr-01-documentation` at the user's explicit
request. The implementation plans otherwise assume no commits are made without
that authorization.

### Next

- Lesson domain, canonical serialization, and the strict TOML catalog
- Reviewed Chain-1 acceleration content, with real source retrieval dates and
  human review attestations — not fabricated to make checks pass
- Deterministic state engine
