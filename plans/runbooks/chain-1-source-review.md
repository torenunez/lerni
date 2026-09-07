# Checking the Lesson's Science

The lesson teaches one idea: **a car's "0–60 time" is how many seconds something
took — not the same thing as acceleration.** It makes four claims, all citing one
NASA page. Read the quotes below, say whether they hold up.

The quotes were pulled by software; the judgment is yours, so open the page and
check. If you can't confirm something, say so — it stays blocked, which is the
system working.

**Source:** [Displacement, Velocity, Acceleration](https://www.grc.nasa.gov/WWW/K-12/airplane/disvelac.html)
— NASA Glenn Research Center. Confirmed loading 2026-08-23; that's not this check.

---

## The four claims

### 1. What a 0–60 number actually means

> **The lesson says:** "A 0-to-60 result reports the elapsed time for velocity to
> change from 0 miles per hour to 60 miles per hour."

**What the NASA page says about this:** nothing. The page is about aircraft and
rocket motion. It never mentions cars or 0–60 figures at all.

**This one needs your judgment.** It isn't really physics — it's about how car
magazines write specs. Either accept it as a restatement of the definition NASA
*does* give (velocity changing over time), or ask for a second source that
actually covers 0–60 as a timed measurement. Neither is obviously right.

Your decision: ______________________________________________

### 2. What acceleration is

> **The lesson says:** "Average acceleration is change in velocity divided by
> elapsed time."

**What the NASA page says:**

> "The **acceleration (a)** of the object through the domain is the change of the
> velocity with respect to time."

> "the **average acceleration** is the change in velocity divided by the time
> interval: a = (V1 - V0) / (t1 - t0)"

**This one is nearly word-for-word.** Should be a quick yes.

Confirmed? ☐ yes ☐ no — notes: ______________________________

### 3. Comparing two cars

> **The lesson says:** "For two straight-line runs with the same initial and final
> velocities, the shorter elapsed time has the greater average acceleration."

**What the NASA page says:** it gives the formula `a = (V1 - V0) / (t1 - t0)`,
but never makes this comparison itself.

**Reasoning, not a quote** — it follows from the formula: same speed change, less
time, bigger acceleration.

Watch the qualifier: *"the same initial and final velocities."* Without it the
claim is flatly false, and it's exactly the kind of clause someone trims later
for readability. Confirm it's there.

Confirmed? ☐ yes ☐ no — notes: ______________________________

### 4. Average isn't the whole story

> **The lesson says:** "A 0-to-60 elapsed time can support average acceleration
> over the interval but does not reveal acceleration at every instant."

**What the NASA page says:** it gives average acceleration as
`a = (V1 - V0) / (t1 - t0)` and instantaneous acceleration as `a = dv/dt`, and
treats them as two different things.

**The distinction is well supported.** As with claim 1, the 0–60 framing is ours.

Confirmed? ☐ yes ☐ no — notes: ______________________________

---

## The simplified wording

What the child actually reads. The risk is that simplifying makes a claim
*stronger* than the evidence supports.

- [ ] "A 0–60 result tells how many seconds the speed change took."
- [ ] "Acceleration tells how quickly velocity changes."
- [ ] "If both cars make the same speed change, the one that does it in less time has greater average acceleration."
- [ ] "A car can accelerate differently during the run, so 0–60 supports an average."

Also confirm: no brand, no logo, no current-rankings claim, and that the 4- and
8-second figures read as hypothetical examples, not real vehicles.

---

## Recording it

Hand this part off if you like. What matters is that the role and date are real
and came from you.

```toml
[[review.attestations]]
id = "chain-1-science-1"
scope = "science"
reviewer_role = "<your actual role>"
reviewed_on = 2026-01-01   # the real date you reviewed
evidence_ref = "plans/runbooks/chain-1-source-review.md"
reviewed_payload_sha256 = "<the exact hash you were shown>"
```

Set `retrieved_on` to the date **you** opened the page.

Your name isn't recorded, only your role. The hex string fingerprints the exact
wording you approved — edit the lesson later and it stops matching, so it goes
back for review.

One of four checks; the others are in [`../human-track.md`](../human-track.md).
All four must reference the same fingerprint.
