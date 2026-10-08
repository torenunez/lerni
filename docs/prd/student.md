# PRD: Student app

A student starts from something they already love (cars, sharks, soccer) and follows it to the ideas underneath. At first the app asks the questions and an educator sits alongside. Over time the app remembers what the student explored, talks and listens, and lets them roam more freely, always within what their educator allows. Educator tasks: [educator PRD](educator.md). How it's built and run: [admin tool PRD](admin.md).

## Outcome

A student keeps coming back to explore their interests, and can explain the ideas they found in their own words.

## Users

- **Student:** anyone exploring their interests with an educator's guidance, on an iPad. We design for a student around 7–9: if it is intuitive at that age, it works for older students too. An educator is beside them in every Release 1 session; from Release 2, usually but not always.

## How the experience grows

| Release | What the student gets |
|---|---|
| 1 | Questions about something they love, answered by tapping |
| 2 | An app that remembers them and builds on what they explored |
| 3 | An app they can talk to, and ask their own questions |
| 4 | New ideas that grow from ones they already know |
| 5 | Free exploration by conversation |

Remembering comes before voice: it is what turns separate activities into a journey.

## What makes it engaging

- **It starts with their interest,** never with the subject.
- **They do the thinking.** Wrong answers get a hint, not the answer.
- **Every new idea links to one they know.**
- **It's short.** A few minutes; they can stop any time, and finishing is not the goal.
- **Their questions count.** From Release 3, they can start the conversation.
- **No scores, no failing.**

## Guarantees

These hold for every release.

- It works by touch on an iPad; nothing needs a keyboard.
- It explores only what the educator allows: at first just the concepts on the educator's allowlist, later anything not on their exclusion list, once the educator turns that on.
- It never shows an excluded concept or a path the educator blocked. Sensitive subjects (death, illness, the body, family matters, religion, politics) wait for the educator's consent.
- It stops the moment a session is stopped.
- It behaves the same whether or not an educator is watching.

## Release 1: answer questions about something you love

The app asks short questions about one of the one or two activities an educator wrote, and the student answers by tapping. Nothing about the student is saved. This is the MVP: the first thing the student tries ([roadmap M2](../roadmap.md#m2--mvp)).

### Story: Work it out myself

As a student, I want questions I can answer by tapping, with hints when I'm stuck, so that I figure the idea out myself.

- WHEN a step is shown THE SYSTEM SHALL display its question, its pictures with text alternatives, and its answer choices.
- WHEN the student picks a wrong choice THE SYSTEM SHALL show the next hint.
- WHEN the hints run out THE SYSTEM SHALL show the answer and finish.
- WHEN the student picks the right choice THE SYSTEM SHALL show completion.

### Story: Say why

As a student, I want to say why I chose my answer, so that I show what I understand, not just what I picked.

- WHEN the student answers the check THE SYSTEM SHALL ask them to explain their reasoning out loud, and record nothing.

## Release 2: the app remembers me

The app keeps a small record (activities finished, ideas reached, recall results) so each session builds on the last. No recordings or transcripts.

### Story: Connect today to before

As a student, I want today's activity to link to something I did before, so that new ideas make sense.

- WHEN an activity involves an idea the student reached before THE SYSTEM SHALL remind them of it.
- WHEN a session starts THE SYSTEM SHALL show which earlier ideas today's activity connects to.

### Story: Remember what I learned

As a student, I want a quick question about something from last time, so that I keep it.

- WHEN the student returns after a gap THE SYSTEM SHALL ask one recall question about an earlier idea before the new activity.

## Release 3: talk with the app

### Story: Talk and be heard

As a student, I want the app to talk with me and hear my answers, so that I can learn without reading or typing.

- WHEN a step is read aloud THE SYSTEM SHALL keep its text visible.
- WHEN the educator has authorized voice THE SYSTEM SHALL listen whenever the student holds the talk button.
- WHEN speech is turned into text THE SYSTEM SHALL show it for correction and send nothing until confirmed.
- WHEN the student answers by voice THE SYSTEM SHALL judge the answer without a tap.
- WHEN voice is unavailable THE SYSTEM SHALL still accept taps.
- WHEN a recording has been used THE SYSTEM SHALL delete it.

### Story: Ask my own question

As a student, I want to ask about whatever I'm curious about, so that the conversation can start from me.

- WHEN the student asks an allowed question THE SYSTEM SHALL answer briefly, then lead back toward the learning plan.
- WHEN the question is not allowed THE SYSTEM SHALL say kindly that it can't talk about that, and lead back.
- WHEN the app generates a reply THE SYSTEM SHALL check it the same way before saying it.

## Release 4: new ideas grow from old ones

The app suggests the next activity from the student's map of ideas, linked to something they already know. An educator approves each one first. Stories to be written after Release 3.

## Release 5: explore freely

### Story: Talk about my interests for as long as I like

As a student, I want to keep asking and answering questions about what interests me, so that I can learn without waiting for anyone.

- WHEN the student asks about an allowed concept THE SYSTEM SHALL answer and keep the conversation going.
- WHEN the student asks about a sensitive subject THE SYSTEM SHALL pause it, ask the educator, and offer something else to explore meanwhile.
- WHEN a question touches an excluded concept or a blocked path THE SYSTEM SHALL decline kindly and steer elsewhere.

## Out of scope

Public access and a native iPad app.

## Decisions

- 2026-08-23: The student app is the main product; the admin tool gets maintenance only. (No reason was recorded.)
- 2026-09-25: The first release uses text, pictures, and taps, as the smallest app that can run a reviewed activity.
- 2026-10-07: Voice is the student app's goal and key unlock; text and pictures come first as a stepping stone.
- 2026-10-07: The app leads a student from idea to idea, building on what they already explored.
- 2026-10-07: Remembering comes before voice.
- 2026-10-07: A session starts with the app asking, or (from Release 3) the student asking. The app answers allowed questions briefly, then leads back to the learning plan.
- 2026-10-07: The app explores only the allowlist first, then anything not excluded once the educator turns that on.
- 2026-10-07: The end state is free conversation without an educator involved; only sensitive subjects wait for consent, and that should be rare.
- 2026-10-08: Sensitive subjects are allowed but personal (death, illness, the body, family matters, religion, politics).
- 2026-10-08: The student's progress record is kept until the educator deletes it; the educator can turn remembering off.
- 2026-10-08: There is no hand-run trial first. Release 1 is the MVP the student tests, and watching those first sessions shapes what comes next. (Replaces the 2026-10-07 discovery-round decision.)

## Open questions

- [NEEDS CLARIFICATION] (Release 2) Should the student see their own map of ideas, as a way to feel progress?
- [NEEDS CLARIFICATION] (Release 3) How does the app decide a question or reply suits a student, beyond the two lists?
- [NEEDS CLARIFICATION] (Release 3) How does the app judge a spoken answer: against prepared answers, or with its own understanding?
- [NEEDS CLARIFICATION] (Release 3) Which speech-to-text service and which reading-aloud voice? Audio must reach the speech-to-text service before there is any text to confirm, so "send nothing until confirmed" covers what happens after transcription. Does transcription run on the home server or at an outside service the educator approved?
- [NEEDS CLARIFICATION] (Release 5) How does a consent request reach the educator, and how long does the student wait?
