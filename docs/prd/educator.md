# PRD: Educator and parent tools

Every task an educator or parent performs: preparing activities, approving them, supervising sessions, and keeping the child safe. What the child experiences is in the [student app PRD](student.md). The admin's terminal work is in the [admin tool PRD](admin.md).

## Outcome

Educators and parents direct a child's learning without code or the terminal, and spend less time on it as the system improves.

## Users

- **Educator:** seeds the first activities, supervises sessions from the supervisor view, and later reviews what the system drafts.
- **Parent:** approves what the child sees, keeps the off-limits list, authorizes use, and can supervise from the same view.

## How adult involvement changes

Adults bootstrap the system, then step back in stages:

1. **Seed.** An educator hand-writes one or two activities, the worked examples of a good activity.
2. **Draft and approve.** The system drafts new activities in the seeded pattern; an adult approves each one before a child sees it.
3. **Guardrails and spot checks.** Once drafting is reliable, adults set limits and sample-check.

Each step needs evidence from the one before. Releases 1 and 2 are at stage 1.

## Constraints

These hold for every release.

- No terminal and no code. Adults work in the authoring spreadsheet and the app's supervisor view.
- An adult is present for every session and can stop it at any moment.
- The parent writes a list of off-limits topics before the first session and can add to it at any time. Nothing on it is seeded, drafted, or suggested.
- No child identity or private observations go into shared curriculum.

## Release 1: seed, approve, and supervise

Runs alongside student app Release 1.

Before the app: the educator writes one or two activities in the authoring spreadsheet ([curation guide](../../curation/README.md)). The admin checks the files, turns a reviewed activity into the app's format, and records the adults' approvals in it. This is a workflow, not an app feature.

### Story: Adults approve an activity

As an educator or parent, I want to approve the exact wording and pictures, so that the child sees only what we checked.

- WHEN an activity lacks any required approval, including the parent's, THE SYSTEM SHALL not list it for a session.
- WHEN an activity's wording or pictures change THE SYSTEM SHALL treat it as unapproved until adults approve it again.
- WHEN an activity is marked `reviewed` only in the spreadsheet THE SYSTEM SHALL still treat it as unapproved for the app.

The parent's approval is the authorization. The parent gives it only after the admin's technical checks pass and an adult has rehearsed the activity; that order is a workflow step, not something the app enforces.

### Story: Supervisor starts an activity

As a supervising adult, I want to choose and start an approved activity, so that I decide what the child does.

- WHEN the app opens THE SYSTEM SHALL show the supervisor view, listing approved activities only.
- WHEN the supervisor presses Start THE SYSTEM SHALL show the activity's first step to the child.

### Story: Supervisor stops or resets

As a supervising adult, I want to stop or restart at any moment, so that I stay in control of the session.

- WHEN the supervisor presses Stop THE SYSTEM SHALL end the interaction at once.
- WHEN the supervisor presses Reset THE SYSTEM SHALL clear progress and return to the supervisor view; another activity requires Start.

### Story: Supervisor sees a recap

As a supervising adult, I want a short summary when the activity ends, so that I can note what worked.

- WHEN the activity ends or is stopped THE SYSTEM SHALL show the supervisor which choices were picked, which hints were used, and how long it took.
- WHEN the supervisor leaves the recap or presses Reset THE SYSTEM SHALL discard it; nothing is saved. Adults keep any notes privately, outside the app.

## Release 2: voice

### Story: Supervisor controls the microphone

As a supervising adult, I want to decide when the microphone is on, so that the app listens only when I allow it.

- WHEN a session starts, or the supervisor presses Stop or Reset, THE SYSTEM SHALL turn the microphone off.
- WHEN the supervisor turns the microphone on THE SYSTEM SHALL allow push-to-talk for that session only.

## Later

- **Review drafts (stage 2):** see each activity the system drafts, then approve it, send it back, or reject it.
- **Set guardrails and spot-check (stage 3):** set limits, then sample what the system runs.
- **Choose from suggestions:** pick the next idea from the system's suggestions.

## Out of scope

Running the admin tool. Editing app code or lesson files directly.

## Decisions

- 2026-09-25: Educators author paths alongside development instead of after a pilot, because authoring, development, and early observations should inform each other.
- 2026-10-07: Adult involvement steps down in stages: seed, then draft-and-approve, then guardrails and spot checks once drafting is reliable.
- 2026-10-07: Every educator and parent task lives in this PRD; the student app PRD covers only the child. Admin terminal work stays in the admin tool PRD.
- 2026-10-07: The parent keeps an off-limits topic list, set before first use and added to over time.
- 2026-10-07: Both parents agree to the voice setup before the microphone is first used.

## Open questions

- [NEEDS CLARIFICATION] What evidence shows drafting is reliable enough to move from approving each activity to spot checks?
- [NEEDS CLARIFICATION] Where would drafting run, given that Releases 1 and 2 make no outbound requests?
- [NEEDS CLARIFICATION] What goes on the starting off-limits list, and where is it kept?
- [NEEDS CLARIFICATION] Do adults review drafts in the supervisor view or a separate screen?
