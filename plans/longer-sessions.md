# Longer student sessions within the Claude Pro limits

## Context

**The admin's goal (2026-11-11):** longer student sessions without hitting the plan limit. The ideas:
- write things ahead, before the session;
- host, and maybe train, a model on this Mac to call instead of Claude.

**Two outside research notes** (private, never committed) are weighed below.

**Where things stand:**
- **No limit hit so far:** production's log shows no pauses.
- **What the usage tracker sees:** each call's share of the 5-hour and weekly windows (`usage.py`, read in `adapters/claude_code.py:90`). It doesn't record which feature spent it.
- **A busy day:** about 10 races and 30–37 conversation turns.

### What was checked (read-only)

| Claim from the notes | Checked | Result |
|---|---|---|
| Chat is Sonnet, one call per student message; the tagger is Haiku, one call per exchange | `serve.py`, `app.py:366-375` | Verified |
| Writing, the blind check, bonus grading, area sorting and the morning plan all share one Haiku adapter (`ClaudeCodeQuizzer`) | `app.py:321-344` | Verified: one place to plug in a local model |
| The blind check lets every question through when it fails | `race.py` `_verify` ("all of them if it can't run") | Verified: a weaker local checker would quietly remove protection |
| Calls carry no Claude Code overhead | `tools=[]`, `setting_sources: []` | Verified: only Lerni's own prompts count |
| 4 races are written at 05:00 and at start-up; the rest during the session | `race.py:76-77`, `app.py:237` | Verified. Held questions live only in memory, so a restart (any deploy) loses them. |
| The Mac's resources | `sysctl`, `df` | M4, **16 GB memory**, **16 GB disk free**. Room for one 4B model at 4-bit (about 3 GB), not several, and no training while students use it. |
| Training on Claude's outputs needs Anthropic's permission | The notes cite the usage policy | Taken as given. **Labels must come from people** (the bank's ratings); Claude's outputs may only be used to score. |

**What the notes get right:**
- measure first;
- move work out of the session;
- a reviewed bank is the safest saving;
- training from scratch (nanoGPT or nanochat) is a learning project, not a product path.

**Where I differ:**
- **The biggest lever for session length is chat on Sonnet,** not the Haiku tagger. Sonnet counts several times more against the limits per token, and every turn resends up to 20 earlier messages.
- **Writing ahead helps the 5-hour window, not the weekly one.** Work done at night lands in a different 5-hour window from the afternoon session, but it still counts toward the week. Only fewer calls (or local ones) help the week.

## The admin's calls (2026-11-11)

- **Unraced questions written ahead** may stay on disk until the day ends (a rule 6 addition).
- **The local tagger's shadow test** may read the conversation logs in place. Nothing leaves the Mac, and only agree/disagree counts are kept.
- **The usage meter comes first** after v4.5. *Replaced 2026-11-11:* it comes after the map picture and Tell Lerni, with minimal CI (v4.8); write-ahead and the daily check share a PR (v4.9).
- **Supervised chat on Haiku 5.5** may be tested, with a switch back.

## The plan: four versions, each its own PR, after v4.5 merges

### A. Usage meter (small; first, so everything after is measured)

- **What each Claude call records, numbers only:**
  - the use case (chat, tagger, question writing, blind check, bonus grading, area sort, morning plan, upload, educator chat);
  - the model;
  - input, output and cached tokens, from the SDK's result;
  - seconds taken and retries;
  - the 5-hour and weekly window shares after the call.
- **Where it goes:** `usage/<day>.jsonl` in the data folder. No usernames, no text.
- **How it's read:** `lerni stats` gains a "Claude use by feature" table: today, the last 7 days, and the share of each window.
- **Rule 6:** add "Claude usage counts (numbers only)".
- **Code:** the adapter already sees `rate_limit_info`. Read `ResultMessage.usage` beside it, and pass the use case as a label through each adapter's call sites.
- **Test:** one call through a fake writes one row with the feature and the token counts.

### B. Write the day ahead, overnight (moves session load into a night window)

- **The night job:** at 02:00, before the 05:00 morning plan, write the day's whole supply, about 12 races of questions plus their bonuses, through the usual checks.
- **During the session,** writing happens only when the supply runs out.
- **Kept on disk until the day ends** (`ahead/<user>.json`), so a deploy or restart doesn't throw them away and pay for them again. **This needs a rule 6 change** (the admin's call).
- **Picking up today's changes:** a goal or set-aside change during the day already drops held questions at race start (`fits`, `_still_on`). Those checks stay.
- **What it measures:** with the meter, compare the session's 5-hour window share before and after.

### C. Lighter chat turns (the biggest per-turn cost)

- **Measure first,** with A, how much each chat turn grows over a session.
- **Then try, using the eval on made-up students:**
  1. keep fewer earlier messages (20 → 10), with a one-line summary of the rest;
  2. send the map context only once it changes;
  3. **supervised chat on Haiku 5.5:** a quality check by the admin first, and a switch to go back.
- **Keep** whichever saves the most with no quality loss the admin can see.

### D. A local model on this Mac (tagger first, shadow only)

- **Serving:** `llama-server` (already installed with llama.cpp) runs Qwen3.5-4B at 4-bit as a resident service on this Mac only (loopback), with a JSON schema.
- **The adapter:** a `LocalTagger` behind the existing `Tagger` interface.
- **Shadow mode first:** the local tagger runs beside Haiku on the same exchanges, and records only whether their fields agree. Nothing it decides reaches the map or points.
- **The bar to switch:**
  - at least 90% agreement on `answered`;
  - `skip` catches every case Haiku catches;
  - no false merges in a reviewed sample.
- **Then:** local first, with Haiku taking the cases where they disagree or the local output is malformed.
- **Next candidates, each measured the same way:**
  - the area sorter, by embeddings alone (no language model);
  - bonus grading, local first, but Claude on "partly" and on anything about care.
- **Stays on Claude:** chat, question writing, the blind check, and uploads.
- **Training (LoRA with MLX), only if shadow mode shows a gap:**
  - on human labels only (the bank's ratings, or hand labels);
  - never on Claude's outputs without Anthropic's written permission;
  - never while a student is using Lerni.

### Not doing

- **Training from scratch:** nanoGPT is retired, and nanochat is a separate learning weekend on rented GPUs.
- **A model per student.**
- **Switching to an API key:** the admin wants to stay on the plan. The notes' "gray area" stays on the to-do list for before anyone outside the family uses Lerni.

## Order

v4.5 (bulk ratings and question quality) → v4.6 the map picture (general interests only) → v4.7 Tell Lerni → **v4.8 A, the usage meter**, with minimal CI → **v4.9 B, overnight write-ahead**, with check a few questions → **v4.10 C, lighter chat** → **v4.11 D, local tagger in shadow** → Versions 5–7.

**Data check-in:** about a week after A ships, read the meter. It may reorder B, C and D.

## Files (by version)

- **A:**
  - `adapters/claude_code.py` (read the usage, label the call);
  - `usage.py` or a new `meter.py`;
  - `stats.py`;
  - the docs: CLAUDE.md rule 6, the code manifest, the admin reference.
- **B:**
  - `race.py`: `prefill` and `_held` move to a disk-backed store with a day stamp, and `AHEAD_RACES` grows;
  - `web/app.py`: the night timer, reusing `seconds_until`;
  - rule 6.
- **C:**
  - `conversation.py` (`MAX_TURNS`, the context);
  - `serve.py` (a model setting for supervised chat);
  - the eval scripts.
- **D:**
  - a new `adapters/llama_chat.py`, alongside `llama_embed.py`;
  - `tagging.py` (the shadow hook);
  - a script that compares the two taggers, modelled on `scripts/bakeoff_embeddings.py`.

## Verification

- **Each version:** `pytest` and ruff, a fresh Opus review, and the docs-drift check.
- **A:** one day of production use shows a per-feature table in `lerni stats` that adds up to the windows' movement.
- **B:** the meter shows question writing and blind-check calls moving into the 02:00 window, and a restart mid-day keeps the supply.
- **C:** the chat eval scores and the admin's read show no visible drop, and tokens per turn fall.
- **D:** the shadow agreement report on at least 200 exchanges, plus memory and response time measured while a session runs.
