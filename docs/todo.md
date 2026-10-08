# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release. When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Choose an interest and a goal, fill in the plan sheet (3–5 rows) and one activity card, and send them to the admin. How: [curation guide](../curation/README.md).
- [ ] Tell the admin what was confusing about the plan sheet or the card.
- [ ] Review the car activity's science with the [review sheet](../plans/runbooks/chain-1-source-review.md). It is the quickest activity to approve for the MVP.

### Later: Release 1 MVP

- [ ] Approve the activity's four checks: science, wording, pictures and accessibility, and OK to use.
- [ ] Log in to the app from your own device as soon as the admin has it running, and say what's confusing, even before there's any content.
- [ ] Rehearse the MVP on the iPad and your own device, including Stop and Reset, then authorize student use.
- [ ] Watch the student try it, keep notes private, and revise one thing.

## Admin

### Now: Release 1 MVP

Build from the [Release 1 plan](../plans/release-1-mvp.md), in this order:

- [ ] Walking skeleton: `lerni serve` on the home server; the educator logs in with the passcode from their own device; the iPad shows a waiting screen. Check the network boundary: home network only, no share links, analytics off, no outbound requests, nothing written to disk.
- [ ] The catalog lists approved activities, plus drafts for educator-only preview.
- [ ] The session controller: one shared session in memory, the tap contract, and Stop and Reset winning over taps in flight.
- [ ] The activity on both screens: the student screen (iPad) and the educator view with Start, Stop, Reset, the recap, and draft preview.

### Now: docs and tooling

- [ ] Merge [PR #4](https://github.com/torenunez/lerni/pull/4) (the docs reset) after the owner's review.
- [ ] Cut `tests/test_curation_templates.py` from 48 tests to about 15 covering the checker's key behavior.

### Later: Release 1 MVP

- [ ] Turn the educator's plan sheet and activity card into the authoring tables and an activity file; run the checker.
- [ ] Record the educator's four approvals in the chosen activity's file.

### Later: Release 2 Remembering

- [ ] Write `plans/release-2-remembering.md`, starting with mapping each activity revision to the concepts it teaches.

### Admin tool maintenance

- [ ] Fix outdated test fixtures in `tests/conftest.py`.
- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Consolidate the duplicate `get_lerni_dir()`.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Release 1 MVP

- [ ] Try the MVP with the educator beside them. They can say no or stop at any time.
