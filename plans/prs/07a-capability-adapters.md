# PR-07A — Deployment-Specific Real Capability Adapters

## Purpose

Realize the provider-neutral tutor, mandatory additional-safety, and speech-to-text contracts for the actual installation selected by the parents. This is a separately reviewed deployment unit because core Explore must remain provider/model/account neutral and fully usable in authored typed mode.

This file is the implementation template for one or more adapter PRs. Replace no contract with provider-specific assumptions: if the selected tutor, safety service, and STT route require different distributions, split this unit by distribution while preserving the same gates and dependency order.

## Depends on

- PR-03 runtime/process contracts and strict private qualification/decision schemas
- PR-04 tutor and mandatory additional-safety contracts
- PR-07 speech-to-text contract and managed media boundary
- completed parent-owned account, terms, route/retention/training, quota/billing, and credential-reference decisions in `runbooks/manual-setup.md`

## Scope

Create outside the provider-neutral core package:

- one or more non-editable, fully recorded Python adapter distributions;
- typed factories implementing only the existing `TutorBackend`, `AdditionalSafetyBackend`, and/or `SpeechToTextBackend` contracts;
- provider wire codecs that emit only each capability decision's exact reviewed `data_sent` categories;
- synthetic contract/qualification fixtures containing no child or family data;
- package-local tests and operator instructions for building/installing a reproducible artifact.

Do not add provider SDKs, endpoint names, model IDs, account identifiers, secrets, or provider response objects to `src/lerni/explore`, telemetry, exports, readiness JSON, lesson packages, or CSV/Google Sheets.

## Manual prerequisites

1. Parents select the desired pilot level and separately approve every service actually needed.
2. For each service, complete the account/terms/privacy/retention/logging/training/quota/billing review.
3. Create a least-privilege credential and place it in the selected credential store under the profile's opaque reference name.
4. Record the exact package artifact hash, adapter ID/version, service/model deployment declaration, route, retention/logging declaration, timeout, and reviewed wire categories in the private qualification and decision records.
5. Keep live provider probes manual, synthetic, bounded, non-child, and separate from repeatable test runs.

## Implementation tasks

- [ ] Reuse the exact core request/result/status/metadata types; reject unknown fields and version skew.
- [ ] Keep `status()` credential-free, local, idempotent, and non-billable; it must not contact a provider.
- [ ] Resolve credentials only inside the capability worker after authorization and remove them from the environment before importing provider code.
- [ ] Map typed requests to the reviewed minimal wire payload; deny undeclared fields by construction.
- [ ] Enforce adapter-local request/response byte bounds in addition to supervisor deadlines and frame bounds.
- [ ] Convert provider errors to bounded stable reason codes; never return raw bodies, headers, request IDs, prompts, audio, account data, or secret-bearing exceptions.
- [ ] For tutor output, return only bounded structured sentence/citation records; do not stream or display provider output.
- [ ] For additional safety, implement both required input and generated-output harm decisions using the shared taxonomy; inability to decide is fail-closed.
- [ ] For STT, accept only the worker-owned validated managed WAV descriptor and return bounded transcript text; do not retain audio through the adapter.
- [ ] Package each adapter as a non-editable distribution with complete metadata/RECORD hashes and pinned, reviewed transitive dependencies.
- [ ] Generate strict private qualification records with synthetic probes, then require parent-authored capability decisions that point to those exact records/artifacts.
- [ ] Recompute readiness and prove the generated mode remains disabled unless tutor plus mandatory safety both qualify, and voice remains disabled unless STT plus microphone authorization qualify.

## Required tests and evidence

- `status()` works with credentials absent and a network/billing canary proves no side effect.
- Unknown contract version/field, malformed frames, oversized input/output, timeout, worker crash, descendant leak, and provider error all fail closed.
- Captured fake wire requests contain exactly the reviewed `data_sent` fields and no answer key, raw rejected learner input, parent token, credential, provider exception, or telemetry object.
- Tutor citations/records traverse the normal deterministic output-policy, grounding, and mandatory harm gates before display.
- Additional safety cannot relax a deterministic denial; timeout/error/unsafe result selects authored fallback and circuit-breaks generated tutoring.
- STT receives only validated worker-owned WAV, and every success/failure/cancel/timeout path proves managed cleanup.
- Built wheel/sdist identity and dependency RECORD verification reproduce the readiness artifact hashes.
- One manual synthetic smoke per selected real service proves the exact adapter/decision/qualification binding without child data.
- Fallback-only launch still works when all adapter decisions are disabled.

## Acceptance

- The core app imports no provider package.
- Credentials cross neither UI state nor supervisor protocol.
- `generated_tutor` eligibility is possible only with real qualified tutor and mandatory safety adapters.
- `generated_tutor_voice_input` eligibility additionally requires real qualified STT, managed-media qualification, and the token-guarded parent microphone enable action.
- If any adapter is unavailable, the exact lower eligibility level and authored fallback are parent-visible; no fake satisfies a child-pilot claim.

## Non-goals

- Choosing a provider/model before the manual review
- Automatic account creation, secret provisioning, or billing changes
- Cloud deployment
- Provider failover or model routing
- Sending real child/family data during qualification
