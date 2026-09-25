# Educator Path Authoring — `educator-paths-v1`

## Status and scope

**Implemented as a drafting contract only.** This spec defines six CSV tables an
educator uses to outline reusable learning paths while the app is still being
built, plus the offline checker that catches broken drafts. It adds no importer,
no database, no publication step, and no change to the installed lesson format.

| Artifact | Location |
|---|---|
| Machine-readable column inventory | [`curation/schemas/educator-paths-v1.json`](../../curation/schemas/educator-paths-v1.json) |
| Blank templates and educator how-to | [`curation/templates/educator-paths-v1/`](../../curation/templates/educator-paths-v1/README.md) |
| Six draft example paths | [`curation/examples/educator-paths-v1-draft/`](../../curation/examples/educator-paths-v1-draft/README.md) |
| Offline checker | [`scripts/validate_curation_templates.py`](../../scripts/validate_curation_templates.py) |
| Tests | [`tests/test_curation_templates.py`](../../tests/test_curation_templates.py) |

This contract is **not** import-compatible with the older delivery-oriented
schema in [`08-graph-recommendations.md`](./08-graph-recommendations.md) (the
`curation/templates/v1/` tables), and it is not the runtime lesson TOML read by
`src/lerni/explore/catalog.py`. Getting an authored activity into the app needs a
deliberate semantic mapping — renaming columns is not enough. That adapter is
later work (roadmap M5); until then the handoff from a path step to a packaged
lesson is manual.

## The unit of authoring

Three questions stay separate:

- **What is this idea?** — a **node** (reusable concept).
- **How does it relate to another idea?** — a **relationship** (subject claim, no order).
- **Why might a learner explore that idea next?** — a **connection** (directional teaching move).

A **path** selects connections and orders them as **path steps**. Semantic
relationships never set lesson order (Standing Rule 4). A node is never
permanently an "interest", "bridge", or "fundamental" — those are roles it plays
inside a particular path.

A path step will later map to one short lesson with its own understanding check.
It does not correspond one-to-one with the engine's internal presentation steps.
Keep `path_id` and `path_step_id` in a separate future mapping record; this
contract adds no field to the runtime lesson format.

## Tables

Columns are listed in exact export order. Only these author-entered columns are
part of the contract; workbook helper columns (`row_check`, `path_position_key`,
`expected_from_node_id`, `source_ref_1` … `source_ref_8`) are excluded. A future
importer must select these named columns explicitly and never ingest every
visible spreadsheet column.

"Required" means required for a structurally complete record. Optional teaching
fields may stay blank while drafting.

### NODES.csv

```csv
node_id,label,definition,aliases,subject_tags,scope_notes,source_ids,status,reviewer_role,review_date,educator_notes
```

One reusable topic or concept. Required: `node_id`, `label`, `definition`,
`status`.

| Field | Meaning |
|---|---|
| `node_id` | Stable ID, e.g. `n-fractions`. Reuse it across paths; changing the label does not change it. |
| `label` | Short human-readable name. |
| `definition` | Adult-facing statement of what the node means. Never a learner observation. |
| `aliases` | Alternative labels, `\|`-separated. For search; not distinct concepts. |
| `subject_tags` | Broad searchable tags, `\|`-separated. They do not restrict where a node is used. |
| `scope_notes` | Boundaries, assumptions, or exclusions that prevent over-broad reading. |
| `source_ids` | `\|`-separated Sources IDs. |
| `status`, `reviewer_role`, `review_date` | See [Status and review](#status-and-review). |
| `educator_notes` | Curriculum-level context or open questions. No student-specific observations. |

### RELATIONSHIPS.csv

```csv
relationship_id,from_node_id,relationship_type,to_node_id,rationale,source_ids,status,reviewer_role,review_date,educator_notes
```

One subject relationship. Required: the first five fields and `status`. Both
endpoints reference Nodes. The rationale says what the claim means in this
context — not a generic "these are related".

| Type | Direction and meaning | Example | Common mistake |
|---|---|---|---|
| `is_a` | From is a narrower kind of To. | Average speed → rate | Reading taxonomy as "teach this first". |
| `part_of` | From is a component of To. | Plant parts → plants | Confusing a component with a subtype. |
| `example_of` | From illustrates or instantiates To. | Steady beat → repeating pattern | Treating every related idea as an example. |
| `uses` | From uses To in the stated context. | Perimeter → length | Claiming every comparison must be numerical. |
| `explains` | Understanding From helps account for To. | Equal parts → fractions | Presenting a speculative link as a proven cause. |
| `related_to` | Symmetric association justified by the rationale. | Rhythm ↔ steady beat | Omitting why the association is useful. |

These types are never lesson order. `related_to` has no direction, so a reversed
copy is a duplicate. All other types are directional. Different types on the same
endpoints are allowed when each claim is justified.

### CONNECTIONS.csv

```csv
connection_id,from_node_id,to_node_id,learning_reason,readiness_guidance,illustrative_prompt,source_ids,status,reviewer_role,review_date,educator_notes
```

One suggested teaching transition. Required: the first four fields and `status`.

- `learning_reason` — why moving from the source idea toward the target could help.
- `readiness_guidance` — what an adult should check before offering the move. Educator guidance, not a stored learner score.
- `illustrative_prompt` — optional generic opener. A path step's own reviewed wording replaces it.

Connections are directional; teaching in reverse needs a separately authored
connection. Two connections may join the same nodes when they are different
teaching moves with different reasons. Reuse a connection when its meaning is
unchanged. A connection that no path uses yet is valid — it is not an executable
lesson.

### PATHS.csv

```csv
path_id,title,entry_node_id,learning_goal,intended_audience,starting_knowledge,source_ids,status,reviewer_role,review_date,educator_notes
```

One educator-curated route. Required: the first four fields and `status`. The
entry node is an available starting topic, not a record of any student's
preference. `intended_audience` and `starting_knowledge` stay generalized — no
child name or personal profile. Two routes from one interest are two Paths
records with the same `entry_node_id`; there is no branching syntax inside a
path.

### PATH_STEPS.csv

```csv
path_step_id,path_id,sequence,target_node_id,connection_id,step_goal,opening_prompt,activity,understanding_check,expected_observation,materials,content_revision,source_ids,status,reviewer_role,review_date,educator_notes
```

One activity occurrence in a path. Required for a complete sketch: the first six
fields and `status`.

**Order.** `sequence` alone determines order: a positive integer, starting at 1,
unique and contiguous within each path. Sorting rows must not change a path. The
visible suffix of an ID such as `p-building-s04` does not control order.

**Continuity.** Group by `path_id`, sort numerically by `sequence`, then:

- step 1's connection starts at the path's `entry_node_id`;
- every later step's connection starts at the previous step's `target_node_id`;
- every step's connection ends at its own `target_node_id`.

**Revisits.** A target may repeat later in the same path with a distinct
`path_step_id` and a new goal (length → perimeter → area → length is valid).

**Activity fields** — optional while outlining, all required before the selected
activity is tried with a student, and then only after a real review:

| Field | Meaning |
|---|---|
| `opening_prompt` | Exact proposed first question or invitation. |
| `activity` | What the educator and student will do. |
| `understanding_check` | Question, choice, or demonstration that probes `step_goal`. |
| `expected_observation` | What would support the intended understanding, and what would be insufficient. An expectation — **never** an observed result. |
| `materials` | Items and reviewed media needed. `none` means none needed; blank means undecided. |
| `content_revision` | Positive integer; increment it whenever activity wording changes substantively. |

### SOURCES.csv

```csv
source_id,title,citation,url,source_notes
```

One reusable reference. Required: `source_id`, `title`, `citation`. `url` is
optional because offline references are legitimate. `source_notes` explains
relevance, limitations, and reuse. Sources has no status column: listing a
reference is not approving a claim. Never invent authors, dates, or retrieval
details.

## Shared rules

1. **IDs** match `[a-z][a-z0-9-]{0,79}`. Use prefixes `n-`, `r-`, `c-`, `p-`, `s-`.
   IDs survive sorting and relabeling, are unique within their table, never come
   from row numbers or formulas, and a retired ID is never reused for a new meaning.
2. **Lists** (`source_ids`, `aliases`, `subject_tags`) use `|` between items, with
   no empty items, no duplicates, and no spaces next to the separator. A literal
   `|` cannot appear inside an item. Every `source_ids` item must resolve to
   Sources. An empty source list is allowed for a draft but is not evidence for
   publication.
3. **Status** on the five curriculum tables is exactly `draft`, `reviewed`,
   `needs_revision`, or `retired`.
4. **Integers** (`sequence`, `content_revision`) are decimal digit strings in CSV;
   the workbook stores numbers.
5. **Dates** (`review_date`) are ISO `YYYY-MM-DD` real calendar dates in CSV; the
   workbook stores real date values.
6. **Self-links** in Relationships or Connections are invalid. A revisit happens
   after another node, as a new path step.
7. **No global acyclic rule.** Association cycles and looping learning routes are
   allowed. A cycle inside `is_a` or `part_of` is flagged for educator review.
8. **Formula-looking text.** Text that begins with `=`, `+`, `-`, or `@` (after
   Unicode NFKC normalization and ignoring leading whitespace and invisible
   control/format characters) is flagged so it is kept literal when opened in a
   spreadsheet. The drafting checker never evaluates or changes it. The stricter
   production importer policy in spec 08 is separate.
9. **Privacy.** Keep child identity, actual interests, observations, engagement
   scores, progress, transcripts, and session dates out of these tables. "Music"
   as a starting topic is curriculum; "this student enjoyed music" is a private
   observation and belongs in a separate learner record.

## Status and review

| Status | Meaning | Next action |
|---|---|---|
| `draft` | Proposed curriculum; no review claimed. | Author, source, or prepare as needed. |
| `reviewed` | A real person reviewed this record. | Recheck linked records and the exact intended use. |
| `needs_revision` | Previously considered content needs changes. | Revise, clear stale review fields, get a fresh review. |
| `retired` | Kept for identity and history; not for new use. | Redirect new paths explicitly. |

`reviewed` requires `reviewer_role` (`educator`, `parent`, or `subject_expert`)
and `review_date`. If either is supplied, both are required. Nothing — no
script, checker, or agent — fills these in; they are entered by the person who
did the review, after it happened. Shipped examples leave both blank.

**A `reviewed` row is curation review only.** It is not application approval.
The installed lesson catalog reads exact-content attestations from the lesson
TOML's `review.attestations` (scopes `science`, `child_content`,
`visual_accessibility`, `parent_approval`, all pinning one
`reviewed_payload_sha256`). Nothing in these CSVs updates that.

## Readiness levels

| Readiness | Needed | What it permits |
|---|---|---|
| Path sketch | Stable IDs, meaningful definitions and transitions, ordered targets and goals, draft status | Adult curriculum authoring and discussion |
| Selected manual activity | All six activity fields, a real educator/parent review, applicable content controls | A short supervised educator-led walkthrough, if the family chooses |
| Application activity | Reviewed packaged content and assets, the app actually built, technical qualification, adult rehearsal, parent authorization | A supervised app session for that enabled slice |
| Recommendations | Exercised handoff, reviewed graph records, separate design and approval controls | Explained suggestions; new graph additions still need review |

Each level is a separate kind of evidence. Structural validity is not review;
review is not app approval; app approval is not a student session.

## CSV serialization

- UTF-8, with or without a leading byte-order mark; LF or CRLF line endings.
- Standard CSV quoting; quoted cells may contain commas, quotes, and newlines.
- A record whose cells are all empty or whitespace is ignored (spreadsheet
  exports often append them). It still counts toward record numbering.
- Record numbers are logical CSV records with the header as record 1, so a
  multi-line cell does not shift later numbers.

CSV does not keep workbook dropdowns, frozen panes, colors, or calculated
warnings. A spreadsheet workbook is an authoring convenience; the CSVs are the
exchange format.

## Offline checker

```bash
python scripts/validate_curation_templates.py --templates curation/templates/educator-paths-v1
python scripts/validate_curation_templates.py --bundle curation/examples/educator-paths-v1-draft
python scripts/validate_curation_templates.py --bundle DIR --json
```

Standard library only. It reads; it never fixes, trims, sorts, renames, writes,
creates a database, fetches a URL, generates a hash or attestation, or activates
anything. It is not the future bounded, byte-canonicalizing publication parser
and its output is not `ValidatedCurationRows`.

Exit status: `0` structurally valid (including incomplete draft activities),
`1` data errors, `2` invalid command line or unreadable input.

| Severity | Codes |
|---|---|
| error | `missing-file`, `malformed-utf8`, `malformed-csv`, `header-missing`, `header-unknown`, `header-duplicate`, `header-order`, `row-width`, `template-has-data`, `required-missing`, `invalid-id`, `duplicate-id`, `unknown-reference`, `list-empty-token`, `list-duplicate-token`, `list-token-whitespace`, `invalid-status`, `invalid-relationship-type`, `invalid-reviewer-role`, `invalid-date`, `invalid-integer`, `reviewed-missing-metadata`, `review-pair-incomplete`, `self-link`, `duplicate-relationship`, `duplicate-sequence`, `sequence-gap`, `first-connection-origin-mismatch`, `connection-origin-mismatch`, `connection-destination-mismatch` |
| warning | `unexpected-file`, `formula-like-text`, `draft-without-sources`, `references-retired`, `review-metadata-without-review`, `taxonomy-cycle`, `path-without-steps` |
| info | `activity-field-missing` (per step and field) |

JSON output carries `schema_version`, `mode`, `counts`, `summary`, `issues`
(each with `code`, `severity`, `table`, `record_number`, `record_id`, `field`,
`message`), `activity_completeness`, and a fixed `notice`. Issues sort by table,
record, field, then code. Messages explain the rule and never echo raw cell
text; `record_id` appears only when it is a well-formed ID. Every report ends
by stating that structural checks do not approve content or make anything ready
for a child. There is no "approved" or "safe to test" flag.

## Relationship to the older curation specs

- [`08-graph-recommendations.md`](./08-graph-recommendations.md) and the
  `curation/templates/v1/` tables remain the **legacy delivery-format draft**.
  Its INTERESTS table mixes reusable topics with learner observations, CONCEPTS
  fixes permanent roles (`kind`, `track`), and NUDGES bundles teaching moves with
  hints and reveals. `educator-paths-v1` separates those concerns. Reconciling the
  two is an explicit adapter/spec revision before any production importer is
  built (roadmap M5), not a column rename.
- [`08a-curriculum-persistence.md`](./08a-curriculum-persistence.md) and
  [`08b-recommendation-feedback.md`](./08b-recommendation-feedback.md) are
  unchanged. Their security, approval, and activation requirements still apply
  to any later publication path.

## Future graph growth (documented only)

Not implemented. The intended sequence when a missing concept or connection is
noticed:

1. Identify the need and the originating node or path step.
2. Search existing labels, aliases, definitions, and scope notes.
3. Record a proposal: rationale, origin, references, possible duplicates.
4. The educator accepts, revises, merges, defers, or rejects it.
5. Accepted additions become ordinary records with stable IDs.
6. Any child-facing activity built on them gets its own content review.

Until a proposal workflow exists, note proposals in `educator_notes` or a private
planning backlog. Generalized educational conclusions may shape shared
curriculum; student-specific evidence stays in private learner records.
