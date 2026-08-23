# Explore Safe Slice — Documentation Alignment

## Goal

Make the repository describe the product that will actually be built:

- one repository with Study and Explore modes;
- Study Phase 1 preserved and maintenance-only;
- Explore active;
- the first Explore milestone is a deterministic, parent-supervised Gradio lesson;
- runtime AI and speech are replaceable capabilities, not named provider requirements;
- safety controls are prototype guardrails, not a legal or production-safety claim.

This phase changes Markdown only. It must preserve the existing uncommitted AI-skill, iOS, and hook documentation.

## Inputs

Read before editing:

- `README.md`
- `CLAUDE.md`
- `docs/mission.md`
- `docs/PRD.md`
- `docs/roadmap.md`
- `docs/spec.md`
- `docs/todo.md`
- `docs/progress.md`
- the current `git diff` for those files
- the master and subplans in this plan set
- optional historical pivot drafts, when available, as non-normative research only

Do not copy a Desktop draft wholesale. It contains decisions superseded by this plan, including graph-edge-as-turn semantics, Week-1 infrastructure, safety sequencing, persistence, and model/provider assumptions.

## Global language rules

Use these terms consistently:

- **Study**: adult Feynman + spaced-repetition CLI; Phase 1 feature-complete; maintenance-only.
- **Explore**: child interest-to-fundamentals Gradio experience; active development.
- **Tutor capability**: replaceable text-generation interface configured by the operator.
- **Speech-to-text capability**: optional replaceable adapter; typed input remains available.
- **Read-aloud**: browser capability detected at runtime; visible text is authoritative.
- **Reviewed lesson content**: source-backed, human-approved facts and authored fallback text.
- **Lesson sequence**: explicit pedagogical order owned by the application.
- **Concept graph**: future shared curriculum structure; not the Week-1 runtime controller.
- **Prototype guardrails**: deterministic input/output policies plus parent supervision.
- **Local telemetry**: separate Explore SQLite data with sanitized turns, structured events, parent observations, export, deletion, and retention.
- **Curation workbook**: portable parent/educator CSV-backed spreadsheet schema, compatible with Google Sheets, whose exported bundle is validated locally; interests, nudges, concepts, facts, edges, and lesson order remain separate records.

Avoid these claims:

- “one edge equals one tutor turn” as a runtime invariant;
- hop count is an objective or validated measure of difficulty;
- 0–60 elapsed time is itself acceleration;
- Study and Explore already share a working agent runtime;
- a named model or provider is required;
- an external moderation API guarantees safety;
- “child-safe,” “COPPA compliant,” “anonymous,” “PII-free,” or “forensic deletion”;
- all processing remains on-device unless the selected runtime profile proves it;
- audio is never retained outside Lerni’s own schema and verified cleanup boundary;
- public deployment, FastAPI, NetworkX, cloud analytics, or a garage is part of the first milestone.

## Task 1 — Rewrite `docs/mission.md`

Target outline:

1. `# Lerni — Mission`
2. `## Vision`
3. `## Two Modes`
4. `## Core Beliefs`
   - Learning is active.
   - Interest is a scaffold.
   - Simplicity reveals mastery.
   - Forgetting is natural.
   - Privacy and parent control matter.
   - AI serves but does not own curriculum or progression.
5. `## Target Learners`
6. `## Success`
7. `## Non-Goals`
   - Study non-goals.
   - Explore non-goals.

Required content:

- Explain that “one engine” is the intended direction, while the first Explore slice is deliberately isolated behind interfaces.
- Describe hop count as a curriculum-authoring heuristic only.
- State that Explore success is curiosity-driven return plus later recall, not session duration.
- State that a supervising parent controls local retention and can export/delete sessions.
- State that non-family use and public deployment require a separate privacy, safety, and legal review.

Preserve the original Study learning beliefs where they remain true.

Review checks:

- A reader can identify both modes and their status.
- Explore does not weaken Study’s local-default privacy statement.
- No implementation provider or model appears.

## Task 2 — Rewrite `docs/PRD.md`

Target outline:

1. `# Lerni — Product Requirements`
2. `## Product Lines`
3. `## Study`
4. `## Explore`
5. `## Explore Phase-1 User Journey`
6. `## Functional Requirements`
7. `## Safety and Data Requirements`
8. `## Success Signals`
9. `## Deferred Requirements`
10. `## Specification Index`

Required Week-1 journey:

1. Parent opens the localhost app.
2. App confirms runtime capabilities without exposing secrets.
3. Child sees a reviewed acceleration visual and authored hook.
4. Child responds by typing or, when qualified, records a short utterance.
5. Microphone transcription is shown for correction before submission.
6. Input policy runs.
7. A configured tutor capability may phrase a bounded response from current facts.
8. Complete output is grounded and gated before display.
9. App—not the tutor—advances intro, teach, check, hint, and completion states.
10. Browser read-aloud is optional and never replaces visible text.
11. Parent records an observation and can export/delete the session.

Functional acceptance requirements:

- One reviewed Chain-1 lesson loads from packaged data.
- The child can complete it with no tutor, microphone, or read-aloud capability.
- A qualified tutor can enrich wording but cannot advance state.
- A correct answer completes the lesson.
- Incorrect answers produce at most the authored hint sequence, then reveal the answer without punishment.
- A blocked input never reaches the tutor.
- A rejected output never reaches display or telemetry.
- Audio is not part of the Explore database or export schema.
- Parent can delete a session and all dependent rows.
- Parent/educator can describe an interest and reviewed educational nudge without entering a child name, transcript, or audio.
- Only approved workbook rows can prime the local curriculum graph or compile child-facing lesson content.

Deferred requirements:

- garage/mastery loop;
- spaced resurfacing;
- adaptive, generated, or automatically child-visible recommendations beyond the bounded parent-only Phase-2 candidate rules;
- parent curation portal;
- automatic Google Sheets synchronization;
- child image uploads;
- Spanish content;
- public or non-family access;
- deployment framework and hosting choice.

## Task 3 — Merge `docs/roadmap.md`

Do not replace the current file. Its uncommitted Study success criteria, AI Skills, and iOS sections must survive.

Required structure:

1. Add a short status preamble.
2. Wrap the existing phases under `# Study Track`.
3. Add `Status: maintenance-only` to Study Phase 2–5 goals.
4. Keep Phase-1 open hardening items visible.
5. Add `# Explore Track`.

Explore roadmap:

### Explore Phase 1A — Deterministic safe slice

- environment qualification;
- docs alignment;
- immutable lesson model;
- strict TOML catalog;
- corrected, reviewed acceleration lesson;
- deterministic state machine;
- app-owned input/output and grounding policies;
- local sanitized telemetry with parent controls;
- Gradio localhost UI;
- curated visual;
- browser read-aloud;
- typed input fallback;
- tutor capability contract and one qualified runtime adapter before the LLM pilot.

### Explore Phase 1B — Push-to-talk

- speech-to-text protocol;
- bounded microphone recording;
- selected adapter qualification;
- editable transcript before submission;
- guaranteed application cleanup attempt;
- no audio schema/export fields;
- text fallback under every failure.

### Explore Phase 2 — Content and parent curation

- Chains 2–4 fact sheets;
- portable spreadsheet workbook, optionally edited in Google Sheets, for interests, concepts, sources, facts, nudges, edges, lessons, lesson steps, and aggregate observations;
- manual CSV export with manifest/hash validation;
- dry-run, staged import, and explicit activation;
- early local curriculum graph whose domain edges remain separate from lesson sequence;
- content approval workflow;
- parent curation interface;
- explicit lesson-to-concept mapping;
- schema decision for curriculum metadata;
- deterministic next-lesson rules;
- transparent parent-only graph-backed recommendation candidates;
- separate parent state for scope, readiness, decisions, and assignments;
- garage only if the first pilot supports the need.

### Explore Phase 3 — Retention and recommendation

- delayed recall checks;
- careful integration with spaced scheduling if semantics fit;
- evidence-informed/adaptive recommendation experiments only after the bounded Phase-2 rules are evaluated;
- parent approval before child visibility;
- bilingual and richer speech work;
- privacy/legal review before broader access.

## Task 4 — Rewrite and reorder `docs/todo.md`

Place `## Explore Phase 1 — Active` first.

Under `## Explore Phase 1 — Active`, mirror the first-slice execution order:

1. Environment qualification.
2. Documentation.
3. Lesson domain.
4. Catalog and approved content.
5. State engine.
6. Safety/grounding.
7. Tutor capability.
8. Telemetry.
9. Gradio visual/read-aloud.
10. Push-to-talk.
11. Verification.
12. Parent-supervised pilot.

Then add `## Explore Phase 2 — Parent Curation and Bounded Recommendations`:

13. Curation workbook and dry-run CSV importer.
14. Early approved graph priming and transparent parent recommendation candidates.

Move current Study work under explicit parked headings without deleting:

- `Study — Optional hardening`.
- `Study Phase 2 — Parked AI Agents and Skills`.
- `Study Phase 3–5 — Parked`.

Retain every existing AI Skill Module and iOS checklist item.

Do not mark implementation items complete during this documentation-only phase.

## Task 5 — Add Explore contracts to `docs/spec.md`

Preserve the existing Study specification, uncommitted AI Skills architecture, and iOS architecture.

Add:

### `# Product Modes`

- Current status and reuse boundary.

### `# Explore Architecture`

- package structure;
- runtime profile;
- immutable lesson content;
- catalog validation;
- deterministic state engine;
- capability interfaces;
- app-owned safety;
- local telemetry;
- Gradio presentation;
- speech lifecycle.

### `## Lesson Contract`

Document:

- schema version;
- content version;
- review metadata;
- explicit sequence;
- authored steps;
- retrieval check and hints;
- grounding facts and sources;
- numeric claims;
- local curated asset reference.

### `## Tutor Contract`

Document only provider-neutral input/output:

- receives sanitized learner text, current snapshot, and reviewed facts;
- returns bounded draft text or typed failure;
- cannot read credentials from lesson data;
- cannot determine correctness or progression;
- complete output is gated before display.

### `## Safety Contract`

Document:

- deterministic policy precedence;
- best-effort redaction;
- grounding/citation/numeric checks;
- authored fallback;
- optional external checks may only tighten;
- residual limitations.

### `## Explore Telemetry Contract`

Document:

- separate database;
- sanitized accepted turns or fixed withholding markers;
- structured events only;
- parent observations;
- retention;
- export;
- transactional deletion;
- excluded data.

### `## Multimodal Contract`

Document:

- reviewed visual assets;
- visible text first;
- optional browser read-aloud;
- optional microphone transcription;
- transcript preview/edit;
- recording cleanup attempt;
- no child image upload.

### `## Parent Curation and Curriculum Graph Contract`

Document:

- workbook tabs and privacy exclusions;
- portable CSV bundle and manifest hashes;
- strict row and cross-tab validation;
- approved-only activation;
- separate content database and import batches;
- distinct Interest, Concept, Fact, Nudge, Edge, Lesson, and LessonStep records;
- graph relationship semantics;
- explicit lesson sequence independent of graph edges;
- immutable lesson-version curriculum bindings used by telemetry;
- separate parent-state database for scope, readiness, recommendation decisions, and assignments;
- parent-attested prerequisite readiness;
- deterministic, explainable recommendation candidates;
- mandatory parent approval before a recommendation becomes child-visible;
- aggregate observation export without transcripts or audio;
- optional future sheet-source adapters, with no Google API requirement for the first version.

Update the existing Tech Stack and Open Questions to describe configurable adapters and deferred choices without naming a required model/provider.

## Task 6 — Update `README.md`

Keep it short and execution-oriented.

Target outline:

1. Product summary.
2. Modes.
3. Current status.
4. Study quick start.
5. Explore development status and local-only warning.
6. Installation profiles:
   - core Study;
   - Explore UI;
   - environment-specific optional adapters.
7. Testing.
8. Documentation links.

Do not advertise the child prototype as production-ready or generally available.

## Task 7 — Update `CLAUDE.md`

This repository guidance file may mention its own tooling context, but the implementation instructions inside it must remain portable.

Required changes:

- two-mode overview;
- Explore active / Study maintenance-only;
- actual package tree rather than nonexistent implemented modules;
- planned Explore modules from the detailed plans;
- build/test commands using ordinary Python tooling;
- rule that runtime adapters are selected by qualification, never hardcoded;
- rule that tests use deterministic fakes and no live model/service;
- rule that child-facing content requires human approval;
- rule that lesson order is separate from `ConceptEdge`;
- rule that no commit is made unless explicitly requested.

Preserve:

- `.claude/` hook documentation;
- current AI Skills content, marked parked;
- Study CLI reference;
- current design principles that remain valid.

## Task 8 — Append `docs/progress.md`

Do not rewrite history.

Append one entry using the actual implementation date. Record:

- pivot decision;
- Study maintenance status;
- selected first-slice boundary;
- science correction;
- lesson/graph separation;
- local telemetry decision;
- read-aloud then push-to-talk sequence;
- provider/model-neutral capability architecture;
- documentation status;
- no commits.

Do not claim code exists until it does.

## Cross-document consistency review

Review all eight files for these assertions:

- Explore is active.
- Study remains present and maintenance-only.
- Study Phases 2–5 are parked, not deleted.
- The first lesson is explicit application data.
- The graph is future curriculum structure, not current state control.
- Tutor, STT, and harm-gate services are capabilities selected by runtime qualification; generated tutor use requires a qualified harm gate.
- No required model/provider is named.
- Parent supervision and prototype limitations are visible.
- Telemetry is local and data-minimized, but not described as anonymous.
- Read-aloud does not imply audio input.
- Push-to-talk does not imply audio retention.
- Workbook content does not imply automatic approval or direct runtime access to Google Sheets.
- Graph edges do not imply lesson order.
- Public deployment is deferred.

## Validation

Inspect the full diff:

```bash
git diff -- README.md CLAUDE.md docs/mission.md docs/PRD.md docs/roadmap.md docs/spec.md docs/todo.md docs/progress.md
```

Confirm preserved parked work:

```bash
rg -n "Feynman Coach|Spaced Repetition Analyzer|Knowledge Graph Builder|Study Session Generator|iOS Companion|SwiftUI|SQLite\\.swift|\\.claude/" \
  CLAUDE.md docs/roadmap.md docs/spec.md docs/todo.md
```

Find model/provider assumptions that require manual review:

```bash
rg -n "required model|required provider|hardcoded model|hardcoded provider|api[_ -]?key|provider =" \
  README.md docs/mission.md docs/PRD.md docs/roadmap.md docs/spec.md docs/todo.md docs/progress.md
```

Find superseded requirements:

```bash
rg -n "one edge = one tutor turn|FastAPI|NetworkX|Render|COPPA compliant|child-safe|that number has a name" \
  README.md CLAUDE.md docs/mission.md docs/PRD.md docs/roadmap.md docs/spec.md docs/todo.md docs/progress.md
```

Any match must be either removed, clearly marked deferred/historical, or explained as a rejected prior proposal.

Finally:

```bash
git status --short
```

Expected:

- only intended Markdown files plus pre-existing user files are modified/untracked;
- no commit exists;
- no non-Markdown source file changed during this phase.
