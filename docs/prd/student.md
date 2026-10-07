# PRD: Supervised student app

What the child experiences in the app (`explore` in the code), and what the app guarantees them. Every task an educator or parent performs is in the [educator and parent PRD](educator.md); the admin's terminal work is in the [admin tool PRD](admin.md). Each release has its own section; the [roadmap](../roadmap.md) says which one is current. When a spec in `plans/` disagrees with this file, this file wins until the spec is updated.

## Outcome

A child explores ideas they care about through short activities, and shows they understand them in their own words.

## Users

- **Child, about 7–9, in one family:** explores ideas that start from their own interests, with an adult present. The goal is a conversation by voice.

## Constraints

These hold for every release.

- The child sees only activities an adult has approved, never a topic on the off-limits list.
- A session can be stopped at any moment. Stopping or resetting clears the child's screen at once, and any delayed, repeated, or earlier-session action is ignored.
- The admin tool's commands and data keep working.
- These are prototype guardrails, not production moderation. One family; no public use.

## Release 1: run a seeded activity

Built after the [discovery round](../roadmap.md#m2--discovery-round). The child works through one of the one or two activities an educator wrote by hand.

Rules for this release:

- Use the existing lesson format, catalog, and engine (the code calls an activity a lesson).
- Runs on this computer only: no outbound requests, sharing, analytics, or remote files.
- Session state stays in memory. Nothing about the child is saved, and logs contain no learner content.
- The app never picks the next activity on its own.

### Story: Child works through the activity

As a child, I want to read, look, and choose an answer, so that I can work out the idea myself.

- WHEN an activity is unapproved or its files do not match their recorded fingerprints THE SYSTEM SHALL refuse to show it.
- WHEN a step is shown THE SYSTEM SHALL display its prepared text, its pictures with text alternatives, and its choices.
- WHEN the child picks a wrong choice THE SYSTEM SHALL show the next prepared hint.
- WHEN the hints run out THE SYSTEM SHALL show the answer and finish the activity.
- WHEN the child picks the right choice THE SYSTEM SHALL show completion.

### Story: Child explains their answer

As a child, I want to say why I chose my answer, so that I show what I understand, not just what I picked.

- WHEN the child answers the check THE SYSTEM SHALL ask them to explain their reasoning out loud.
- WHEN the child explains THE SYSTEM SHALL record nothing.

## Release 2: voice

Release 1's rules still apply.

### Story: The app talks and listens

As a child, I want the app to talk with me and hear my answer, so that I can learn without reading or typing.

- WHEN a step is read aloud THE SYSTEM SHALL keep its text visible.
- WHEN the microphone has not been turned on by an adult THE SYSTEM SHALL not listen.
- WHEN the child answers by voice THE SYSTEM SHALL listen only while the talk button is held.
- WHEN speech is turned into text THE SYSTEM SHALL show it for correction and send nothing until confirmed.
- WHEN voice is unavailable THE SYSTEM SHALL still accept tapped choices.
- WHEN a recording has been used, or something fails, THE SYSTEM SHALL delete it; no recording is saved.

## Later

- Activities drafted by the system, in the seeded pattern, once adults approve them.
- Suggestions for the next idea on the map, for an adult to choose from.

## Out of scope

Accounts, cloud sync, more than one family, and public deployment.

## Decisions

- 2026-08-23: The student app (then called Explore) is the active product; the admin tool gets maintenance only. (No reason was recorded.)
- 2026-09-25: The first app uses text, pictures, and choices, as the smallest app that can run a reviewed activity.
- 2026-10-07: Voice (the app speaks and listens) is the student app's goal and its key unlock; text and pictures come first as a stepping stone.
- 2026-10-07: A discovery round comes before building, because watching a real session tells us what the app must do.
- 2026-10-07: No requirement IDs for now; refer to releases and stories by name.
- 2026-10-07: Call the unit an "activity", not a "lesson".
- 2026-10-07: Separate PRDs by who acts. This file covers the child; adult tasks are in the educator and parent PRD; terminal work is in the admin tool PRD.

## Open questions

- [NEEDS CLARIFICATION] Where is speech turned into text: on this computer, or by an outside service that would receive the child's voice?
- [NEEDS CLARIFICATION] Which reading-aloud voice do we use, and does it run locally?
- [NEEDS CLARIFICATION] How is a spoken answer matched to the prepared choices?
