# Lerni — Mission

## Vision

**Help people learn deeply and remember permanently.**

Lerni is one repository with two modes, aimed at two different learners:

- **Study** helps a self-directed adult understand a topic well enough to explain it, then remember it, by combining the Feynman Technique with SM-2 spaced repetition.
- **Explore** helps a child follow something they already care about — a fast car — down into the fundamental idea underneath it, with a parent present.

Both rest on the same conviction: understanding is demonstrated by explanation, and retained by revisiting.

## Two Modes

| | Study | Explore |
|---|---|---|
| Learner | Self-directed adult | Child, with a supervising parent |
| Interface | Terminal CLI (`study`) | Local browser page, localhost only |
| Status | **Feature-complete, maintenance-only** | **Active development** |
| Core loop | Explain → find gaps → refine → review on schedule | Interest → reviewed lesson → retrieval check |

Study is not deprecated and is not being removed. Its Phase-1 command surface works and stays compatible. It receives fixes and hardening, not new features, while Explore is being built.

"One engine, two modes" is the intended direction, not a description of today. Study's concept graph and scheduler are not currently driving Explore. The first Explore slice is deliberately isolated behind its own interfaces so that the two can be unified later on evidence rather than merged early on optimism.

## Core Beliefs

### Learning is active
Passive consumption — reading, watching — creates an illusion of understanding. Real learning requires explaining, questioning, and connecting. This is as true for a seven-year-old asked what they think will happen as for an adult writing out a proof.

### Interest is a scaffold
A child will not care about acceleration on request. They may care about it because a car they like reaches 60 mph quickly. Interest is the ladder to the fundamental idea, not a decoration on top of it.

Distance between an interest and a fundamental — how many concepts separate them — is a **curriculum-authoring heuristic**. It helps a human decide what to teach next. It is not a validated measure of difficulty, and the number depends entirely on how finely the author chose to split concepts.

### Simplicity reveals mastery
The ability to explain something complex in plain terms is the strongest available test of understanding. Jargon usually conceals confusion rather than conveying precision.

### Forgetting is natural
Without reinforcement, most of what we learn decays within days. Scheduled revisiting is what turns a moment of understanding into durable knowledge.

### Privacy and parent control matter
Study notes may hold proprietary or personal material. A child's learning session holds something more sensitive still. Lerni runs locally by default and makes no network calls unless the operator explicitly configures and qualifies a capability that requires one.

In Explore, a supervising parent controls what is retained, and can export or delete any session. Retention is a setting the parent chooses, not a default the software imposes.

### AI serves, but does not own curriculum or progression
An AI capability may rephrase an explanation or answer a bounded question. It does not choose what is taught, decide whether an answer was correct, mark anything as mastered, or advance the lesson. Those decisions belong to reviewed content and application logic, which a human can inspect.

## Target Learners

**Study** — self-learners working through technical or complex material; professionals maintaining expertise across domains; students who prefer active recall to passive review; anyone who has read a book and lost it a month later.

**Explore** — a child roughly ages 7–9 with a strong specific interest, learning alongside a parent who is present for the session. Explore is built for one family at a time. It is not built for classrooms, unsupervised use, or distribution.

## Success

**Study succeeds** when a user can explain their topics to a beginner, sustains a review habit, finds and fills gaps over time, and still holds the material months later.

**Explore succeeds** when a child comes back on their own and, later, still remembers the idea.

Session duration is explicitly not the measure. A short session a child chooses to repeat is a better signal than a long one they sat through. The first pilot is intended to test whether the approach creates curiosity at all — a negative answer is a real and useful result.

## Non-Goals

### Study non-goals
- Social features and sharing
- Cloud sync
- Mobile apps
- AI-generated study content — an AI may challenge what the user wrote, not write it for them

### Explore non-goals
- Any use outside the immediate family. Non-family use, classroom use, or public deployment requires a separate privacy, safety, and legal review that has not been done and is not planned as part of this work.
- Claims of production-grade safety. Explore's guardrails are prototype controls plus a present parent. They are not a moderation system and are not a compliance posture.
- Autonomous operation. Explore assumes a parent in the room.
- Replacing school, a teacher, or a curriculum.
