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
