# Checking the Lesson's Science

## What you're being asked to do

The lesson teaches one idea: **a car's "0–60 time" is how many seconds something
took — it is not the same thing as acceleration.** It makes four specific claims,
and all four cite the same NASA page.

Your job is to read four short quotes and say whether they hold up. You should
not have to read a physics article and work backwards; that's what this sheet is
for.

The software will not show this lesson to a child until you've done this. If you
can't confirm something, say so and it stays blocked — that's the system working
correctly, not an obstacle to get around.

**The quotes below were pulled by software. The judgment is yours.** Open the
page yourself and check them.

## The source

**Displacement, Velocity, Acceleration** — NASA Glenn Research Center
<https://www.grc.nasa.gov/WWW/K-12/airplane/disvelac.html>

Confirmed online on 2026-08-23. That only means the page loaded — it is not the
check you're doing now.

---

## The four claims

### 1. What a 0–60 number actually means

> **The lesson says:** "A 0-to-60 result reports the elapsed time for velocity to
> change from 0 miles per hour to 60 miles per hour."

**What the NASA page says about this:** nothing. The page is about aircraft and
rocket motion. It never mentions cars or 0–60 figures at all.

**This is the one that needs your judgment.** The claim isn't really physics —
it's a statement about how car magazines write specifications. Two reasonable
options:

- **Accept it** as a plain restatement of the definition NASA does give (velocity
  changing over time), and note that reasoning when you sign off; or
- **Ask for a second source** that actually discusses 0–60 as a timed
  measurement. That means updating the lesson and redoing the fingerprint.

Neither is obviously right. Pick one and say why.

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

**So this one is reasoning, not a quote.** It follows from the formula: if the
speed change stays the same and the time gets smaller, acceleration gets bigger.

The part worth your attention is the qualifier — *"the same initial and final
velocities."* Without it the claim is flatly false, and it would be easy for
someone to trim it later for readability. Please confirm it's there and that you
think it belongs.

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

## Also: the simplified wording

Each claim has a plain-English version — that's what the child actually reads.
It has to stay honest while being simpler. The risk is that simplifying
accidentally makes a claim *stronger* than the evidence supports.

- [ ] "A 0–60 result tells how many seconds the speed change took."
- [ ] "Acceleration tells how quickly velocity changes."
- [ ] "If both cars make the same speed change, the one that does it in less time has greater average acceleration."
- [ ] "A car can accelerate differently during the run, so 0–60 supports an average."

Also confirm the lesson packages **no brand, no logo, and no current-rankings
claim**, and that the 4-second and 8-second figures read as hypothetical examples
rather than assertions about real vehicles.

---

## Recording it

This part is for whoever types it in — you can hand it off. What matters is that
the role and date are real, and that they came from you.

Add to `chain_1_acceleration.toml`:

```toml
[[review.attestations]]
id = "chain-1-science-1"
scope = "science"
reviewer_role = "<your actual role>"
reviewed_on = 2026-01-01   # the real date you reviewed
evidence_ref = "plans/runbooks/chain-1-source-review.md"
reviewed_payload_sha256 = "<the exact hash you were shown>"
```

Also set `retrieved_on` to the date **you** opened the page — not the date at the
top of this sheet.

Your name is not recorded; only your role. The long hex string is a fingerprint
of the exact wording you approved, so if anyone edits the lesson afterward it
stops matching and the software blocks it until someone re-reviews. Approving
specific words rather than the lesson in general is the point.

This is one of four checks. The other three — age fit, the picture, and a
parent's permission — are listed in [`../human-track.md`](../human-track.md).
All four have to be done, and all four have to reference the same fingerprint.
