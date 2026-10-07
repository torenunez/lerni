# To do

The one checklist. Owners in brackets. Milestones and what completes them: [roadmap](roadmap.md). Done work: [history](history.md).

## Now (in parallel)

- [ ] **[educator + parent]** Choose an interest and a goal, sketch 3–5 activities, and prepare the first. How: [curation guide](../curation/README.md).
- [ ] **[educator]** Try the templates in a spreadsheet app; report what is confusing.
- [ ] **[builder]** Update the technical requirements and checks for [Release 1](prd/student.md#release-1-run-a-seeded-activity) before building it.

## Next

- [ ] **[educator + parent]** Review the first activity, try a short walkthrough, keep notes private, revise one thing.
- [ ] **[builder]** Build the local app against test content.
- [ ] **[builder]** Turn the reviewed activity into the app's lesson format.
- [ ] **[reviewers]** Approve that activity's exact wording and pictures.
- [ ] **[builder]** Show Release 1 working in the installed app.
- [ ] **[parent]** Rehearse it as an adult, then authorize student use.

## Tooling

- [ ] **[builder]** Cut `tests/test_curation_templates.py` from 48 tests to about 15 covering the checker's key behavior.

## Admin tool maintenance

- [ ] Fix outdated test fixtures in `tests/conftest.py`.
- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Consolidate the duplicate `get_lerni_dir()`.
- [ ] Add `study --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.
