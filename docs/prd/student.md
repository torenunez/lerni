# PRD: Student app

A student talks with Lerni about something they already love (cars, sharks, soccer, or anything else). Lerni follows their curiosity and, now and then, builds a bridge from what they love to something their educator wants them to explore. Everything they talk about grows an **interest map**: their **interests** (what they love), their **goals** (what they're working toward), and the bridges between them. A supervised student has an educator alongside; an independent student is their own educator. Over time the app remembers what they like, talks and listens, and needs the educator less. Educator tasks: [educator PRD](educator.md). How it's built and run: [admin tool PRD](admin.md). Design: [interest map spec](../../plans/specs/04-interest-map.md).

## Outcome

A student keeps coming back to talk about their interests, and can explain the ideas they found in their own words.

## Users

Every student signs in, and is one of two kinds, set by supervision, not age:

- **Supervised student:** talks with Lerni with an educator's guidance, usually on an iPad. The educator chooses the goals and is beside them in every Release 1 session. Often a child; we design for around 7–9, because if it is intuitive at that age, it works for older students too.
- **Independent student:** their own educator. They talk with Lerni, see their own map, and add their own "things to practice". Often an adult; the educator and admin each use the app this way too.

Both kinds share the same conversation and map. One person can be a student and also the educator or admin.

## How the experience grows

| Release | What the student gets |
|---|---|
| 1 | A text conversation about what they love that gently bridges to goals, and grows their interest map |
| 2 | A companion that remembers what they like and checks they still remember earlier ideas |
| 3 | A conversation they can hold by voice: one button, held to talk |
| 4 | New goals suggested from their map, for the educator to accept |
| 5 | Conversation without an educator present |

## What makes it engaging

- **It starts with their interest,** never with the subject.
- **It answers first, then bridges.** It follows their curiosity and links new ideas to ones they love, one goal at a time, never forced.
- **They do the thinking.** Narrowing follow-up questions ("top speed or acceleration?") invite them to go deeper, and now and then the agent asks them to explain a goal back in their own words.
- **It comes back to things.** Ideas from a while ago come up again, and a goal is reached again from a different interest.
- **It's short.** Brief replies; they can stop any time, and finishing is not the goal.
- **No scores, no failing.**

## Guarantees

These hold for every release.

**For every student:**

- Conversation text is never saved to disk, logs, or browser storage: one ongoing conversation per student lives in memory until New conversation or a server restart. What's saved is the account and the interest map (interest names, educator notes, time, and links).
- No account details (name, username) are sent to Claude; their own messages can still contain anything.
- Goals come only from a person: an educator, or an independent student for their own map. The agent only records interests, time, and links.
- Nothing is sent to an outside service without consent at the moment of sending. In the family prototype, pressing Send (or Upload) is that consent: everyone in the household knows where messages go, so the screen carries no notice. A short notice comes back before anyone outside the family uses it.
- A student never sees another student's map or conversation.
- It's designed for touch and phones first. That's a goal, not an absolute.

**For a supervised student, also:**

- An educator is beside them in every Release 1 session.
- Replies are short and gentle. Subjects on the educator's starting exclusion list (violence, weapons, sexual content, self-harm, drugs), and anything scary or sad, get a kind redirect to their educator and something fun instead.
- It behaves the same whether or not an educator is watching.

## Release 1: talk about what you love

The student signs in and talks with Lerni by text. Their map grows as they talk; the educator (or the independent student, for themselves) adds goals and watches the bridges appear. This is the MVP ([build plan](../../plans/release-1-mvp.md), [design](../../plans/specs/04-interest-map.md)).

### Story: Sign in as me

As a student, I want to sign in as myself, so that my conversation and map are my own.

- WHEN someone opens the app without being signed in THE SYSTEM SHALL show a standard sign-in form (username and password) that the browser can offer to save.
- WHEN a supervised student signs in THE SYSTEM SHALL show only the conversation, full screen; WHEN an independent student signs in, Ask, My map, and My account.
- WHILE someone is signed in THE SYSTEM SHALL show "Signed in as <display name> · <kind>" and a Sign out button that signs out this device only.
- WHEN a username gets 3 or more wrong passwords in a row THE SYSTEM SHALL wait longer before checking each further attempt (up to 30 seconds), without affecting anyone already signed in.
- WHEN an account is archived or its password reset THE SYSTEM SHALL sign it out on every device at once.

A supervised student's iPad is signed in only as that student; the educator and admin use their own devices (a household rule, not something the app can enforce).

### Story: Talk about what I love

As a student, I want to ask anything by text and get clear, short answers, so that I can explore what I'm curious about right away.

- WHEN a student sends a question THE SYSTEM SHALL stream Claude's answer, briefly and at their level, sometimes ending with one question that invites them to go deeper.
- WHILE they're in a conversation THE SYSTEM SHALL keep one ongoing conversation per student, the last 20 messages, only in memory, the same on each of their devices, until they start a new conversation or the server restarts. Lerni keeps no transcript; Anthropic's own retention applies to what is sent.
- WHILE an answer is streaming THE SYSTEM SHALL turn Send into Stop, keeping what was said so far if they press it, and keep their question if the answer fails.
- WHEN the conversation fits naturally THE SYSTEM SHALL build a bridge from one of their interests to one goal, one at a time, never forced or announced.

### Story: My interests grow a map

As a student, I want what I talk about to be remembered as interests, so that the next conversation starts from what I love.

- WHEN an exchange ends THE SYSTEM SHALL record which interests it was about, any new interest, and any bridge, and add the time spent (capped at 3 minutes per exchange).
- WHEN a new conversation starts THE SYSTEM SHALL start from the map: their top interests and the goals.
- WHEN an independent student opens My map THE SYSTEM SHALL show their map and let them add, rename, and remove entries, set their own goals (things to practice), and Upload notes that Claude turns into proposed interests and goals, saving only the ones they tick.

## Release 2: a companion that remembers me

The companion learns what each student likes (how they like to be talked to, which examples land) and, after a gap, asks one quick recall question about an earlier idea from their map. Stories to be written when Release 2 starts.

## Release 3: talk with the app

### Story: Hold to talk

As a student, I want to hold one button to talk and let go when I'm done, so that I can learn without reading or typing.

- WHEN the student holds the talk button THE SYSTEM SHALL listen until they let go, then answer aloud with the text visible.
- WHEN speech is turned into text THE SYSTEM SHALL show it for correction before it reaches the conversation. The audio itself goes only to a speech-to-text service the educator approved.
- WHEN voice is unavailable THE SYSTEM SHALL still accept typing.
- WHEN a recording has been used THE SYSTEM SHALL delete it.

## Release 4: new goals from the map

The agent suggests goals that connect to what the student already loves; the educator accepts or declines each. Stories to be written after Release 3.

## Release 5: conversation without an educator present

### Story: Talk about my interests for as long as I like

As a student, I want to keep talking about what interests me, so that I can learn without waiting for anyone.

- WHEN the student raises a sensitive subject (death, illness, the body, family matters, religion, politics) THE SYSTEM SHALL pause it, ask the educator, and offer something else meanwhile.
- WHEN a question touches an excluded subject THE SYSTEM SHALL decline kindly and steer elsewhere.

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
- 2026-10-09: A student is supervised or independent, set by supervision, not age. One PRD covers both; they share the same activities, engine, and screens.
- 2026-10-09: Every student signs in on a standard sign-in form the browser can save, and the account is re-checked on every request, so archive and reset take effect at once. One app, with tabs by role. (Gradio's built-in login was considered first; it checks only at sign-in and isn't a form browsers save.)
- 2026-10-09: An independent student is their own educator: they plan, import with Claude, and approve their own activities. Explore freely, their own switch, lets Claude's full drafts play unchecked, labeled.
- 2026-10-09: "Nothing needs a keyboard" becomes a goal: designed for touch first.
- 2026-10-09: A supervised student's iPad is signed in only as that student; the educator and admin dogfood on their own devices.
- 2026-10-09: Release 5 is renamed "free conversation", so it isn't confused with Explore freely.
- 2026-10-09: Release 1 saves the account and an independent student's plans, but still no progress record. (Replaces "nothing about the student is saved".)
- 2026-10-09: The app is AI-enabled from Release 1: independent students get Ask Lerni, a text conversation with Claude (open questions, kept only in memory). It comes before cards, and Release 3 adds voice on top of it.
- 2026-10-09: Ask Lerni is one ongoing conversation per student, not one per visit: the start of a companion that, from Release 2, remembers what each student likes. For an independent student it helps them study directly. Confirmed by the admin's first real use: after answering "what's the fastest car?", it asked whether they were more interested in top speed or acceleration. Narrowing follow-ups like that are the direction to keep.
- 2026-10-09: A supervised student's AI conversation is Release 3, not Release 1. Their whole screen is the conversation: one button they hold to talk and release when done. The agent is a companion that starts from the student's interests and gracefully steers back to the educator-approved learning plan, so learning feels like play; it isn't an open chat. It runs on an API key under Anthropic's commercial terms (never the admin's consumer account, which is for people 18 and over), with reply checks, and the educator can see the conversation.
- 2026-10-09: The interest map replaces activity cards, learning plans, approvals, Explore freely, and the plan import. The conversation is the whole activity; interests grow from it (sized by time), the educator adds goals, and the agent bridges between them. Upload is just a way to add goals. Only educators see a supervised student's map. (Replaces the Release 1 cards-and-taps design and "Remembering comes before voice".)
- 2026-10-09: A supervised student talks with Lerni by text in Release 1, through the admin's Claude account, with an educator beside them in every session. No API key is planned. The admin chose this knowing Anthropic's consumer terms are for people 18 and over and consumer Claude has no filtering for children. (Replaces the earlier decision to wait for Release 3 and an API key.)

## Open questions

- [NEEDS CLARIFICATION] (Release 2) Should a supervised student see their own map, as a way to feel progress? (Release 1: educators only.)
- [NEEDS CLARIFICATION] (Release 3) Which speech-to-text service and which reading-aloud voice? Audio must reach the speech-to-text service before there is any text to confirm, so "send nothing until confirmed" covers what happens after transcription. Does transcription run on the home server or at an outside service the educator approved?
- [NEEDS CLARIFICATION] (Release 5) How does a consent request reach the educator, and how long does the student wait?
