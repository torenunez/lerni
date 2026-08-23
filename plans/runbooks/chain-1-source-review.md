# Runbook — Chain-1 Source Review Sheet

## What this is

The Chain-1 acceleration lesson makes four factual claims, all citing one source.
Before the lesson can leave `status = "draft"`, a scientifically competent
reviewer must confirm that the source still supports those claims and record the
date they actually checked.

This sheet exists so the reviewer verifies **four specific quotes** rather than
reading a physics article and cross-referencing from scratch.

**The evidence below was gathered by an agent. The verdict is not.** Fill in the
right-hand columns yourself, from the live page. If you cannot confirm a row, the
lesson stays draft and no child sees it — that is the system working, not a
failure to route around.

## Source under review

- **id**: `nasa-acceleration`
- **title**: Displacement, Velocity, Acceleration
- **publisher**: NASA Glenn Research Center
- **url**: <https://www.grc.nasa.gov/WWW/K-12/airplane/disvelac.html>
- **checked reachable**: 2026-08-23 (availability only — not a science review)

## Evidence table

### Fact 1 — `zero-to-sixty-is-time`

> **Our claim:** "A 0-to-60 result reports the elapsed time for velocity to change
> from 0 miles per hour to 60 miles per hour."

**Supporting text found on the source:** *none.* The page discusses aircraft and
rocket motion. It never mentions cars, 0–60 figures, or automotive specifications.

**Status: UNSUPPORTED by this source.** This is a claim about how car
specifications are written, not a physics claim. It is the one row that needs a
real decision:

- Accept it as a definitional framing that follows from the sourced definition of
  velocity change over time, and note that reasoning in the attestation; **or**
- Add a second source that actually discusses 0–60 as an elapsed-time measurement,
  update `source_ids`, and regenerate the payload hash.

Reviewer decision: ______________________________________________

### Fact 2 — `acceleration-definition`

> **Our claim:** "Average acceleration is change in velocity divided by elapsed time."

**Supporting text on the source:**

> "The **acceleration (a)** of the object through the domain is the change of the
> velocity with respect to time."

> "the **average acceleration** is the change in velocity divided by the time
> interval: a = (V1 - V0) / (t1 - t0)"

**Status: DIRECTLY SUPPORTED.** Near-verbatim.

Confirmed? ☐ yes ☐ no — notes: ______________________________

### Fact 3 — `shorter-time-greater-average`

> **Our claim:** "For two straight-line runs with the same initial and final
> velocities, the shorter elapsed time has the greater average acceleration."

**Supporting text on the source:** the formula `a = (V1 - V0) / (t1 - t0)`.

**Status: DERIVED, not stated.** The page does not make this comparison. It
follows arithmetically: hold the numerator `(V1 - V0)` fixed and shrink the
denominator, and `a` increases. The reviewer is attesting to the derivation being
sound and the "same initial and final velocities" qualifier being present and
necessary — without it the claim is false.

Confirmed? ☐ yes ☐ no — notes: ______________________________

### Fact 4 — `average-not-instant`

> **Our claim:** "A 0-to-60 elapsed time can support average acceleration over the
> interval but does not reveal acceleration at every instant."

**Supporting text on the source:** the page gives average acceleration as
`a = (V1 - V0) / (t1 - t0)` and instantaneous acceleration as `a = dv / dt`,
treating them as distinct quantities.

**Status: DIRECTLY SUPPORTED** for the distinction. The 0–60 framing is again ours.

Confirmed? ☐ yes ☐ no — notes: ______________________________

## Also check the child-facing wording

The `child_text` of each fact is what a 7–9 year old reads. It must stay true to
`canonical_text` while being simpler — not truer than the evidence allows.

- [ ] "A 0–60 result tells how many seconds the speed change took."
- [ ] "Acceleration tells how quickly velocity changes."
- [ ] "If both cars make the same speed change, the one that does it in less time has greater average acceleration."
- [ ] "A car can accelerate differently during the run, so 0–60 supports an average."

Also confirm the lesson packages **no brand, no logo, and no current-rankings
claim**, and that the 4-second and 8-second figures read as hypothetical examples
rather than assertions about real vehicles.

## Recording the result

When satisfied, record in `chain_1_acceleration.toml`:

```toml
[[review.attestations]]
id = "chain-1-science-1"
scope = "science"
reviewer_role = "<your actual role>"
reviewed_on = 2026-01-01   # the real date you reviewed
evidence_ref = "plans/runbooks/chain-1-source-review.md"
reviewed_payload_sha256 = "<the exact hash you were shown>"
```

Also update `retrieved_on` in `[[grounding.sources]]` to the date **you** opened
the page.

`science` is one of four required scopes. The other three — `child_content`,
`visual_accessibility`, `parent_approval` — are tracked in
[`../human-track.md`](../human-track.md). All four must carry the **same**
`reviewed_payload_sha256`; a mismatch fails the parser closed.
