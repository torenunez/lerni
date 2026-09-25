# Draft example paths — `educator-paths-v1`

Six illustrative paths showing how the authoring tables fit together. **Every
record is `draft`. Nothing here has been source-checked, educator-approved, or
tried with a student.** Review fields are deliberately blank.

| Path | Entry | Ordered targets |
|---|---|---|
| `p-cars` | `n-cars` | distance → elapsed time → average speed → average acceleration |
| `p-music-pulse` | `n-music` | steady beat → tempo → rate → elapsed time |
| `p-music-pattern` | `n-music` | rhythm → repeating pattern → equal parts → fractions |
| `p-cooking` | `n-cooking` | measurement → equal parts → fractions → equivalent fractions |
| `p-plants` | `n-plants` | plant parts → plant needs → fair test → observation |
| `p-building` | `n-building` | length → perimeter → area → length |

Counts: 30 nodes, 35 relationships, 26 connections, 6 paths, 24 path steps,
10 sources.

## What each example demonstrates

- **Two routes from one interest.** Both music paths start at the same
  `n-music` node, which exists once. They are two Paths rows, not a branch
  inside one path.
- **Reuse across subjects.** Music and cooking both reach `n-equal-parts` and
  `n-fractions`, and both use the same connection `c-012` (equal parts →
  fractions). The node definitions do not change; each path step supplies its own
  activity (a timing strip in music, a pretend recipe diagram in cooking).
- **A legitimate revisit.** The building path returns to `n-length` at sequence 4
  with its own step ID (`p-building-s04`) and a different goal. It is valid.
- **Several ways in.** Fractions can be reached from equal parts (`c-012`) or area
  (`c-026`); measurement from cooking, rate, or observation (`c-013`, `c-024`,
  `c-025`).
- **Graph content outside any path.** `c-024`–`c-026` are useful branches that no
  path uses yet. They are not executable lessons.
- **Outlines, not scripts.** Each path's first step has a fuller draft activity.
  Later steps are deliberate outlines; the checker reports their missing fields.

Where precision matters the drafts keep distinctions such as elapsed time versus
acceleration, and average versus instantaneous quantities. Those distinctions
still need a real subject review before any use.

Check it:

```bash
python scripts/validate_curation_templates.py --bundle curation/examples/educator-paths-v1-draft
```

Expected: no errors; warnings for records with no sources yet; drafting notes for
unfinished activity fields. That result is structural only.

These records were extracted, author-entered columns only, from a draft
educator workbook containing generalized curriculum examples. No workbook
metadata, review values, or learner information was copied.
