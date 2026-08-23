# Human Track — Non-Coding Work

Every `## Manual prerequisites` block in this plan bundle, collected into one
status file. The runbooks in [`runbooks/`](./runbooks/) say **how** to do these
things; this file says **whether they are done**.

## Two rules

1. **No child sees anything until PR-08's pilot gate passes.** Not a preview, not
   a rehearsal. PR-06 produces a UI a *parent or developer* can open; that is not
   a pilot. See [`prs/08-pilot-gate.md`](./prs/08-pilot-gate.md).
2. **No agent ever records an attestation, review date, or content hash.** A
   coding agent may prepare evidence for a reviewer. Only a human writes the
   verdict. Fabricating one is a Standing Rule 3 violation.

Unlike `docs/todo.md`, completed items **stay here**. An approval trail is only
useful as history — knowing a review happened, and when, is the point.

---

## Done

| Date | Item | Outcome |
|---|---|---|
| 2026-08-23 | Confirm "Explore active / Study maintenance-only" is still the product decision | Confirmed. Locked in `docs/mission.md`, `CLAUDE.md`. |
| 2026-08-23 | Confirm graph/recommendation stays post-first-pilot | Confirmed. PRs 09–11 sit behind the pilot decision. |
| 2026-08-23 | Project `.venv` with `ruff` and `pytest` | Present. Commit gate resolves from `.venv/bin` first. |
| 2026-08-23 | `jq` on PATH for Claude Code PreToolUse commits | Present. |
| 2026-08-23 | Chain-1 source availability check | NASA Glenn page resolves and supports the acceleration definitions. Evidence in [`runbooks/chain-1-source-review.md`](./runbooks/chain-1-source-review.md). **This is availability, not a science attestation.** |

---

## Do now — unblocks PR-02

PR-02's code can be written and tested against draft content. The lesson cannot
leave `status = "draft"`, and `PackageLessonCatalog` will refuse to serve it,
until all four reviews below are real.

### Chain-1 content review (4 attestations required)

Work from [`runbooks/chain-1-source-review.md`](./runbooks/chain-1-source-review.md).
Review the **exact final payload hash**, not a draft — the hash is generated at
the end of PR-02 stage 5, so these reviews happen after the code lands.

- [ ] **`science`** — a scientifically competent reviewer verifies the four facts,
      the average-vs-instantaneous distinction, and the source. **Open question
      waiting on this reviewer:** the fact `zero-to-sixty-is-time` cites the NASA
      page, but that page never mentions cars or 0–60. Decide whether it is an
      acceptable derivation of the sourced definition or needs a second source.
- [ ] **`child_content`** — parent or educator reviews age fit and tone for ages 7–9.
- [ ] **`visual_accessibility`** — reviewer checks the exact SVG bytes, its hash,
      and the alt text. Confirm no meaning is carried by color alone.
- [ ] **`parent_approval`** — a parent records explicit approval for this family pilot.

Each becomes one `[[review.attestations]]` entry with a stable id, the actual
reviewer role, the actual date, and the **same** `reviewed_payload_sha256`.
Reviewer names are not stored — roles only.

### Interest notes (parallel, no gate)

[`runbooks/data-priming.md`](./runbooks/data-priming.md) permits parents to draft
sanitized interest observations while PRs 01–08 proceed. The workbook templates
do not exist until PR-09, so this is freeform notes for now.

- [ ] Sanitized notes on what the child actually gravitates toward about cars.
- [ ] A truthful 1–5 engagement judgment and real first/last observed dates.

Never write: child name, initials, birthday, school, address, contact details,
exact location, raw quotes, or any medical/behavioral/diagnostic label.

---

## Do later — grouped by the gate that needs it

### PR-03 · Runtime boundary
- [ ] Pick an absolute private runtime root outside the repository (not a symlink, not cloud-synced).
- [ ] Qualify the Python executable used for helper subprocesses.
- [ ] Decide fallback-only vs. optional plugin qualification.

### PR-05 · Telemetry lifecycle
- [ ] Telemetry enabled or disabled.
- [ ] Retention: 1–3650 days purged at startup/maintenance, or explicit manual. No wall-clock scheduler is promised.
- [ ] Confirm telemetry/export/audio paths are private and non-synced.
- [ ] Review the managed-wipe scope and its storage-remanence limits.

### PR-06 · Gradio app
- [ ] Qualify a compatible current Gradio version.
- [ ] Dedicated minimal browser profile for cache/log/temp canaries.
- [ ] Confirm actual browser speech routing — do not assume it is local.
- [ ] Fallback-only readiness review before first launch.

### PR-07 · Audio input
- [ ] Decide typed-only, local STT, or external STT.
- [ ] Both parents acknowledge that raw voice reaches STT **before** transcript redaction.
- [ ] For local STT: preinstall and verify artifacts/licenses, observe network behavior.
- [ ] Browser microphone permission scoped to the local origin.

### PR-07A · Real capability adapters (only if you want a real LLM or voice)
- [ ] Choose the pilot level: `authored_typed`, `generated_tutor`, or `generated_tutor_voice_input`.
- [ ] Per service: account, terms, retention, logging, training-use, region, quota, billing cap, MFA, revocation path.
- [ ] Least-privilege credential placed in a credential store under an opaque reference name. **Value never enters TOML, Git, IPC, telemetry, logs, or a spreadsheet.**
- [ ] Record adapter id/version, artifact hash, route, and declared retention in the private operator record.

### PR-08 · Pilot gate — the child boundary
- [ ] Lesson attestations and hashes complete.
- [ ] Synthetic export / delete / managed-wipe exercises pass.
- [ ] Browser data-handling canaries pass.
- [ ] Parent reviews the exact readiness report and its stated limitations.
- [ ] **Both parents consent to the specific enabled data routes.**
- [ ] One parent present and able to stop immediately.

### PR-09 · Curation
- [ ] Local CSV editor or private Google Sheets. (No Google API, OAuth, or service account either way.)
- [ ] Reviewers lined up for the later 25-attestation content gate.

### PR-10 · Curriculum graph
- [ ] Private bundle carries real dates, source review, asset hash, and 25 active attestations.
- [ ] Both parents review the generated lesson/asset/index diff and hashes.
- [ ] Operator confirms manifest hash and the formula-free attestation.

### PR-11 · Recommendations
- [ ] Parent selects interest scope and allowed nudge kinds.
- [ ] Readiness attested **only from actual observation** — otherwise leave it `unknown`.
- [ ] Parent reviews each deterministic explanation before approval.

---

## Accounts — summary

Nothing in PRs 01–08 requires a service account, API key, hosted Gradio account,
Google account, or deployment service. The authored baseline runs on typed input,
reviewed content, local SQLite, and visible text.

Accounts become relevant only at PR-07A, and only for the tier you choose.
Full procedure: [`runbooks/manual-setup.md`](./runbooks/manual-setup.md).
