# PRD: Educator tools

Every task an educator performs: preparing activities, approving them, supervising sessions, and keeping the student safe. What the student experiences is in the [student app PRD](student.md). The admin's terminal work is in the [admin tool PRD](admin.md).

## Outcome

Educators direct a student's learning without code or the terminal, and spend less time on it as the system improves.

## Users

- **Educator:** seeds the first activities, approves what the student sees, keeps the off-limits list, consents to data sharing, authorizes use, supervises sessions from the educator view, and later reviews what the system drafts.

## How educator involvement changes

Educators bootstrap the system, then step back in stages:

1. **Seed.** An educator hand-writes one or two activities, the worked examples of a good activity.
2. **Draft and approve.** The system drafts new activities in the seeded pattern; an educator approves each one before a student sees it.
3. **Guardrails and spot checks.** Once drafting is reliable, educators set limits and sample-check.

Each step needs evidence from the one before. Student app Releases 1–3 are at stage 1, Release 4 is stage 2, and Release 5 is stage 3.

## Constraints

These hold for every release.

- No terminal and no code. Educators work in the authoring spreadsheet and the app's educator view.
- An educator is present for every session and can stop it at any moment.
- The educator writes a list of off-limits topics before the first session and can add to it at any time. Nothing on it is seeded, drafted, or suggested.
- No student identity or private observations go into shared curriculum.
- Before first use, the educator agrees to which outside services receive the student's data, and can withdraw that at any time.

## Release 1: seed, approve, and supervise

Runs alongside student app Release 1.

Before the app: the educator writes one or two activities in the authoring spreadsheet ([curation guide](../../curation/README.md)). The admin checks the files, turns a reviewed activity into the app's format, and records the educators' approvals in it. This is a workflow, not an app feature.

### Story: Educators approve an activity

As an educator, I want to approve the exact wording and pictures, so that the student sees only what we checked.

- WHEN an activity lacks any required approval, including the educator's, THE SYSTEM SHALL not list it for a session.
- WHEN an activity's wording or pictures change THE SYSTEM SHALL treat it as unapproved until educators approve it again.
- WHEN an activity is marked `reviewed` only in the spreadsheet THE SYSTEM SHALL still treat it as unapproved for the app.

The educator's approval is the authorization. The educator gives it only after the admin's technical checks pass and an educator has rehearsed the activity; that order is a workflow step, not something the app enforces.

### Story: Educator starts an activity

As a educator, I want to choose and start an approved activity, so that I decide what the student does.

- WHEN the app opens THE SYSTEM SHALL show the educator view, listing approved activities only.
- WHEN the educator presses Start THE SYSTEM SHALL show the activity's first step to the student.

### Story: Educator stops or resets

As a educator, I want to stop or restart at any moment, so that I stay in control of the session.

- WHEN the educator presses Stop THE SYSTEM SHALL end the interaction at once.
- WHEN the educator presses Reset THE SYSTEM SHALL clear progress and return to the educator view; another activity requires Start.

### Story: Educator sees a recap

As a educator, I want a short summary when the activity ends, so that I can note what worked.

- WHEN the activity ends or is stopped THE SYSTEM SHALL show the educator which choices were picked, which hints were used, and how long it took.
- WHEN the educator leaves the recap or presses Reset THE SYSTEM SHALL discard it; nothing is saved. Educators keep any notes privately, outside the app.

## Release 2: continuity

### Story: Educator links activities to earlier ideas

As an educator, I want to write a short reminder and a recall question for each idea, so that the app can build on what the student explored before.

- WHEN an activity's idea is reached THE SYSTEM SHALL use only the reminder and recall question the educator wrote and approved.

### Story: Educator sees and deletes what the app remembers

As a educator, I want to see and delete the record of my student's progress, so that I control what is kept.

- WHEN the educator opens the progress view THE SYSTEM SHALL show which activities were finished, which ideas were reached, and recall results.
- WHEN the educator deletes the record THE SYSTEM SHALL remove it from Lerni's storage. Copies an outside service keeps follow that service's rules.

## Release 3: voice

### Story: Educator controls the microphone

As a educator, I want to decide when the microphone is on, so that the app listens only when I allow it.

- WHEN a session starts, or the educator presses Stop or Reset, THE SYSTEM SHALL turn the microphone off.
- WHEN the educator turns the microphone on THE SYSTEM SHALL allow push-to-talk for that session only.

## Later

- **Review drafts (stage 2, student app Release 4):** see each activity the system proposes and drafts, then approve it, send it back, or reject it.
- **Set guardrails and spot-check (stage 3, Release 5):** set limits, then sample what the system runs.

## Out of scope

Running the admin tool. Editing app code or lesson files directly.

## Decisions

- 2026-09-25: Educators author paths alongside development instead of after a pilot, because authoring, development, and early observations should inform each other.
- 2026-10-07: Educator involvement steps down in stages: seed, then draft-and-approve, then guardrails and spot checks once drafting is reliable.
- 2026-10-07: Every educator task lives in this PRD; the student app PRD covers only the student. Admin terminal work stays in the admin tool PRD.
- 2026-10-07: The educator keeps an off-limits topic list, set before first use and added to over time.
- 2026-10-07: The educator agrees to the voice setup before the microphone is first used.

## Open questions

- [NEEDS CLARIFICATION] What evidence shows drafting is reliable enough to move from approving each activity to spot checks?
- [NEEDS CLARIFICATION] Whose Claude account powers drafting and conversation: the admin's or the educator's?
- [NEEDS CLARIFICATION] What goes on the starting off-limits list, and where is it kept?
- [NEEDS CLARIFICATION] Do educators review drafts in the educator view or a separate screen?
