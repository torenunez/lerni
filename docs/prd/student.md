# PRD: Supervised student app

What the student experiences in the app, and what the app guarantees them. Every task an educator performs is in the [educator PRD](educator.md); the admin's terminal work is in the [admin tool PRD](admin.md). Each release has its own section; the [roadmap](../roadmap.md) says which one is current. When a spec in `plans/` disagrees with this file, this file wins until the spec is updated.

## Outcome

Eventually the student talks back and forth with the app about their interests, without an educator involved. The app leads them from idea to idea, each new one connected to what they already explored, and the student shows they understand in their own words. Educators step back as the app earns trust.

## Users

- **Student, about 7–9, in one family:** explores ideas that start from their own interests on an iPad, with an educator present. The goal is a conversation by voice.

## Where this goes

| Release | What the student gets |
|---|---|
| 1 | One seeded activity: text, pictures, and choices |
| 2 | Continuity: the app remembers what the student explored and builds on it |
| 3 | Voice: the app talks and listens |
| 4 | New ideas that build on old ones, proposed by the app and approved by an educator |
| 5 | Free conversation: the student explores by talking, without an educator involved |

Continuity comes before voice: it is what makes this more than one-off activities, and it can be tested with text first.

In Releases 1 and 2, every session starts with the app asking a question. From Release 3, the student can also start by asking the app a question, by voice only.

## Constraints

These hold for every release.

- The app is a Gradio web app, hosted on Hugging Face Spaces, that the student opens in Safari on an iPad. Touch comes first; nothing needs a keyboard.
- Data about the student may leave the device, but only to services the educator has agreed to.
- **Allowlist mode (Releases 1–4):** the app explores only concepts and questions on the educator's allowlist. Approving an activity adds its concepts to the allowlist.
- **Exclusion-list mode (Release 5):** the app explores freely, except for concepts on the educator's exclusion list. The educator turns this mode on as a setting; the app never switches on its own.
- In both modes, the student never sees an excluded concept or a path the educator blocked, and a sensitive subject waits for the educator's consent.
- A session can be stopped at any moment. Stopping or resetting clears the student's screen at once, and any delayed, repeated, or earlier-session action is ignored.
- The admin tool's commands and data keep working.
- These are prototype guardrails, not production moderation. One family; no public use.

## Release 1: run a seeded activity

Built after the [discovery round](../roadmap.md#m2--discovery-round). The student works through one of the one or two activities an educator wrote by hand. Each activity is a short question-and-answer exchange: the app asks, and the student answers by tapping, with choices where needed.

Rules for this release:

- Use the existing lesson format, catalog, and engine (the code calls an activity a lesson).
- No sharing, analytics, or advertising.
- Session state stays in memory. Nothing about the student is saved, and logs contain no learner content.
- The app never picks the next activity on its own.

### Story: Student works through the activity

As a student, I want the app to ask me questions I can answer by tapping, so that I can work out the idea myself.

- WHEN an activity is unapproved or its files do not match their recorded fingerprints THE SYSTEM SHALL refuse to show it.
- WHEN a step is shown THE SYSTEM SHALL display its prepared question, its pictures with text alternatives, and its answer choices.
- WHEN the student picks a wrong choice THE SYSTEM SHALL show the next prepared hint.
- WHEN the hints run out THE SYSTEM SHALL show the answer and finish the activity.
- WHEN the student picks the right choice THE SYSTEM SHALL show completion.

### Story: Student explains their answer

As a student, I want to say why I chose my answer, so that I show what I understand, not just what I picked.

- WHEN the student answers the check THE SYSTEM SHALL ask them to explain their reasoning out loud.
- WHEN the student explains THE SYSTEM SHALL record nothing.

## Release 2: continuity

The app remembers what the student explored, so each session can build on the last. Release 1's rules still apply, except that a small record of the student's progress is now saved.

Rules for this release:

- Remember only which activities the student finished, which ideas they reached, and how later recall questions went. No recordings, transcripts, or free-text answers.
- The record is stored where the educator can see and delete it ([educator PRD](educator.md)).

### Story: The app builds on what I explored

As a student, I want the app to connect today's activity to something I did before, so that new ideas make sense.

- WHEN an activity involves an idea the student reached before THE SYSTEM SHALL show its prepared reminder of that earlier idea.
- WHEN the student starts a session THE SYSTEM SHALL show which earlier ideas today's activity connects to.

### Story: The app checks what I remember

As a student, I want a short question about something from an earlier session, so that I keep what I learned.

- WHEN the student returns after a gap THE SYSTEM SHALL ask one prepared recall question about an earlier idea before the new activity.
- WHEN the student answers a recall question THE SYSTEM SHALL record only whether it was answered correctly.

## Release 3: voice

The rules of Releases 1 and 2 still apply. The student can now ask the app questions by voice; the app's replies to those questions are its first generated content.

### Story: The app talks and listens

As a student, I want the app to talk with me and hear my answer, so that I can learn without reading or typing.

- WHEN a step is read aloud THE SYSTEM SHALL keep its text visible.
- WHEN the microphone has not been turned on by an educator THE SYSTEM SHALL not listen.
- WHEN the student answers by voice THE SYSTEM SHALL listen only while the talk button is held.
- WHEN speech is turned into text THE SYSTEM SHALL show it for correction and send nothing until confirmed.
- WHEN the student answers by voice THE SYSTEM SHALL judge the answer itself, without the student tapping a choice.
- WHEN voice is unavailable THE SYSTEM SHALL still accept tapped choices.
- WHEN a recording has been used, or something fails, THE SYSTEM SHALL delete it; no recording is saved.

### Story: I can ask the app a question

As a student, I want to ask the app something I'm curious about, so that the conversation can start from my question.

- WHEN the student asks a question by voice THE SYSTEM SHALL check it against the allowlist, the exclusion list, and blocked paths, and for whether it suits a student before answering.
- WHEN the question is allowed THE SYSTEM SHALL answer briefly, then steer the conversation toward the learning plan educators approved.
- WHEN the question is not allowed THE SYSTEM SHALL say kindly that it can't talk about that, and steer back to the learning plan.
- WHEN the app generates a reply THE SYSTEM SHALL check the reply the same way before saying or showing it.

## Release 4: new ideas that build on old ones

The app proposes the next activity from the concept map, connected to something the student already explored, and drafts it in the seeded pattern. An educator approves each one before the student sees it. Stories to be written after Release 3.

## Release 5: free conversation

The student talks back and forth with the app and learns about their interests without an educator involved. The educator no longer approves individual activities or interactions. Stories to be written once Release 4 is reliable.

### Story: Talk freely about my interests

As a student, I want to keep asking and answering questions about what interests me, so that I can learn without waiting for an adult.

- WHEN the student asks about an allowed concept THE SYSTEM SHALL answer and continue the conversation without educator approval.
- WHEN the student asks about a sensitive subject THE SYSTEM SHALL pause that subject, ask the educator for consent, and offer to explore something else meanwhile.
- WHEN the educator has not consented THE SYSTEM SHALL not discuss the subject.
- WHEN a question touches an excluded concept or a blocked path THE SYSTEM SHALL decline kindly and steer elsewhere, without asking the educator.

## Out of scope

More than one family, public access, and a native iPad app.

## Decisions

- 2026-08-23: The student app (then called Explore) is the active product; the admin tool gets maintenance only. (No reason was recorded.)
- 2026-09-25: The first app uses text, pictures, and choices, as the smallest app that can run a reviewed activity.
- 2026-10-07: Voice (the app speaks and listens) is the student app's goal and its key unlock; text and pictures come first as a stepping stone.
- 2026-10-07: A discovery round comes before building, because watching a real session tells us what the app must do.
- 2026-10-07: No requirement IDs for now; refer to releases and stories by name.
- 2026-10-07: Call the unit an "activity", not a "lesson".
- 2026-10-07: The app's purpose is to lead a student from idea to idea, building on what they already explored.
- 2026-10-07: Continuity (remembering what the student explored) comes before voice.
- 2026-10-07: The student app is a web app used on an iPad, not a native app, for now.
- 2026-10-07: Build it with Gradio and host it on Hugging Face Spaces; the specifics are deferred.
- 2026-10-07: For now, assume any data can leave the device, under educator supervision.
- 2026-10-07: A session starts with the app asking, or (from Release 3, by voice only) the student asking. The app answers allowed questions briefly, then steers toward the learning plan.
- 2026-10-07: The app runs in allowlist mode first (only approved concepts and questions), then in exclusion-list mode (anything not excluded).
- 2026-10-07: The end state is free conversation without an educator involved. Only sensitive subjects ask for educator consent, and that should be rare.
- 2026-10-07: Separate PRDs by who acts. This file covers the student; educator tasks are in the educator PRD; terminal work is in the admin tool PRD.

## Open questions

- [NEEDS CLARIFICATION] What counts as a sensitive subject that needs educator consent?
- [NEEDS CLARIFICATION] How does a consent request reach the educator, and how long does the student wait?
- [NEEDS CLARIFICATION] How does the app decide a question or reply suits a student, beyond the allowlist and exclusion list?
- [NEEDS CLARIFICATION] How long is the student's progress record kept, and can a educator turn remembering off entirely?
- [NEEDS CLARIFICATION] Which service turns the student's speech into text?
- [NEEDS CLARIFICATION] Which reading-aloud voice do we use?
- [NEEDS CLARIFICATION] Deferred: Hugging Face Spaces details (private Space or login, cost, which plan).
- [NEEDS CLARIFICATION] How does the app judge a spoken answer: against prepared answers, or with its own understanding?
