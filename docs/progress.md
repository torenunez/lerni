# Progress Log

## Current state

**Verified 2026-09-25** at commit `f0af295`, the head of branch
`explore/curation-templates` (GitHub PR #2, open, not merged into `main`). Each row names a
different kind of evidence: implemented code, human review, app qualification,
and observed student use are separate and are never implied by one another.

| Area | State | Evidence | Next action or blocker |
|---|---|---|---|
| Study | Implemented; maintenance-only | `src/lerni/` CLI; SM-2 tests in the full suite | Optional hardening in [todo.md](./todo.md) |
| Explore lesson foundation (plan PR-02) | Implemented, on `main` at `7f7fc0b` | `src/lerni/explore/`; `tests/explore/` pass in the 2026-09-25 run | Integrate into the M3 app slice |
| Chain-1 acceleration lesson | Draft, zero attestations | `review.status = "draft"` in `chain_1_acceleration.toml`; the child catalog refuses it | Optional: needed only if this lesson is chosen for the M3 app slice ([runbook](../plans/runbooks/chain-1-source-review.md)) |
| Educator authoring (`educator-paths-v1`) | Implemented; committed to `explore/curation-templates` (GitHub PR #2); **not merged** | `curation/`, checker, tests; results in the 2026-09-25 entry | Review and merge PR #2; educator usability feedback |
| Product documents | Revised direction adopted (GitHub PR #2, unmerged) | [PRD](./PRD.md), [roadmap](./roadmap.md) | Planning deliverable, not runtime delivery |
| Local app and qualification (M3) | Not implemented | No UI, runtime, or parent-control modules in `src/lerni/explore/` | Reconcile reduced-slice specs, then build |
| First activity review and walkthrough (M2) | Pending | No review or session evidence exists | Educator and parent: choose interest, prepare and review one activity |
| Student app session (M4) | Pending | None | Waits for M3 |
| Conversion and recommendations (M5–M6) | Planned | Specs only | After M4 |

**Next:** merge PR #2 (user); M2 activity preparation and review (educator and
parent); M3 spec reconciliation (developer). The same list, with owners, is at the
top of [todo.md](./todo.md).

Plan work package **PR-02** (`plans/prs/02-lesson-core.md`) is the implemented
lesson core. **GitHub PR #2** is a different thing: the curation-template branch.

---

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
  control, so plan revisions become reviewable history. Reorganized it into
  `prs/` (execution units), `specs/` (technical contracts), and `runbooks/`
  (manual procedures), renamed the master plan from its hash to
  `cursor_master_plan.plan.md`, dropped the repeated `explore_safe_slice_` prefix,
  and added a `plans/README.md` index carrying the spec-to-PR mapping — the two
  numbering schemes do not line up and that was undocumented.
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

*(Superseded by the 2026-09-06 entry below: `src/lerni/explore/` now exists.)*

Commits were made on branch `explore/pr-01-documentation` at the user's explicit
request. The implementation plans otherwise assume no commits are made without
that authorization.

### Next

- Lesson domain, canonical serialization, and the strict TOML catalog
- Reviewed Chain-1 acceleration content, with real source retrieval dates and
  human review attestations — not fabricated to make checks pass
- Deterministic state engine

---

## 2026-09-06 (Explore PR-02 — Lesson Core)

### Done

- Implemented the Explore lesson domain: immutable lesson, source, fact, step,
  check, and review types with constructor invariants that fail closed on an
  invalid enum, ID, version, index, hash, or review scope.
- Implemented the strict canonical-JSON encoder that gives a lesson payload its
  identity. The payload hash changes for a runtime, grounding, or asset change and
  does not change for review-only metadata.
- Implemented catalog loading over `importlib.resources`: exact schema rejection,
  index and asset hash verification, size limits enforced before an unbounded
  decode or render, and child-catalog filtering that excludes draft content.
- Implemented the deterministic state engine — intro, teach, check, progressive
  hint, correct completion, and revealed completion. No random branch exists.
  Public snapshots omit answer keys and internal review or source detail.
  Tutor-like text produces no engine event.
- Added draft Chain-1 acceleration content and a project-authored accessible SVG,
  packaged as resources. The content teaches that a 0–60 result is elapsed time
  and that average acceleration is velocity change over time; it avoids
  instantaneous acceleration and mutable ranking claims.
- Verified both distributions: wheel and source distribution carry the exact
  indexed bytes in clean installs.
- Rewrote `plans/human-track.md` and `plans/runbooks/chain-1-source-review.md` for
  the people who actually have to use them — educators and parents, not developers.
- Study is untouched: no change to its models, database, SM-2, or commands.

### Files Created

- `src/lerni/explore/__init__.py`, `domain.py`, `canonical.py`, `catalog.py`,
  `engine.py`
- `src/lerni/explore/lessons/__init__.py`, `lesson_index.toml`,
  `chain_1_acceleration.toml`, `assets/chain_1_acceleration.svg`
- `tests/explore/` — `conftest.py`, `test_domain.py`, `test_canonical.py`,
  `test_catalog.py`, `test_chain_1_content.py`, `test_engine.py`,
  `test_distribution.py`

### Testing

```
$ .venv/bin/python -m pytest -q
148 passed, 2 xfailed in 12.10s
```

### Status

**The Chain-1 lesson is `status = "draft"` and carries zero attestations.** The
child catalog refuses to load it. Leaving draft requires four real human reviews —
`science`, `child_content`, `visual_accessibility`, `parent_approval` — each
recorded with a role and date and pinning the same recomputed payload hash. No
agent may write one (Standing Rule 3). Nothing here has been reviewed, and no
child-facing session is possible before the PR-08 pilot gate.

The draft status blocks child-facing content. It does not block PR-03, which uses
synthetic fixtures only, so the human review gate and the next code unit can
proceed in parallel.

### Next

- [PR-03 — Runtime profile and capability process boundary](../plans/prs/03-runtime-boundary.md):
  strict provider-neutral profile parsing, private path derivation and process
  lock, `env:VAR` credential references, bounded helper-subprocess IPC, and
  readiness primitives.
- In parallel, the human review gate: educator checks the science against the
  NASA source, parents make the age-fit, picture, and permission calls.
- PR-03's manual prerequisites are the operator's: an absolute private runtime
  root outside the repository, a qualified helper Python, and a fallback-only
  versus plugin decision. No account or credential is needed.

*(Superseded 2026-09-25: sequence now follows roadmap milestones M1–M6. PR-03
work is scoped to the subset the M3 authored app slice needs.)*

## 2026-09-25 (M1 — Educator Path Authoring and Product-Document Adoption)

**Baseline:** local checkout `54acca4d5fab1098059e972faec3029dd27aa26c` on
`explore/curation-templates` — the head of GitHub PR #2, whose base is `main` at
`7f7fc0b`. Clean working tree before this work. Baseline full suite:
`148 passed, 2 xfailed`. No remote was fetched for this entry.

That branch already held two earlier commits with no log entry of their own:
`76ee190` (2026-09-06) added the legacy v1 curation templates and the Chain-1
draft example bundle, and `54acca4` (2026-09-07) corrected two stale CLAUDE.md
claims. This entry's work was committed as `f0af295` and pushed to update PR #2.

**Committed to `explore/curation-templates` and pushed to update GitHub PR #2. Not merged into `main`.**

### Decisions

- Adopted the revised product direction: educator curation runs alongside
  development; a genuinely reviewed educator-led walkthrough comes before any app
  session; the first app slice is authored text/choices/visuals/hints with parent
  Start/Stop/Reset and no AI, speech, accounts, or persistence.
- New authoring contract `educator-paths-v1` (six tables: nodes, relationships,
  connections, paths, path steps, sources) is separate from, and not
  import-compatible with, the legacy v1 delivery schema or the runtime lesson
  TOML. The adapter is later work (M5).
- Kept the legacy `curation/templates/v1/` headers intact; corrected their
  instructions instead of rewriting their schema.

### Done

- `educator-paths-v1` contract: `curation/schemas/educator-paths-v1.json` (column
  inventory the checker reads) and `plans/specs/08c-educator-path-authoring.md`
  (field meanings, relationship semantics, path continuity, status/readiness,
  serialization, privacy separation).
- Blank header-only templates, `LISTS.csv`, and an educator how-to in
  `curation/templates/educator-paths-v1/`; single entry point `curation/README.md`.
- Draft example bundle `curation/examples/educator-paths-v1-draft/`: 30 nodes,
  35 relationships, 26 connections, 6 paths, 24 path steps, 10 sources, extracted
  (author-entered columns only) from the supplied educator workbook with a
  standard-library XLSX reader. All 121 curriculum records are `draft` with blank
  review fields. Demonstrates two routes from `n-music`, shared `c-012` across
  music and cooking, the building revisit of `n-length`, multiple incoming
  connections, and off-path branches. First steps have fuller activities; later
  steps are deliberate outlines.
- Offline drafting checker `scripts/validate_curation_templates.py` (standard
  library, read-only; exit 0/1/2; plain text and `--json`) with 49 tests in
  `tests/test_curation_templates.py`.
- Legacy corrections: `curation/templates/v1/README.md`, `README.csv`, and
  `EDUCATOR_TODO.csv` no longer promise a clean import, name the six missing
  delivery tables, point the four Chain-1 sign-offs at the TOML
  `review.attestations` procedure, and route learner observations to a private
  log. The Chain-1 example INTERESTS note now says not to fill its observation
  fields. Task verdicts, dates, and both `REVIEWS.csv` files remain blank.
- Adopted `docs/PRD.md` and `docs/roadmap.md` from the revised drafts, with links
  rewritten to repository paths; preserved Study detail (roadmap Appendix A) and
  explicit safety limitations. Added the current-state table above.
- Reconciled `plans/README.md`, the master plan (revision section, educator track,
  readiness table, next developer unit, dependency graph), `plans/human-track.md`
  (immediate educator steps and a non-personal walkthrough section),
  `plans/prs/09-curation-csv.md` (drafting checker vs. future strict importer,
  new mapping prerequisite), status notes in spec 08 and the data-priming
  runbook, and the directly conflicting lines in `README.md`, `CLAUDE.md`,
  `docs/spec.md`, and `docs/todo.md`.
- Not touched: `src/`, the packaged lesson TOML and its review state, the asset,
  Study, and the supplied planning originals (hashes match their manifest).

### Testing

```
$ .venv/bin/python scripts/validate_curation_templates.py --templates curation/templates/educator-paths-v1
Result: structurally valid - 0 error(s), 0 warning(s), 0 drafting note(s).   (exit 0)
$ .venv/bin/python scripts/validate_curation_templates.py --bundle curation/examples/educator-paths-v1-draft
Result: structurally valid - 0 error(s), 9 warning(s), 54 drafting note(s).  (exit 0)
$ .venv/bin/python -m pytest tests/test_curation_templates.py -q
49 passed in 0.24s
$ .venv/bin/python -m ruff check scripts/validate_curation_templates.py tests/test_curation_templates.py
All checks passed!
$ .venv/bin/python -m pytest -q
197 passed, 2 xfailed in 11.98s
$ git diff --check
(clean)
```

The 9 warnings are records with no sources yet (three off-path connections and
all six paths). The 54 drafting notes are unfinished activity fields on the 18
outline steps. A relative-link check over the 20 changed or new Markdown files
found 183 links and 0 broken.

**Not performed:** no spreadsheet application was opened — CSVs were checked by
parsing and Markdown by reading, not by rendering in a spreadsheet or browser. No
human review, no walkthrough, and no student session occurred; none is implied.

### Status

Structural validity only. No curriculum record is reviewed, the Chain-1 lesson
is still draft with zero attestations, there is no app, and no student has used
anything.

### Next

- **Educator and parent (M2):** choose a fitting interest and goal, sketch three
  to five activities, prepare and genuinely review the first, optionally run a
  short walkthrough, keep observations private, revise one thing.
- **Developer (M3):** reconcile the PR-03/PR-06/PR-08 specifications for the
  reduced authored slice and write its acceptance checks, then build it.
- **User:** review and merge GitHub PR #2.
