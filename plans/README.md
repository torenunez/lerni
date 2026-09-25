# Explore Implementation Plans

The implementation bundle for **Explore** — Lerni's parent-supervised, child-facing
mode. The lesson core (PR-02) is implemented; its Chain-1 content is an unapproved
draft. Educator authoring templates and a drafting checker exist in
[`../curation/`](../curation/README.md). The runtime, UI, and later work are still
design only.

Product milestones M1–M6 are defined in [`../docs/roadmap.md`](../docs/roadmap.md).
The numbered `prs/` files are internal work packages — plan **PR-02** is not
GitHub PR #2.

**Start here: [`cursor_master_plan.plan.md`](./cursor_master_plan.plan.md).** It owns
sequence, dependencies, manual gates, and the PR index. This file is only a map.

## Layout

| Directory | Contents |
|---|---|
| [`prs/`](./prs/) | Execution units. One file per review unit, in order — the work queue. |
| [`specs/`](./specs/) | Normative technical contracts. What each component must do. |
| [`runbooks/`](./runbooks/) | Procedures a human performs by hand: account setup, credential qualification, private data priming. |
| [`human-track.md`](./human-track.md) | **What people need to do** — written for the educator and parents, not for programmers. Tracks what has been reviewed or decided, and what is still pending. |

A PR file says *what to build and in what order*. A spec file says *what the built
thing must satisfy*. When they disagree, the spec wins — see the authority order in
the master plan.

## Which spec does each PR implement?

The two numbering schemes **do not line up**, because specs were numbered by topic
before the PR sequence was settled. This table is the mapping:

| PR | Implements |
|---|---|
| [01 — documentation](./prs/01-documentation.md) | [`01-documentation`](./specs/01-documentation.md) |
| [02 — lesson core](./prs/02-lesson-core.md) | [`02-lesson-core`](./specs/02-lesson-core.md) |
| [03 — runtime boundary](./prs/03-runtime-boundary.md) | [`00a-runtime-bootstrap`](./specs/00a-runtime-bootstrap.md), [`00-execution-contract`](./specs/00-execution-contract.md) |
| [04 — safety and tutor](./prs/04-safety-tutor.md) | [`03-safety-tutor`](./specs/03-safety-tutor.md), [`03a-policy-algorithms`](./specs/03a-policy-algorithms.md), [`03b-harm-probe-cases`](./specs/03b-harm-probe-cases.md) |
| [05 — telemetry lifecycle](./prs/05-telemetry-lifecycle.md) | [`04-telemetry`](./specs/04-telemetry.md) |
| [06 — Gradio app](./prs/06-gradio-app.md) | [`05-gradio-ui`](./specs/05-gradio-ui.md) |
| [07 — audio input](./prs/07-audio-input.md) | [`06-audio-input`](./specs/06-audio-input.md) |
| [07a — capability adapters](./prs/07a-capability-adapters.md) | self-contained; deliberately outside the core specs |
| [08 — pilot gate](./prs/08-pilot-gate.md) | [`07-verification`](./specs/07-verification.md) |
| [09 — curation CSV](./prs/09-curation-csv.md) | Early drafting checker: [`08c-educator-path-authoring`](./specs/08c-educator-path-authoring.md) (delivered, roadmap M1). Strict import: [`08-graph-recommendations`](./specs/08-graph-recommendations.md), [`08a-curriculum-persistence`](./specs/08a-curriculum-persistence.md) (not built; roadmap M5) |
| [10 — curriculum graph](./prs/10-curriculum-graph.md) | [`08a-curriculum-persistence`](./specs/08a-curriculum-persistence.md), [`08-graph-recommendations`](./specs/08-graph-recommendations.md) |
| [11 — recommendations](./prs/11-recommendations.md) | [`08b-recommendation-feedback`](./specs/08b-recommendation-feedback.md) |

`00-execution-contract` applies to every PR, not just PR-03.

## Human gates

**[`human-track.md`](./human-track.md) tracks the state of all of it.** It is
written in plain language for the people who actually do this work, with the
PR-by-PR breakdown kept in a section at the end for developers. Check there first.

Three runbooks cover work no PR can do for you:

- [`runbooks/manual-setup.md`](./runbooks/manual-setup.md) — environment, and the
  account/terms/retention/credential review required before any optional capability.
  The authored fallback-only slice needs no account and no key.
- [`runbooks/chain-1-source-review.md`](./runbooks/chain-1-source-review.md) — the
  four-fact source evidence sheet a science reviewer works from before the Chain-1
  lesson can leave draft.
- [`runbooks/data-priming.md`](./runbooks/data-priming.md) — filling and reviewing the
  private legacy-format curation bundle. The filled family copy stays untracked. New
  path authoring uses [`../curation/templates/educator-paths-v1/`](../curation/templates/educator-paths-v1/README.md).

Educator authoring and a reviewed educator-led walkthrough do **not** wait for any
PR — they run alongside development (roadmap M1–M2). What stays gated is app use:
no child uses the app before its technical gate, adult rehearsal, and parent
authorization pass, and any content a child sees still needs genuine review. The
strict import/publication work (PR-09's validator, PR-10) additionally needs the
real content reviews in its specs. PRs 09–11 do not begin merely because code is
ready.

## Ground rules

- A PR label names a future review unit. It does not authorize a commit or a push.
- No plan assumes an available model, provider, credential, speech engine, or
  accelerator. Adapters are selected by explicit runtime qualification.
- Content a child can see requires recorded human review against an exact content
  hash. Never fabricate an attestation, date, or hash to make a check pass.
