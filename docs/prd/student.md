# PRD: Supervised student app

The app a child uses with an adult supervising (`explore` in the code). The builder's terminal tool has its own [admin PRD](admin.md). Each release has its own section; the [roadmap](../roadmap.md) says which one is current. When a spec in `plans/` disagrees with this file, this file wins until the spec is updated.

## Outcome

A child explores ideas they care about through short activities, and shows they understand them in their own words, with less adult effort over time.

## Users

- **Child, about 7–9, in one family:** explores ideas that start from their own interests. The goal is a conversation by voice.
- **Educator:** seeds the first activities, supervises sessions from the app's supervisor view, and later reviews what the system drafts.
- **Parent:** approves what the child sees, authorizes use, and can supervise from the same view.

Educators and parents never need the terminal. The builder runs the [admin tool](admin.md).

## How adult involvement changes

Humans bootstrap the system, then step back in stages:

1. **Seed.** An educator hand-writes one or two activities. They are the worked examples of what a good activity looks like.
2. **Draft and approve.** The system drafts new activities in the seeded pattern. An adult approves each one before a child sees it.
3. **Guardrails and spot checks.** Once drafting is reliable, adults set limits and sample-check, and the system runs within those limits.

Each step needs evidence from the one before. Releases 1 and 2 are at stage 1.

## Constraints

These hold for every release.

- An adult can always stop a session from the supervisor view.
- Educators and parents work only through the app and the authoring spreadsheet, never the terminal.
- Some topics are off limits. The parent writes a list of topics never to explore with the child before the first session, and can add to it at any time. Nothing on it is seeded, drafted, or suggested. This applies to Explore only, not Study.
- No child identity or private observations go into shared curriculum.
- The admin tool's commands and data keep working.
- These are prototype guardrails, not production moderation. One family; no public use.

## Release 1: run a seeded activity

Built after the [discovery round](../roadmap.md#m2--discovery-round). The app runs one or two hand-written activities and shows the adults what happened.

Rules for this release:

- Use the existing lesson format, catalog, and engine (the code calls an activity a lesson).
- People approve the exact wording and pictures of each activity; changed content needs a new approval. A `reviewed` mark in the authoring spreadsheet does not count.
- Runs on this computer only: no outbound requests, sharing, analytics, or remote files.
- Session state stays in memory. Nothing about the child is saved, and logs contain no learner content.
- The app never decides what comes next; an adult chooses.
- Before a child uses it: technical checks pass, an adult rehearses it, and a parent authorizes it.

### Story: Supervisor starts an approved activity

As a supervising adult, I want to start only approved activities, so that the child sees nothing an adult hasn't checked.

- WHEN an activity is unapproved or its files do not match their recorded fingerprints THE SYSTEM SHALL refuse to show it.
- WHEN the app opens THE SYSTEM SHALL show the supervisor view, listing approved activities only.
- WHEN the supervisor presses Start THE SYSTEM SHALL show the activity's first step.

### Story: Child works through the activity

As a child, I want to read, look, and choose an answer, so that I can work out the idea myself.

- WHEN a step is shown THE SYSTEM SHALL display its prepared text, its pictures with text alternatives, and its choices.
- WHEN the child picks a wrong choice THE SYSTEM SHALL show the next prepared hint.
- WHEN the hints run out THE SYSTEM SHALL show the answer and finish the activity.
- WHEN the child picks the right choice THE SYSTEM SHALL show completion.

### Story: Child explains their answer

As a child, I want to say why I chose my answer, so that the adult can tell whether I understand.

- WHEN the child answers the check THE SYSTEM SHALL ask them to explain their reasoning to the adult.
- WHEN the child explains THE SYSTEM SHALL record nothing; the adult notes it privately if useful.

### Story: Adult sees a recap

As a supervising adult, I want a short summary when the activity ends, so that I can note what worked.

- WHEN the activity ends or is stopped THE SYSTEM SHALL show the supervisor which choices were picked, which hints were used, and how long it took.
- WHEN the supervisor leaves the recap or presses Reset THE SYSTEM SHALL discard it; nothing is saved.

### Story: Supervisor stops or resets

As a supervising adult, I want to stop or restart at any moment, so that I stay in control of the session.

- WHEN the supervisor presses Stop THE SYSTEM SHALL end the interaction and discard any pending action.
- WHEN the supervisor presses Reset THE SYSTEM SHALL clear progress and return to the supervisor view; another activity requires Start.
- WHEN a delayed, repeated, or earlier-session action arrives THE SYSTEM SHALL ignore it if the session was stopped, reset, or replaced.

## Release 2: voice

Release 1's rules still apply.

### Story: The app talks and listens

As a child, I want the app to talk with me and hear my answer, so that I can learn without reading or typing.

- WHEN a step is read aloud THE SYSTEM SHALL keep its text visible.
- WHEN a session starts, or the supervisor presses Stop or Reset, THE SYSTEM SHALL turn the microphone off; only the supervisor turns it on.
- WHEN the child answers by voice THE SYSTEM SHALL listen only while the talk button is held.
- WHEN speech is turned into text THE SYSTEM SHALL show it for correction and send nothing until confirmed.
- WHEN voice is unavailable THE SYSTEM SHALL still accept tapped choices.
- WHEN a recording has been used, or something fails, THE SYSTEM SHALL delete it; no recording is saved.

## Later

- **Draft and approve (stage 2):** the system drafts activities from the seeded examples; an adult approves each.
- **Guardrails and spot checks (stage 3):** adults set limits and sample-check.
- **Suggesting what's next:** the system proposes the next idea on the map; at first an adult chooses.

## Out of scope

Accounts, cloud sync, more than one family, and public deployment.

## Decisions

- 2026-08-23: Explore is the active product; Study gets maintenance only. (No reason was recorded.)
- 2026-09-25: Educators author paths alongside development instead of after a pilot, because authoring, development, and early observations should inform each other.
- 2026-09-25: The first app uses text, pictures, and choices, as the smallest app that can run a reviewed activity.
- 2026-10-07: Voice (the app speaks and listens) is the student app's goal and its key unlock; text and pictures come first as a stepping stone.
- 2026-10-07: A discovery round comes before building, because watching a real session tells us what the app must do.
- 2026-10-07: No requirement IDs for now; refer to releases and stories by name.
- 2026-10-07: Humans only seed the first one or two activities as worked examples. Adult involvement then steps down: seed, then draft-and-approve, then guardrails and spot checks once drafting is reliable.
- 2026-10-07: Call the unit an "activity", not a "lesson".
- 2026-10-07: Two PRDs: this supervised student app, and the builder's terminal [admin tool](admin.md). Educators supervise through the app's supervisor view, never the terminal.
- 2026-10-07: The student app keeps a parent-written list of off-limits topics, set before first use and added to over time.

## Open questions

- [NEEDS CLARIFICATION] Where is speech turned into text: on this computer, or by an outside service that would receive the child's voice?
- [NEEDS CLARIFICATION] Which reading-aloud voice do we use, and does it run locally?
- [NEEDS CLARIFICATION] How is a spoken answer matched to the prepared choices?
- [NEEDS CLARIFICATION] What evidence shows drafting is reliable enough to move from approving each activity to spot checks?
- [NEEDS CLARIFICATION] What goes on the starting off-limits list, and where is it kept?
- [NEEDS CLARIFICATION] Where would drafting run, given that Releases 1 and 2 make no outbound requests?
