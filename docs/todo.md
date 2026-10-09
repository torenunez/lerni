# To do

Open tasks by who does the work. The educator and admin tracks run in parallel: building and troubleshooting the app never waits for content, and content never waits for the app. Within each role, **Now** comes first and later work is grouped by release. When a task is done, delete it; if it changed where things stand, add a dated entry to [progress](progress.md). What completes each release: [roadmap](roadmap.md).

## Educator

### Now: Release 1 MVP

- [ ] Open the educator view, read the Guide tab, and make a learning plan: import your rough notes with Claude, or start from the cars or sharks example, then fill in one activity card.
- [ ] Review the car activity's science with the admin (who has the review sheet). It's the activity for the MVP, because it already exists as a draft; your own activity card comes next.

### Later: Release 1 MVP

- [ ] Approve the activity's four checks: science, wording, pictures and accessibility, and OK to use.
- [ ] Once step 5 lands: sign in from your own device, add the student accounts in the Students tab, and say what's confusing.
- [ ] Rehearse the MVP on the iPad and your own device, including Stop and Reset, then authorize student use.
- [ ] Watch the student try it, keep notes private, and revise one thing.

## Admin

### Now: Release 1 MVP

Build from [specs/03-student-accounts.md](../plans/specs/03-student-accounts.md), one PR each, in this order:

- [ ] Step 5: accounts and one sign-in (one app at `/`, tabs by role, the Students tab, lockout). Update the in-app guide for the Students tab and the two kinds of student. Check on the iPad that Safari saves the password.

### Later: Release 1 MVP

- [ ] Step 6: plan my own (independent students' Learning plans and My account, plan schema v2, Explore freely, self-approval). Make the first real Claude import on the home server, and add the import evals.
- [ ] Step 7: play a card (card activities, one session per student, Learn). Done when you do your own activity end to end on the iPad.
- [ ] Step 8: the supervised path (the educator's Start, Stop, Reset, and recap; the four approvals in the app, including the car activity's).

### Later: Release 2 Remembering

- [ ] Write `plans/release-2-remembering.md`, starting with mapping each activity revision to the concepts it teaches.

### Later: Release 3 Voice

- [ ] Plan the conversation agent with tools (reading the plan, checking the allowlist, giving hints), and grow its evals from the import evals.
- [ ] Before anyone outside the household uses the app: replace the Claude Code adapter with an API-key adapter (`env:ANTHROPIC_API_KEY`).

- [ ] Before choosing speech or model services, check each one's data retention for a student's audio and text, and get the educator's agreement.

### Admin tool maintenance

- [ ] Add database, CLI, and full-workflow tests.
- [ ] Clear ruff lint debt in `src/` (99 findings on 2026-08-23, mostly style).
- [ ] Run mypy and fix type errors.
- [ ] Add `lerni --version`.
- [ ] Check empty-database, invalid-ID, and concurrent-access behavior.

## Student

### Later: Release 1 MVP

- [ ] Independent student (the admin first): once step 7 lands, import your own interests and do an activity end to end; note what's confusing.
- [ ] Supervised student: try the MVP with the educator beside them. They can say no or stop at any time.
