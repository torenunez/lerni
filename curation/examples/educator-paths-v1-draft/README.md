# Draft example paths — `educator-paths-v1`

Six illustrative paths showing how the authoring tables fit together, built around three interests: cars, sharks, and soccer. **Every record is `draft`. Nothing here has been source-checked, educator-approved, or tried with a student.** Review fields are deliberately blank.

| Path | Entry | Ordered targets |
|---|---|---|
| `p-cars` | `n-cars` | distance → elapsed time → average speed → average acceleration |
| `p-cars-ramp` | `n-cars` | fair test → observation → measurement → comparison |
| `p-sharks-speed` | `n-sharks` | distance → elapsed time → average speed → comparison |
| `p-sharks-body` | `n-sharks` | animal body parts → adaptation → habitat → food chain |
| `p-soccer-kick` | `n-soccer` | force → direction → distance → force |
| `p-soccer-field` | `n-soccer` | length → perimeter → area → square unit |

Counts: 26 nodes, 32 relationships, 26 connections, 6 paths, 24 path steps, 5 sources.

## What each example demonstrates

- **Two routes from one interest.** Each interest has two paths that start at the same node (for example, both shark paths start at `n-sharks`, which exists once). They are two Paths rows, not a branch inside one path.
- **Reuse across interests.** Cars and sharks both reach speed through the same nodes and the same teaching connections, `c-002` (distance → elapsed time) and `c-003` (elapsed time → average speed). The node definitions do not change; each path step supplies its own activity (paper roads for cars, a reef map for sharks).
- **A legitimate revisit.** The soccer kick path returns to `n-force` at sequence 4 with its own step ID (`p-soccer-kick-s04`) and a different goal. It is valid.
- **Several ways in.** Distance can be reached from cars, sharks, or direction (`c-001`, `c-005`, `c-013`); comparison from speed or measurement (`c-006`, `c-022`).
- **Graph content outside any path.** `c-023`–`c-026` are useful branches that no path uses yet. They are not executable activities.
- **Outlines, not scripts.** Each path's first step has a fuller draft activity. Later steps are deliberate outlines; the checker reports their missing fields.

Where precision matters the drafts keep distinctions such as elapsed time versus acceleration, and average versus instantaneous quantities. Those distinctions still need a real subject review before any use.

Sources: only references already vetted for motion, measurement, geometry, and fair tests are listed. Shark, soccer, force, and life-science records have no sources yet; the checker warns about them rather than anyone inventing references.

Check it:

```bash
python scripts/validate_curation_templates.py --bundle curation/examples/educator-paths-v1-draft
```

Expected: no errors; warnings for records with no sources yet; drafting notes for unfinished activity fields. That result is structural only.
