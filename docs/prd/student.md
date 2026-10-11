# PRD: Student app

A student talks with Lerni about something they already love (cars, sharks, soccer, or anything else). Lerni follows their curiosity and, now and then, builds a bridge from what they love to something their educator wants them to explore. Everything they talk about grows an **interest map**: their **interests** (what they love), their **goals** (what they're working toward), and the bridges between them. A supervised student has an educator alongside; an independent student is their own educator. Over time the app remembers what they like, talks and listens, and needs the educator less. Educator tasks: [educator PRD](educator.md). How it's built and run: [admin tool PRD](admin.md). Design: [interest map spec](../../plans/specs/04-interest-map.md).

## Outcome

A student keeps coming back to talk about their interests, and can explain the ideas they found in their own words.

## Users

Every student signs in, and is one of two kinds, set by supervision, not age:

- **Supervised student:** talks with Lerni with an educator's guidance, usually on an iPad. The educator chooses the goals and is beside them in every Release 1 session.
- **Independent student:** their own educator. They talk with Lerni, see their own map, and add their own "things to practice". The educator and admin each use the app this way too.

Both kinds share the same conversation and map, and the experience is simple and engaging for people of all ages. One person can be a student and also the educator or admin.

## How the experience grows

| Release | What the student gets |
|---|---|
| 1 | A text conversation about what they love that gently bridges to goals, and grows their interest map |
| 2 | A conversation they can hold by voice: one button, held to talk |
| 3 | A companion that remembers what they like and checks they still remember earlier ideas |
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

- Conversation text is kept on the home server only in 7-day logs the admin can read, then deleted; never in browser storage. The ongoing conversation lives in memory until New conversation or a server restart. Also saved: the account and the interest map (interest names, goals and notes, dates, and links).
- No account details (name, username) are sent to Claude; their own messages can still contain anything.
- Goals come only from a person: an educator, or an independent student for their own map. The agent only records interests, time, and links.
- Nothing is sent to an outside service without consent at the moment of sending. In the family prototype, pressing Send (or Upload) is that consent: everyone in the household knows where messages go, so the screen carries no notice. A short notice comes back before anyone outside the family uses it.
- A student never sees another student's map or conversation.
- It's designed for touch and phones first. That's a goal, not an absolute.

**For a supervised student, also:**

- An adult is nearby whenever they use it (a household rule the app doesn't enforce), and Lerni says plainly it's a computer helper.
- Replies are short and gentle. Subjects on the starting exclusion list (violence, weapons, sexual content, self-harm, drugs), and anything scary or sad, get a kind redirect to their educator and something fun instead.
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
- WHILE they're in a conversation THE SYSTEM SHALL keep one ongoing conversation per student, the last 20 messages, in memory, the same on each of their devices, until they start a new conversation or the server restarts. Anthropic's own retention applies to what is sent.
- WHILE an answer is streaming THE SYSTEM SHALL turn Send into Stop, keeping what was said so far if they press it, and keep their question if the answer fails.
- WHEN the conversation fits naturally THE SYSTEM SHALL build a bridge from one of their interests to one goal, one at a time, never forced or announced.

### Story: My interests grow a map

As a student, I want what I talk about to be remembered as interests, so that the next conversation starts from what I love.

- WHEN an exchange ends THE SYSTEM SHALL record which interests it was about, any new interest, and any bridge, and the day it came up; interests grow with the days they come up.
- WHEN a new conversation starts THE SYSTEM SHALL start from the map: their top interests and the goals.
- WHEN an independent student opens My map THE SYSTEM SHALL show their map and let them add, rename, and remove entries, set their own goals (things to practice), and Upload notes that Claude turns into proposed interests and goals, saving only the ones they tick.

## Release 2: talk with the app

### Story: Hold to talk

As a student, I want to hold one button to talk and let go when I'm done, so that I can learn without reading or typing.

- WHEN the student holds the talk button THE SYSTEM SHALL listen until they let go, show what it heard in the chat, and send it at once, as if typed; Stop works as it does for text.
- WHEN Lerni answers THE SYSTEM SHALL speak it aloud a sentence at a time as it's written, with the text visible; Stop silences it.
- WHEN speech is turned into text, or text into speech, THE SYSTEM SHALL do it on the home server, so no audio leaves the house; any audio kept on the server is deleted within 7 days, like the conversation logs.
- WHEN voice is unavailable THE SYSTEM SHALL still accept typing.

## Release 3: a companion that remembers me

The companion learns what each student likes (how they like to be talked to, which examples land) and, after a gap, asks one quick recall question about an earlier idea from their map. Stories to be written when Release 3 starts.

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
- 2026-09-25: The first release uses text, pictures, and taps, as the smallest app that can run a reviewed activity. (Replaced 2026-10-09 by the interest map.)
- 2026-10-07: Voice is the student app's goal and key unlock; text and pictures come first as a stepping stone.
- 2026-10-07: The app leads a student from idea to idea, building on what they already explored.
- 2026-10-07: Remembering comes before voice.
- 2026-10-07: A session starts with the app asking, or (from Release 3) the student asking. The app answers allowed questions briefly, then leads back to the learning plan. (Replaced 2026-10-09 by the interest map.)
- 2026-10-07: The app explores only the allowlist first, then anything not excluded once the educator turns that on. (Replaced 2026-10-09 by the interest map.)
- 2026-10-07: The end state is free conversation without an educator involved; only sensitive subjects wait for consent, and that should be rare.
- 2026-10-08: Sensitive subjects are allowed but personal (death, illness, the body, family matters, religion, politics).
- 2026-10-08: The student's progress record is kept until the educator deletes it; the educator can turn remembering off. (Replaced 2026-10-09 by the interest map.)
- 2026-10-08: There is no hand-run trial first. Release 1 is the MVP the student tests, and watching those first sessions shapes what comes next. (Replaces the 2026-10-07 discovery-round decision.)
- 2026-10-09: A student is supervised or independent, set by supervision, not age. One PRD covers both; they share the same activities, engine, and screens. (Replaced 2026-10-09 by the interest map.)
- 2026-10-09: Every student signs in on a standard sign-in form the browser can save, and the account is re-checked on every request, so archive and reset take effect at once. One app, with tabs by role. (Gradio's built-in login was considered first; it checks only at sign-in and isn't a form browsers save.)
- 2026-10-09: An independent student is their own educator: they plan, import with Claude, and approve their own activities. Explore freely, their own switch, lets Claude's full drafts play unchecked, labeled. (Replaced 2026-10-09 by the interest map.)
- 2026-10-09: "Nothing needs a keyboard" becomes a goal: designed for touch first.
- 2026-10-09: A supervised student's iPad is signed in only as that student; the educator and admin dogfood on their own devices.
- 2026-10-09: Release 5 is renamed "free conversation", so it isn't confused with Explore freely.
- 2026-10-09: Release 1 saves the account and an independent student's plans, but still no progress record. (Replaces "nothing about the student is saved".) (Replaced 2026-10-09 by the interest map.)
- 2026-10-09: The app is AI-enabled from Release 1: independent students get Ask Lerni, a text conversation with Claude (open questions, kept only in memory). It comes before cards, and Release 3 adds voice on top of it.
- 2026-10-09: Ask Lerni is one ongoing conversation per student, not one per visit: the start of a companion that, from Release 3, remembers what each student likes. For an independent student it helps them study directly. Confirmed by the admin's first real use: after answering "what's the fastest car?", it asked whether they were more interested in top speed or acceleration. Narrowing follow-ups like that are the direction to keep.
- 2026-10-09: A supervised student's AI conversation is Release 3, not Release 1. Their whole screen is the conversation: one button they hold to talk and release when done. The agent is a companion that starts from the student's interests and gracefully steers back to the educator-approved learning plan, so learning feels like play; it isn't an open chat. It runs on an API key under Anthropic's commercial terms, with reply checks, and the educator can see the conversation. (Replaced 2026-10-09 by the interest map.)
- 2026-10-09: The interest map replaces activity cards, learning plans, approvals, Explore freely, and the plan import. The conversation is the whole activity; interests grow from it, the educator adds goals, and the agent bridges between them. Upload is a way to add interests and goals. Only educators see a supervised student's map. (Replaces the Release 1 cards-and-taps design. Remembering, Release 2, still comes before voice, Release 3.)
- 2026-10-09: A supervised student talks with Lerni by text in Release 1, through the admin's Claude account, with an educator beside them in every session. No API key is planned. (Replaces the earlier decision to wait for Release 3 and an API key.)
- 2026-10-09: After two outside reviews of the map design: interests are sized by the days they come up and goals by the days the student explained them back (Lerni's guess at competence), replacing time spent. Every student's conversation is kept for 7 days in logs the admin reads, so the map can be checked against what was said (replaces "conversation text is never saved"). Release 1 has no automatic reply check and no app-enforced co-presence: the household keeps an adult nearby, the iPad is signed in only as the student, and the adults never save their passwords on it.
- 2026-10-09: Voice comes before remembering: Release 2 is voice, Release 3 remembering. Speech-to-text and text-to-speech run on the home server (local Whisper and Kokoro, as separate helper programs behind two calls, "transcribe" and "speak", set by environment variables), so no audio leaves the house and no new account is needed; a hosted service only if the local ones are too slow or flat with the students. What Lerni heard is sent at once, shown in the chat, instead of waiting for a confirm tap. (Replaces "remembering comes before voice" and "show the text for correction before it reaches the conversation", and answers which speech services to use.)
- 2026-10-10: Voice audio may stay on the home server for up to 7 days, like the conversation logs; Release 2 keeps whatever is easiest (it doesn't save audio on purpose). (Replaces "audio is held in memory only and never saved".)
- 2026-10-10: Lerni speaks with the home server's own voice (macOS `say`) and hears with whisper.cpp's `whisper-cli`, both run as commands, so there's nothing to install for the voice and no helper program to keep running; Kokoro or a hosted voice can replace them behind the same adapter. While the button is held, what's heard so far shows below it. Only spoken questions are answered aloud. With voice on, both conversation screens are just the chat and the button (a tap stops Lerni); typing shows only when voice is off. (Replaces "local Whisper and Kokoro, as separate helper programs".)
- 2026-10-10: Files Gradio keeps in its cache on the home server (an upload before it's read, any voice audio) can be reached by URL by anyone signed in. Accepted for the household: at most three people signed in, each with their own account. Revisit before anyone outside the family uses the app.

## Open questions

- [NEEDS CLARIFICATION] (Release 3) Should a supervised student see their own map, as a way to feel progress? (Release 1: educators only.)
- [NEEDS CLARIFICATION] (Release 5) How does a consent request reach the educator, and how long does the student wait?
