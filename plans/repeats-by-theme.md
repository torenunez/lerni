# Repeats by theme, and where embeddings help (options, for review)

**Status:** open; the admin's call, after an outside review (2026-11-10).

**The problem:** the admin still sees race questions on the same few themes for a goal, even though each question's idea is new.
- An example is one interest's sizes asked again and again in different ways.
- Another is a car's speeding up, in almost every set.

**This doc:** the options, their trade-offs, and an internal review's verdicts on more uses for local embeddings ([spec 10](specs/10-local-embeddings.md)).

## What's in place

- **Checks by meaning (v3.40):**
  - a question is dropped if its idea's label is 0.91 or closer to a label on its goal's "asked lately" list (30 days, up to 30 a goal);
  - it's also dropped if it's 0.55 or closer to a set-aside interest.
- **Fresher races (v3.42–v3.43, shipped 2026-11-10, not yet measured):**
  - 15 are written and the 10 most different are kept;
  - each question gets a format and a setting, dealt by the server;
  - every interest takes turns;
  - the morning plan adds steps for each goal.
- **Calibration:** 103 made-up label pairs and a bake-off script (`scripts/data/embedding_pairs.jsonl`).

## Why the 0.91 check can't catch theme repeats

- Spec 10's tests put a rewording of one idea at 0.70, and two *different* ideas on one goal as close as 0.90.
- Same-theme questions on different ideas therefore pass the 0.91 check, and that's by design.
- Lowering the cut would drop questions that really are new angles.

## Causes that have nothing to do with embeddings

| Cause | Where |
|---|---|
| One car comparison in every set, using only 0-60 time, horsepower, and price | [race.py](../src/lerni/student/race.py) `QUIZ_SYSTEM` |
| Missed ideas come back after 1, 3, and 7 days, by design | `concepts.py` |
| When Claude can only repeat, repeats race anyway | `race.py` (`spare`) |
| Goals take turns, but interests are counted across all goals, so one goal can keep landing on the same interest | `race.py` `deal`, `concepts.settings_since` |
| A background write isn't checked against a race that just started | [to-do](../docs/todo.md) (v3.9 review) |

## Options

| Option | What | For | Against |
|---|---|---|---|
| **A. Measure first** (recommended internally) | A one-off repeat report from production's concept ledger, labels and numbers only. It splits repeats into: by design (reviews), goal-and-interest lock-in, car comparisons, repeats raced anyway, and clusters of one theme in other words (each goal's 30-day labels, at 0.75, 0.85, and 0.91). Plus a week of the "Race set" log lines. Then fix only the causes it shows. | Fixes the real cause. Measures v3.42–v3.43 first. Cheap: one script, nothing shipped. | About a week before the measured fixes. The report is a real student's labels, so it stays private: shown on the admin's screen, never in the repo. |
| **B. Fix all now** | Ship the cheap fixes together in v4.1: a prompt line ("avoid the same theme in other words, not just the same idea"), interests taking turns within each goal, rotating which car number is compared, and the banked-question check (below). | Fast. No embeddings. Each fix is small and tested with fakes. | May fix causes that aren't there, and blurs what v3.42–v3.43 did. |
| **C. Theme clustering** | Before each write, group each goal's recent labels by meaning (about 0.8) and tell Claude "themes asked a lot lately: … (×6)". It's a hint, never a drop. | Goes after theme repetition directly. A wrong group costs little. | The threshold isn't measured. One more embedding call (2–4 s, outside the race lock). More code and a new pair set. |

Cheap either way: the theme prompt line (in B) can ride with A or C.

## A smaller call: keep the text of questions marked ✗?

v4.1 saves only a ✗'d question's hash, so a reworded copy can race again.
- **No (recommended):** a ✗ usually means a wrong answer key, and v4.2 sends the educator's reason to the question writer.
- **Yes:** add ✗'d question text (educator-judged, never a student's words) to rule 6's list, so rewordings can be caught by meaning.

## The review's verdicts on more embedding uses

- **Keep, in v4.1:** a banked question's label joins the existing repeat check. A race then doesn't ask a fresh question on the same idea alongside it, with no new embedding call.
- **Keep, only if the report shows it:**
  - **Due ideas:** match a reworded due idea back to its label by meaning (same goal, 0.91 or closer). Otherwise its review never moves and it keeps coming back.
- **Defer, each until something shows a need:**
  - **Steps:** count a step as tried by meaning, once a goal's steps never empty while its questions repeat.
  - **Version 5:** drop a suggested goal that repeats an existing one, once one is seen.
  - **v4.2+, answer keys already in the bank:** let the Tell Lerni agent see the goal's bank first, and use meaning only if that fails.
  - **Version 6, from the checked bank:**
    - examples in the prompt, once a goal's bank passes about 20;
    - recall neighbours.
  - **Version 7 (the set-aside check):** run it on the morning plan and on Upload, which only matters without an educator present.
- **Dropped:**
  - a filter for numbers and negation: there are no false positives at 0.91 on the pairs;
  - a diverse audit sample, since it would bias the error rate and the 3 come from 3 different goals anyway;
  - flags for wrong choices too close to the answer, since the blind second check is stronger;
  - routing guidance notes to goals, and catching duplicate ones, by meaning: the Tell Lerni agent does both better, and a person ticks;
  - comparing whole question texts;
  - embeddings as a safety guard for Version 7, since they catch about 63% of close pairs. An LLM check stays the guard.

## Questions for reviewers

1. Is measuring first worth about a week, given the admin's aim of Versions 4–7 this week?
2. Is a theme hint (C) a sound use of embeddings, or does the prompt line alone usually do the job?
3. Is any dropped use worth more than the review gave it, at family scale (a few students, hundreds of questions a week)?
4. Should ✗'d question text be kept?
