# Lerni — Product Requirements

## Product Lines

One repository, two modes, two audiences.

| Mode | Audience | Interface | Status |
|---|---|---|---|
| Study | Self-directed adult | `study` CLI | Feature-complete, maintenance-only |
| Explore | Child ages ~7–9 with a supervising parent | Local browser page on `127.0.0.1` | Active development |

The modes share a repository, a language, and a set of beliefs. They do not currently share a runtime, a database, or a scheduler.

## Study

Study is Phase-1 feature-complete. It supports the four-step Feynman workflow, immutable answer versions, SM-2 scheduling, a concept graph with typed edges, full-text search, and macOS reminders.

Feature-complete is not the same as hardened. Automated coverage exists for the SM-2 algorithm; the database layer and CLI remain untested, and lint debt is outstanding. Those gaps are tracked as optional hardening in [`todo.md`](./todo.md), not as new features.

Study requirements are unchanged by the Explore work. The `study` entry point, its command surface, and its database schema stay compatible.

## Explore

Explore takes something a child already cares about and walks it down to the fundamental idea underneath. The first lesson — "Chain 1" — starts from a car's 0–60 time and arrives at average acceleration.

Design commitments:

- **The application owns the lesson.** Lesson content is reviewed, packaged data. A deterministic state machine owns intro, teach, check, hint, and completion. Nothing generated can move the child through the lesson.
- **AI is a replaceable capability, not a requirement.** A tutor capability may phrase an explanation more warmly or answer a bounded in-scope question. There is no required model, provider, or service. With no tutor configured at all, the lesson still runs start to finish on authored text.
- **Content is human-reviewed before a child sees it.** Facts are source-backed and carry review attestations. Approval is a human act recorded against an exact content hash.
- **Local and supervised.** Localhost only, no share URL, no public deployment, one parent present.
- **The graph is future structure, not a controller.** No concept graph drives the first slice. The lesson is packaged data with an authored sequence; the curriculum graph arrives in Phase 2 to support authoring and parent-reviewable recommendations, not to select what a child sees next at runtime.

## Explore Phase-1 User Journey

1. A parent opens the local application.
2. The application confirms which runtime capabilities are available and reports them, without exposing any credential.
3. The child sees a reviewed acceleration visual and an authored opening hook.
4. The child responds by typing or, when a speech capability is qualified and the parent has enabled it, by recording a short utterance.
5. Any microphone transcription is shown to the child for correction before it is submitted.
6. Input policy runs on the submitted text.
7. A configured tutor capability may phrase a bounded response drawn from the current reviewed facts.
8. The complete response is checked for grounding and passed through an output gate before anything is displayed.
9. The application — not the tutor — advances intro, teach, check, hint, and completion.
10. Browser read-aloud is optional and never replaces the visible text.
11. The parent records an observation and can export or delete the session.

## Functional Requirements

- One reviewed Chain-1 lesson loads from packaged data.
- The child can complete that lesson with no tutor, no microphone, and no read-aloud capability available.
- A qualified tutor may enrich wording but cannot advance state, judge correctness, or unlock content.
- A correct answer completes the lesson.
- An incorrect answer produces at most the authored hint sequence, then reveals the answer. There is no penalty, score, or failure state.
- Input the policy blocks never reaches a tutor capability.
- Output the gate rejects never reaches the display or the telemetry store.
- Audio is not part of the Explore database or the export schema.
- A parent can delete a session and every row that depends on it.
- A parent or educator can describe an interest and a reviewed educational nudge without entering a child's name, a transcript, or audio.
- Only approved curation rows can prime the local curriculum graph or compile child-facing lesson content.

## Safety and Data Requirements

Explore's controls are prototype guardrails plus a present parent. They are deliberately narrow and are described here without overstatement.

- Deterministic local input and output policy, applied to complete responses rather than streamed tokens.
- Grounding checks against the current reviewed lesson facts, including numeric claims.
- A bounded turn cap per session.
- An authored fallback that runs whenever a capability is unavailable, unqualified, or fails.
- Any generated, child-facing tutor output additionally requires a separately qualified input and output harm gate. Without one, the authored fallback stays active.
- Telemetry is a separate local SQLite database holding sanitized turns, structured events, and parent observations. It stores no child name, no raw blocked content, no audio, and no credentials.
- Parent-controlled retention, JSON export, session deletion, and a registered managed wipe of local family data.

Explicit limitations: this is **not** a COPPA compliance posture, **not** production-grade moderation, and **not** anonymous or PII-free data. A provider's own safety behavior is not an application safety boundary. Deletion covers Lerni's managed local paths and cannot reach OS backups, snapshots, or any external service's retained copies.

## Success Signals

- A child completes the lesson and chooses to return without being asked.
- The child can restate the idea later, in their own words.
- A parent can tell, from sanitized records alone, what happened in a session.
- No child-facing content appeared that a human had not reviewed.

Session duration is not a success signal. A pilot that shows the approach does not create curiosity is a valid outcome and should stop the work rather than expand it.

## Deferred Requirements

- Garage / mastery loop
- Spaced resurfacing of Explore material
- Adaptive, generated, or automatically child-visible recommendations beyond the bounded parent-only Phase-2 candidate rules
- Parent curation portal
- Automatic Google Sheets synchronization
- Child image uploads
- Spanish content
- Public or non-family access
- Deployment framework and hosting choice

## Specification Index

| Document | Description |
|---|---|
| [mission.md](./mission.md) | Product vision, two modes, core beliefs |
| [roadmap.md](./roadmap.md) | Study Track and Explore Track phases |
| [spec.md](./spec.md) | Technical specification and Explore contracts |
| [todo.md](./todo.md) | Active Explore backlog and parked Study work |
| [progress.md](./progress.md) | Dated implementation log |
| [`plans/`](../plans/) | Explore safe-slice implementation bundle: [master plan](../plans/cursor_master_plan.plan.md), `prs/`, `specs/`, `runbooks/` |

Feature specifications, when written, follow:

```
specs/{YYYYMMDD}-{feature-name}/
├── requirements.md
├── spec.md
└── tasks.md
```
