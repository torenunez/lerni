# To do

The one checklist. Owners in brackets. Milestones and what completes them: [roadmap](roadmap.md). Done work: [history](history.md).

## Now (in parallel)

- [ ] **[educator]** Choose an interest and a goal, sketch 3–5 activities, and prepare the first. How: [curation guide](../curation/README.md).
- [ ] **[educator]** Try the templates in a spreadsheet app; report what is confusing.
- [ ] **[educator]** Review the car activity's science with the [review sheet](../plans/runbooks/chain-1-source-review.md), the quickest activity to approve for the MVP.
- [ ] **[admin]** Build the MVP from the [Release 1 plan](../plans/release-1-mvp.md), in this order:
  - [ ] The catalog lists approved activities only.
  - [ ] The session controller: one shared session in memory, the tap contract, Stop and Reset winning over taps in flight.
  - [ ] The student screen (iPad) and the educator view (own device, passcode).
  - [ ] Run it on the home server and check the network boundary: home network only, no share links, analytics off, no outbound requests, nothing written to disk.

## Next

- [ ] **[admin]** Record the educator's four approvals in the chosen activity's file.
- [ ] **[educator]** Rehearse the MVP on the iPad and your own device, including Stop and Reset, then authorize student use.
- [ ] **[educator]** Watch the student try the MVP, keep notes private, revise one thing.

## Tooling

- [ ] **[admin]** Merge [PR #4](https://github.com/torenunez/lerni/pull/4) (the docs reset) after the owner's review.

- [ ] **[admin]** Cut `tests/test_curation_templates.py` from 48 tests to about 15 covering the checker's key behavior.

## Admin tool maintenance

- [ ] Fix outdated test fixtures in `tests/conftest.py`.
- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Consolidate the duplicate `get_lerni_dir()`.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.
