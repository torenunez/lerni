# PR-04 — Deterministic Safety, Grounding, and Tutor Service

## Goal

Route sanitized in-scope child text through an optional tutor capability, then accept only short structured output grounded in the current reviewed lesson context. Manual authored fallback must work with no service.

## Depends on

- PR-02 lesson context/snapshots.
- PR-03 capability contracts and process wrappers.

## Normative plans

- [Safety, grounding, and tutor boundary](../specs/03-safety-tutor.md)
- [Normative policy algorithms](../specs/03a-policy-algorithms.md)
- [Normative harm-probe fixture](../specs/03b-harm-probe-cases.md)
- [Manual capability setup](../runbooks/manual-setup.md)

## Files

Create:

- `src/lerni/explore/plugin_loader.py`
- `src/lerni/explore/qualification.py`
- `src/lerni/explore/tutor_process.py`
- `src/lerni/explore/policy.py`
- `src/lerni/explore/sanitization.py`
- `src/lerni/explore/grounding.py`
- `src/lerni/explore/tutor_service.py`
- `src/lerni/explore/policy_data/policy_cases_v1.toml`
- `src/lerni/explore/qualification_data/harm_probe_cases_v1.toml`
- deterministic fakes, golden fixtures, and focused tests

Extend `contracts.py` and process codecs only through the exact shared types.

## Manual prerequisites

- No account is required for `ManualTutor`.
- Any tutor/harm-gate adapter must pass the account, terms, routing, retention, logging, credential, quota, and synthetic qualification gates; generated tutor use requires both.
- No child input may be used for qualification.

## Environment-specific capability realization

This core PR may complete in fallback-only mode, but that does not deliver an LLM pilot. Before PR-08 can report `generated_tutor`, the implementation environment must either install an already reviewed compatible plugin distribution or implement one in a separate provider-specific adapter change/package. It may expose tutor and safety factories from one recorded distribution, but each factory has its own status, metadata, qualification, decision, deadline, and failure path. Provider SDKs/endpoints and their tests stay outside core contracts/dependencies; build a non-editable recorded artifact, use only synthetic probes in repeatable tests, and keep any live operator probe manual and child-data-free.

## Implementation tasks

- [ ] Scaffold exact policy/tutor types and fake backends.
- [ ] Add the complete installed normalization/token/phrase/regex/number/sentence/precedence golden resource before policy code; tests and readiness hash those same bytes.
- [ ] Implement best-effort redaction with fixed markers and explicit limitations.
- [ ] Withhold all non-allow raw input from display/storage/tutor.
- [ ] Add bounded serious-distress, secrecy/relationship, instruction-override, and scope checks.
- [ ] Add output markup/Unicode/contact/personal-data/relationship/dependency/coercion/meeting checks.
- [ ] Implement `ManualTutor` as unavailable generation plus lesson-authored fallback.
- [ ] Implement child-process-only plugin loaders and qualification through process wrappers.
- [ ] Build minimal `TutorRequest` from sanitized text and current context only.
- [ ] Validate citations, significant-term traceability, exact allowed numbers, sentence count, and output length.
- [ ] Allow the harm gate only to tighten; operational failure uses fallback and circuit-breaks generated tutoring for the launch.
- [ ] Keep generated tutor disabled unless the required input/output harm-gate taxonomy and benign controls qualify.
- [ ] Label readiness `disabled_authored_fallback` and expose no generated-call path when either tutor or mandatory additional safety is absent/degraded.
- [ ] Ensure tutor output never becomes an engine event or answer grade.

## Required concrete tests

- Every golden input/output phrase/regex has an exact expected action/reason plus a neighboring benign counterexample.
- Fake tutor call count is zero for every redirect/block/escalation/limit.
- CHECK/HINT/COMPLETE phase requests create no turn and call neither policy nor tutor.
- Raw blocked canary is absent from result, persistable values, captured logs, and fake request.
- Unknown/missing citation, unsupported number, untraceable sentence, markup, Unicode control, too many sentences, and overlength output use authored fallback.
- Rejected draft is absent from returned object and any persistence input.
- Optional safety cannot turn a deterministic denial into allow.
- Output harm block or harm-gate runtime failure prevents every later tutor call until restart/requalification.
- Missing/degraded mandatory additional safety yields an acknowledgement-ready authored baseline, visibly ineligible for generated tutoring, with zero tutor/safety generation calls.
- The installed harm fixture has exactly 56 ordered cases matching the appendix byte-for-byte; every harmful/benign input/output result must match or generated mode is ineligible.
- Manual fallback has explicit `AUTHORED_FALLBACK` outcome.
- No provider SDK/model/credential field appears in core contracts.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_plugin_loader.py -q
"$PYTHON" -m pytest tests/explore/test_qualification.py -q
"$PYTHON" -m pytest tests/explore/test_sanitization.py -q
"$PYTHON" -m pytest tests/explore/test_input_policy.py -q
"$PYTHON" -m pytest tests/explore/test_output_policy.py -q
"$PYTHON" -m pytest tests/explore/test_grounding.py -q
"$PYTHON" -m pytest tests/explore/test_tutor_service.py -q
"$PYTHON" -m pytest tests/explore/test_policy_golden.py -q
```

## Acceptance

- Fallback-only tutor service is fully usable.
- Generated output reaches the caller only after deterministic policy and grounding.
- Generated mode is eligible only when tutor plus mandatory additional safety both qualify against the exact installed 56-case harm/benign fixture; any failure selects `ManualTutor`.
- All rejected text/drafts have explicit non-storage behavior.
- Parent supervision and incomplete-classifier limitations remain documented.

## Out of scope

- General-purpose child moderation.
- Legal/compliance certification.
- Live provider tests in the automated suite.
- State advancement or mastery scoring from generation.
- Commit, push, or PR creation.
