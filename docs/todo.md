# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release. When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Open the educator view, read the Guide tab, and make a learning plan: start from the cars or sharks example, then fill in one activity card.
- [ ] Review the car activity's science with the admin (who has the review sheet). It's the activity for the MVP, because it already exists as a draft; your own activity card comes next.

### Later: Release 1 MVP

- [ ] Approve the activity's four checks: science, wording, pictures and accessibility, and OK to use.
- [ ] Log in to the app from your own device as soon as the admin has it running, and say what's confusing, even before there's any content.
- [ ] Rehearse the MVP on the iPad and your own device, including Stop and Reset, then authorize student use.
- [ ] Watch the student try it, keep notes private, and revise one thing.

## Admin

### Now: Release 1 MVP

Build from the [Release 1 plan](../plans/release-1-mvp.md), in this order:

- [ ] The session controller: one shared session in memory, the tap contract, and Stop and Reset winning over taps in flight.
- [ ] The activity on both screens: the student screen (iPad) and the educator view with Start, Stop, Reset, the recap, and draft preview.

### Later: Release 1 MVP

- [ ] Step 6: approvals in the app, with the science review sheet; admin packaging of a saved activity card, then automatic.
- [ ] Record the educator's four approvals in the chosen activity's file.

### Later: Release 2 Remembering

- [ ] Write `plans/release-2-remembering.md`, starting with mapping each activity revision to the concepts it teaches.

### Later: Release 3 Voice

- [ ] Before choosing speech or model services, check each one's data retention for a student's audio and text, and get the educator's agreement.

### Admin tool maintenance

- [ ] Fix outdated test fixtures in `tests/conftest.py`.
- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Release 1 MVP

- [ ] Try the MVP with the educator beside them. They can say no or stop at any time.
