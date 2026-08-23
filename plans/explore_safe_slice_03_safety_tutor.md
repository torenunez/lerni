# Explore Safe Slice — Safety, Grounding, and Tutor Capability

## Goal

Build a provider-neutral boundary in which:

- deterministic application policy examines child input before any tutor call;
- only sanitized, in-scope input reaches a configured tutor capability;
- the tutor receives the current lesson snapshot and reviewed grounding facts;
- tutor output is treated as untrusted, buffered, grounded, and gated;
- rejected output is discarded rather than displayed or stored;
- authored fallback text works without any model or external service;
- no tutor or safety adapter can advance lesson state.

These controls reduce risk but do not make the prototype generally child-safe, legally compliant, or appropriate without active parent supervision.

## File map

Create:

```text
src/lerni/explore/
├── plugin_loader.py
├── qualification.py
├── tutor_process.py
├── policy.py
├── sanitization.py
├── grounding.py
├── tutor_service.py
└── qualification_data/
    └── harm_probe_cases_v1.toml

tests/explore/
├── fakes.py
├── test_contracts.py
├── test_plugin_loader.py
├── test_qualification.py
├── test_sanitization.py
├── test_input_policy.py
├── test_output_policy.py
├── test_policy_golden.py
├── test_grounding.py
└── test_tutor_service.py
```

Extend the PR-03-owned `src/lerni/explore/contracts.py` with tutor/additional-safety request, result, and protocol types; PR-04 does not recreate or replace that module.

No module imports a provider SDK.
Use `from __future__ import annotations` in contract/loader modules so raw plugin protocol types may be declared after loader signatures without runtime-name coupling.

## Capability status

Import `CapabilityAvailability`, `CapabilityCallRegistry`, `CapabilityCallScope`, `CapabilityMetadata`, `CapabilityStatus`, and `PolicyLimits` from the runtime-boundary contract created in PR-03. Add only this shared error:

```python
class CapabilityUnavailableError(RuntimeError):
    pass
```

`adapter_id` identifies a configured plugin implementation, not a model.

## Tutor contract

```python
@dataclass(frozen=True, slots=True)
class TutorRequest:
    turn_id: str
    learner_text: str
    snapshot: LessonSnapshot
    context: LessonContext
    maximum_sentences: int


@dataclass(frozen=True, slots=True)
class TutorSentence:
    text: str
    cited_fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TutorDraft:
    sentences: tuple[TutorSentence, ...]


class TutorBackend(Protocol):
    def status(self) -> CapabilityStatus:
        ...

    def generate(
        self,
        request: TutorRequest,
        *,
        call_scope: CapabilityCallScope | None = None,
        call_registry: CapabilityCallRegistry | None = None,
    ) -> TutorDraft:
        ...


class TutorPlugin(Protocol):
    def status(self) -> PluginStatusPayload:
        ...

    def generate(self, request: TutorRequest) -> TutorDraft:
        ...
```

Contract rules:

- input text is already sanitized;
- context contains only the current snapshot’s approved facts and scope;
- the helper-process runner enforces the configured execution deadline;
- parent-process backends accept null scope/registry only for synthetic qualification; every child-session generate/assess call requires both;
- adapter returns a complete structured draft, never a token iterator;
- adapter exceptions are mapped to a sanitized application exception;
- the interface does not pass lesson engine, answer key, database, telemetry store, runtime profile/secrets, or parent notes;
- adapter does not return state transitions or scores.

An operator-approved plugin is still trusted local code and could access local resources independently. This interface prevents accidental coupling; it is not a sandbox.

## Manual fallback

Implement:

```python
class ManualTutor:
    def status(self) -> CapabilityStatus:
        ...

    def generate(
        self,
        request: TutorRequest,
        *,
        call_scope: CapabilityCallScope | None = None,
        call_registry: CapabilityCallRegistry | None = None,
    ) -> TutorDraft:
        raise CapabilityUnavailableError(
            "Manual tutor has no generation capability."
        )
```

`ManualTutor.status()` is unavailable and names authored fallback. `TutorService` detects that status before generation, never calls `generate()`, and returns `context.grounding.fallback_text` with `AUTHORED_FALLBACK`. It permits deterministic development and UI use without implying a generated tutor responded.

## Portable tutor plugin loading

Implement the generic factory loader in `plugin_loader.py`. These functions run only inside the capability helper process:

```python
def load_factory(import_reference: str) -> Callable[..., object]:
    ...


def load_tutor_backend(
    import_reference: str,
    *,
    settings: Mapping[str, str],
) -> TutorPlugin:
    ...


def load_additional_safety_backend(
    import_reference: str,
    *,
    settings: Mapping[str, str],
) -> AdditionalSafetyPlugin:
    ...
```

Import-reference grammar:

```text
python.module.path:factory_name
```

PR-04 implements `ProcessTutorBackend` and `ProcessAdditionalSafetyBackend` in `tutor_process.py` by composing PR-03's generic `ProcessCapabilityClient`; PR-03 never imports these later-owned protocols. The application parent validates import-reference grammar without importing it, constructs one of those typed adapters, and performs status/probes through the versioned runner protocol. Child-side loading validates:

- one colon;
- absolute dotted module path;
- valid factory identifier;
- callable factory;
- returned object has callable `status` and `generate`;
- additional-safety object has callable `status` and `assess`;
- status call succeeds without generation;
- plugin settings reject secret/key/token/password-like keys;
- import/factory errors become sanitized qualification errors.

This is dependency injection, not a security sandbox. Only operator-approved plugins may be loaded. A raw object returned by these loaders never crosses the child-process boundary.

Use PR-03 `CapabilityQualification` and implement tutor qualification in `qualification.py`:

```python
def qualify_tutor_backend(
    backend: TutorBackend,
    *,
    probe_request: TutorRequest | None = None,
) -> CapabilityQualification:
    ...
```

Qualification verifies the structured metadata from the runtime-bootstrap plan, complete output shape, bounded response, helper-process deadline, sanitized failure behavior, and no secret exposure. Route, retention, and logging are labeled operator/plugin declarations. A probe runs only when explicitly requested.

## Generated-content harm gate

```python
class AdditionalSafetyDisposition(StrEnum):
    CLEAR = "clear"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class AdditionalSafetyResult:
    disposition: AdditionalSafetyDisposition


class AdditionalSafetyBackend(Protocol):
    def status(self) -> CapabilityStatus:
        ...

    def assess(
        self,
        text: str,
        *,
        direction: str,
        call_scope: CapabilityCallScope | None = None,
        call_registry: CapabilityCallRegistry | None = None,
    ) -> AdditionalSafetyResult:
        ...


class AdditionalSafetyPlugin(Protocol):
    def status(self) -> PluginStatusPayload:
        ...

    def assess(self, text: str, *, direction: str) -> AdditionalSafetyResult:
        ...


@dataclass(frozen=True, slots=True)
class HarmProbeCase:
    case_id: str
    direction: str
    category: str
    variant: str
    text: str
    expected: AdditionalSafetyDisposition


def qualify_additional_safety_backend(
    backend: AdditionalSafetyBackend,
    *,
    probe_cases: tuple[HarmProbeCase, ...],
) -> CapabilityQualification:
    ...
```

The direction is validated as `input` or `output`.

The deterministic/manual lesson works without this backend. A generated tutor may be enabled for child use only when this backend qualifies against the reviewed minimum input/output taxonomy: violence/weapons/dangerous acts, self-harm, abuse/exploitation/grooming, sexual content, illegal drugs/crime, hate/harassment, and requests for harmful instructions. Probe cases include obvious, obfuscated, lesson-scope-overlap, and benign neighboring controls in both directions.

The exact reviewed probe set is one bounded installed package resource, `qualification_data/harm_probe_cases_v1.toml`, loaded by both operator qualification and tests. Its complete schema, IDs, texts, and expected dispositions are normative in [Harm-probe fixture appendix](./explore_safe_slice_03b_harm_probe_cases.md): exactly seven taxonomy categories × four variants (`obvious`, `obfuscated`, `lesson_overlap`, `benign`) × two directions, or 56 unique cases. Qualification rejects missing/extra/duplicate/reordered cases or any byte drift from the reviewed resource. Its source hash enters the qualification record; no clean-install check reads `tests/`.

The backend may tighten a decision. It may never change an app-owned redirect, block, escalation, or fallback into allow. If it is missing, unavailable, malformed, times out, or fails any required harm/benign probe, bootstrap selects `ManualTutor` for the child pilot even when a tutor plugin itself qualifies.

It runs through the same helper-process deadline and trusted-plugin limitations as tutor/STT capabilities.

Backend-provided free-form codes are not accepted. The application emits only fixed event codes:

```text
optional_input_block
optional_output_block
optional_safety_unavailable
```

Malformed plugin output or any extra field becomes `optional_safety_unavailable`. Plugin text never enters `TurnResult`, telemetry, logs, or parent/child notices.

`TurnResult.event_codes` contains zero or one value from that exact list. The session service maps it to the one optional `PendingEventRecord` passed to `record_turn_pair`:

- `optional_input_block` → `EventType.POLICY_APPLIED`, identical `value_code`, fixed block decision with `PolicyReason.OPTIONAL_CHECK_BLOCK`;
- `optional_output_block` → `EventType.POLICY_APPLIED`, identical `value_code`, fixed fallback decision with `PolicyReason.OPTIONAL_CHECK_BLOCK`;
- `optional_safety_unavailable` → `EventType.TUTOR_FAILED`, identical `value_code`, no plugin-supplied decision/text.

No dynamic event type or backend code is accepted.

## Policy types

Implement in `policy.py`.

```python
class PolicyAction(StrEnum):
    ALLOW = "allow"
    REDIRECT = "redirect"
    BLOCK = "block"
    ESCALATE = "escalate"
    FALLBACK = "fallback"


class PolicyReason(StrEnum):
    OK = "ok"
    EMPTY_INPUT = "empty_input"
    INPUT_TOO_LONG = "input_too_long"
    TURN_LIMIT_REACHED = "turn_limit_reached"
    PERSONAL_DATA = "personal_data"
    SECRET_OR_CREDENTIAL = "secret_or_credential"
    SERIOUS_DISTRESS = "serious_distress"
    HARMFUL_OR_AGE_INAPPROPRIATE = "harmful_or_age_inappropriate"
    INPUT_RELATIONSHIP_OR_SECRECY = "input_relationship_or_secrecy"
    INSTRUCTION_OVERRIDE = "instruction_override"
    OUT_OF_SCOPE = "out_of_scope"
    URL_OR_CONTACT = "url_or_contact"
    RELATIONSHIP_OR_SECRECY = "relationship_or_secrecy"
    UNSAFE_MARKUP = "unsafe_markup"
    UNSAFE_UNICODE = "unsafe_unicode"
    OUTPUT_TOO_LONG = "output_too_long"
    TOO_MANY_SENTENCES = "too_many_sentences"
    MISSING_CITATION = "missing_citation"
    UNKNOWN_FACT = "unknown_fact"
    UNSUPPORTED_NUMBER = "unsupported_number"
    OPTIONAL_CHECK_BLOCK = "optional_check_block"
    GENERATED_HARM_GATE_REQUIRED = "generated_harm_gate_required"
    GENERATION_FAILURE = "generation_failure"
    INTERNAL_FAILURE = "internal_failure"


class RedactionKind(StrEnum):
    EXPLICIT_NAME = "explicit_name"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    ADDRESS = "address"
    LOCATION = "location"
    SCHOOL = "school"
    AGE = "age"
    IP_ADDRESS = "ip_address"
    SECRET = "secret"


@dataclass(frozen=True, slots=True)
class SanitizedText:
    text: str
    redactions: tuple[RedactionKind, ...]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    action: PolicyAction
    reason: PolicyReason
    safe_text: str
    redactions: tuple[RedactionKind, ...] = ()
    rule_ids: tuple[str, ...] = ()

    @property
    def allows_generation(self) -> bool:
        return self.action is PolicyAction.ALLOW


@dataclass(frozen=True, slots=True)
class InputPolicyAssessment:
    decision: PolicyDecision
    sanitized: SanitizedText | None


@dataclass(frozen=True, slots=True)
class ScopeSpec:
    allowed_terms: frozenset[str]
    allowed_short_replies: frozenset[str]
    redirect_text: str


class GenerationOutcome(StrEnum):
    NOT_CALLED = "not_called"
    GENERATED = "generated"
    AUTHORED_FALLBACK = "authored_fallback"
    FIXED_POLICY_RESPONSE = "fixed_policy_response"


class StorageDisposition(StrEnum):
    SANITIZED_TEXT = "sanitized_text"
    WITHHOLD = "withhold"


@dataclass(frozen=True, slots=True)
class PersistableTurnText:
    content: str
    disposition: StorageDisposition
    action: PolicyAction
    reason: PolicyReason
```

Use the exact PR-03 `PolicyLimits` validation bounds. Safety, grounding, telemetry, UI budgets, and readiness all receive the same immutable instance.

## Sanitization contract

Implement in `sanitization.py`.

```python
def sanitize_text(text: str, *, max_chars: int) -> SanitizedText:
    ...


def persistable_input(
    sanitized: SanitizedText | None,
    decision: PolicyDecision,
) -> PersistableTurnText:
    ...
```

`sanitize_text` has no independent normalization algorithm. It calls the appendix's sole `normalize_policy_text(text, max_chars=...)` implementation, propagates its fixed-code `PolicyNormalizationError`, and only then applies the redactions below to successful normalized text. It performs no second NFKC/control/apostrophe/dash/whitespace pass. `SafetyPolicy.assess_input` owns this call, maps normalization failure to a fixed decision without retaining input, and returns `InputPolicyAssessment`; only an allow decision may have its non-null `sanitized` value passed to a tutor.

Redact:

- email;
- HTTP(S), `www`, and Markdown-link URLs;
- phone-like strings with 7–15 digits;
- IPv4;
- explicit credential labels, bearer values, and high-entropy key-like tokens;
- “my name is,” “call me,” or “I’m called” declarations;
- explicit “I live at/in,” “my address is,” school, and age disclosures.

Use fixed markers:

```text
[REDACTED:email]
[REDACTED:phone]
[REDACTED:name]
[REDACTED:url]
[REDACTED:address]
[REDACTED:location]
[REDACTED:school]
[REDACTED:age]
[REDACTED:ip]
[REDACTED:secret]
```

The mapping is one-to-one and exact: `EXPLICIT_NAME→name`, `EMAIL→email`, `PHONE→phone`, `URL→url`, `ADDRESS→address`, `LOCATION→location`, `SCHOOL→school`, `AGE→age`, `IP_ADDRESS→ip`, and `SECRET→secret`. No generic marker or backend-provided label is accepted.

Do not silently truncate. A dangerous suffix must not disappear.

Storage behavior:

- allowed input stores sanitized text;
- every non-allow action stores only `[WITHHELD:{reason}]`;
- raw rejected text is never returned from `persistable_input`.
- safe app-authored fixed responses and fallbacks are constructed separately as `PersistableTurnText(SANITIZED_TEXT)`; no helper can turn rejected generated text into a persistable value.

Limitations to document:

- unintroduced names are often missed;
- addresses and schools are hard to detect;
- misspellings, slang, coded language, and unsupported languages are missed;
- redaction is best-effort pseudonymization, not anonymity.

## Deterministic safety policy

```python
class SafetyPolicy:
    def __init__(self, limits: PolicyLimits = PolicyLimits()) -> None:
        ...

    def assess_input(
        self,
        text: str,
        *,
        completed_learner_turns: int,
        effective_max_turns: int,
        scope: ScopeSpec,
    ) -> InputPolicyAssessment:
        ...

    def assess_output(self, text: str) -> PolicyDecision:
        ...
```

Input precedence:

1. Raw input over limit: block.
2. Normalized over-limit or unsafe-Unicode normalization failure: block.
3. Empty normalized input: block.
4. Turn limit reached: redirect to parent/end.
5. Serious distress or immediate-danger phrase: escalate to supervising adult.
6. Bounded harmful/age-inappropriate request: redirect to supervising adult and do not generate.
7. Personal data or credential: redirect and do not generate.
8. Relationship/secrecy request: redirect to supervising adult/current lesson.
9. Bounded instruction-override pattern: redirect to current lesson.
10. Out-of-scope content: redirect to current lesson.
11. Allow.

The input scope check:

- tokenizes normalized lowercase words;
- permits exact configured short replies such as `why`, `yes`, and `no`;
- permits input with at least one current scope term;
- redirects otherwise;
- does not attempt general semantic classification.

Output precedence:

1. Reject output over limit.
2. Reject more than the maximum sentence count.
3. Reject bidirectional override/control tricks.
4. Reject HTML tags, Markdown links/images, data URLs, or other active/linked markup.
5. Reject bounded harmful/age-inappropriate content.
6. Reject URLs, contact details, credentials, secrecy requests, requests to meet, or relationship manipulation.
7. Allow.

Fixed responses:

- Serious distress: tell the learner to stop and get the supervising adult now.
- Personal data: say not to share names, addresses, schools, contact details, or secrets.
- Out of scope: return to the current lesson.
- Turn limit: end the activity and invite the supervising adult to continue later.
- Internal/generation/grounding failure: use the lesson-authored fallback.

Never:

- diagnose;
- promise confidentiality;
- claim emergency monitoring;
- imply a human has been notified;
- expose exception or adapter details to the child.

The exact normalization, regular expressions, sentence splitting, stop words, significant-term rule, numeric grammar, and golden fixtures are normative in [Policy algorithm appendix](./explore_safe_slice_03a_policy_algorithms.md). Implementations may be more restrictive only after tests and documentation are updated together.

## Grounding gate

Implement in `grounding.py`.

```python
class GroundingGate:
    def assess(
        self,
        draft: TutorDraft,
        *,
        grounding: GroundingBundle,
        limits: PolicyLimits,
    ) -> PolicyDecision:
        ...
```

For every `TutorSentence`:

- draft has `1..max_generated_sentences` records and each record’s text is exactly one sentence under the normative splitter before joining;
- at least one fact citation;
- every cited ID exists in the current grounding bundle;
- sentence contains at least one normalized significant term from a cited fact’s canonical or child text;
- every numeric token appears in a cited fact’s `allowed_numbers`;
- no more than the sentence and character limits;
- caller supplies the once-joined text separately to deterministic output policy; the grounding gate evaluates the still-bounded typed records/citations.

Normalize numeric forms conservatively:

- Unicode digits to ASCII;
- commas removed only inside digits;
- decimal trailing zeros normalized;
- percent sign and unit boundaries preserved.

Do not perform algebraic equivalence. If two number forms are allowed, author both explicitly.

These checks establish traceability, not semantic entailment. A sentence can cite a fact and still contradict it. Therefore:

- keep generated output short;
- prefer authored fallback when uncertain;
- require parent supervision;
- never use generated output to grade or advance.

## Tutor service

Implement in `tutor_service.py`.

```python
class NoTurnReason(StrEnum):
    EMPTY_INPUT = "empty_input"
    PHASE_UNAVAILABLE = "phase_unavailable"


@dataclass(frozen=True, slots=True)
class TurnResult:
    turn_created: bool
    no_turn_reason: NoTurnReason | None
    learner_decision: PolicyDecision | None
    output_decision: PolicyDecision | None
    generation_outcome: GenerationOutcome
    learner_display_text: str | None
    display_text: str | None
    persistable_learner: PersistableTurnText | None
    persistable_assistant: PersistableTurnText | None
    event_codes: tuple[str, ...]


class TutorService:
    def __init__(
        self,
        tutor: TutorBackend,
        safety: SafetyPolicy,
        grounding_gate: GroundingGate,
        limits: PolicyLimits,
        additional_safety: AdditionalSafetyBackend | None = None,
    ) -> None:
        ...

    def respond(
        self,
        *,
        turn_id: str,
        learner_text: str,
        completed_learner_turns: int,
        lesson_max_turns: int,
        snapshot: LessonSnapshot,
        context: LessonContext,
        call_scope: CapabilityCallScope,
        call_registry: CapabilityCallRegistry,
    ) -> TurnResult:
        ...
```

Exact invariant: a created turn has null `no_turn_reason` and non-null learner decision/persistable pair; a non-created turn has one fixed no-turn reason and null persistable values. Empty input may retain its fixed empty-input policy decision; phase-unavailable has `learner_decision=None` because policy never ran.

Learner display rule:

- allowed input: sanitized learner text;
- every redirect/block/escalation: fixed `Message not shown for privacy or safety.`;
- empty input rejected before a turn is created: `None`.

`learner_display_text` never contains raw rejected input or `PolicyDecision.safe_text`; the latter is the assistant/app response.

For empty normalized input, return `turn_created=False`, `no_turn_reason=EMPTY_INPUT`, null display/persistable fields, `NOT_CALLED`, and a fixed UI notice code. No turn/event row is written and the completed-turn counter does not increment. Every non-empty allow/redirect/block/escalation result in an eligible phase creates exactly one learner/assistant turn pair.

Exact flow:

1. Compute effective turn cap as `min(runtime_policy_max_turns, lesson_max_turns)`.
   - every helper invocation in this turn uses the same required session/epoch call scope and registry;
2. Run `SafetyPolicy.assess_input` once; it performs the sole normative normalization/sanitization and returns the decision plus transient sanitized text.
3. If non-allow:
   - do not call tutor;
   - set `output_decision=None`;
   - return a fixed app-authored response with `GenerationOutcome.FIXED_POLICY_RESPONSE`.
4. Check effective tutor status. If unavailable/manual/circuit-broken, return authored fallback without an additional-safety or tutor generation call.
5. If tutor is available but `additional_safety` is missing, unqualified, unavailable, or degraded, do not call either capability: set a fallback `output_decision` with `PolicyReason.GENERATED_HARM_GATE_REQUIRED`, emit only `optional_safety_unavailable`, return authored fallback, and circuit-break generated tutoring for the launch.
6. Invoke the mandatory generated-content input harm gate exactly once.
   - a harm block becomes a fixed policy response and emits `optional_input_block`;
   - operational/malformed failure preserves the deterministic app decision, emits `optional_safety_unavailable`, returns authored fallback without calling tutor, and circuit-breaks generated tutoring for the rest of the launch.
7. Require the allow assessment's sanitized text to be non-null and create `TutorRequest` from it, snapshot, and current context.
8. Call tutor once through the bounded runner.
9. Validate exact `TutorDraft` structure: bounded record count, one normative sentence per nonblank bounded record, bounded/deduplicated citation IDs, and no unknown fields. On timeout, degraded/unavailable status change, malformed draft, or exception:
   - discard details;
   - return authored fallback;
   - set `GenerationOutcome.AUTHORED_FALLBACK`.
10. Strictly join the validated records once; keep the typed draft only until citation grounding completes and never serialize/persist a second rejected copy.
11. Run deterministic structural/content output policy exactly once, before citation/number grounding.
12. If output policy allows, run `GroundingGate` exactly once with the same constructor-supplied `PolicyLimits`.
13. If both allow, invoke mandatory generated-content output harm safety exactly once.
    - harm block emits `optional_output_block`, returns authored fallback, and circuit-breaks generated tutoring for the rest of the launch;
    - operational/malformed error emits `optional_safety_unavailable`, returns authored fallback, and circuit-breaks generated tutoring for the rest of the launch.
14. Return generated text only after all gates, otherwise authored fallback.
15. Construct persistable values from sanitized learner text and final safe app/generated display text. The rejected draft is not retained in `TurnResult`.

The launch-scoped circuit breaker is monotonic: only process restart plus fresh capability/readiness qualification can re-enable generated tutoring. It updates the in-memory effective capability/fallback state used by parent status and any later freshly computed assignment readiness, without rewriting the signed/hashed qualification decision record. Parent status shows a fixed unavailable category; no plugin exception or draft is exposed.

`TutorService` does not import or accept:

- `DeterministicLessonEngine`;
- `LessonEvent`;
- `LessonTransition`;
- telemetry store;
- Gradio;
- audio.

`respond()` accepts only `LessonPhase.INTRO` or `LessonPhase.TEACH`. `CHECK`, `HINT`, and `COMPLETE` return `turn_created=False`, `no_turn_reason=PHASE_UNAVAILABLE`, null decisions/display/persistables, and `NOT_CALLED` before sanitization, policy/helper calls, display, or persistence; authored choice/hint controls own retrieval and grading.

## Deterministic fakes

Implement in `tests/explore/fakes.py`.

```python
@dataclass
class ScriptedTutor:
    drafts: deque[TutorDraft]
    requests: list[TutorRequest] = field(default_factory=list)

    def status(self) -> CapabilityStatus:
        return CapabilityStatus(
            CapabilityAvailability.AVAILABLE,
            "scripted-test-tutor",
            "deterministic test capability",
            "authored fallback",
            TEST_CAPABILITY_METADATA,
        )

    def generate(
        self,
        request: TutorRequest,
        *,
        call_scope: CapabilityCallScope | None = None,
        call_registry: CapabilityCallRegistry | None = None,
    ) -> TutorDraft:
        self.requests.append(request)
        if not self.drafts:
            raise AssertionError("Unexpected tutor call")
        return self.drafts.popleft()
```

Also implement:

- `FailingTutor`;
- `UnavailableTutor`;
- `FixedAdditionalSafety`;
- every fake method exactly matches its protocol's keyword-only call-scope/registry signature;
- no fake may access network or environment credentials.

## Task 1 — Contracts and fakes

Tests:

- `test_scripted_tutor_returns_drafts_in_order`;
- `test_scripted_tutor_records_exact_request`;
- `test_unexpected_extra_call_fails`;
- `test_request_contains_no_provider_or_credential_fields`;
- `test_request_snapshot_has_no_answer_key`;
- `test_tutor_draft_cannot_construct_lesson_event`;
- `test_manual_tutor_status_is_unavailable`;
- `test_tutor_service_never_calls_manual_generate`;
- `test_tutor_service_returns_authored_fallback_for_manual_tutor`.

Red:

```bash
"$PYTHON" -m pytest tests/explore/test_contracts.py -q
```

Green:

- add only contract dataclasses, protocols, manual tutor, and fakes.

Then add plugin/qualification tests:

- valid tutor factory loads;
- malformed/relative import reference fails;
- missing/non-callable factory fails;
- wrong returned contract fails;
- secret-like setting key fails;
- unavailable tutor remains manual fallback;
- qualification does not generate unless a probe is supplied;
- valid controlled probe passes;
- malformed, unbounded, timeout, and secret-leaking probe fails.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_plugin_loader.py tests/explore/test_qualification.py -q
```

## Task 2 — Sanitization

Tests:

```python
def test_explicit_personal_data_is_redacted():
    result = sanitize_text(
        "My name is CanaryName; email canary@example.test; call 415-555-1212",
        max_chars=500,
    )
    assert "CanaryName" not in result.text
    assert "canary@example.test" not in result.text
    assert "415-555-1212" not in result.text
    assert RedactionKind.EXPLICIT_NAME in result.redactions
    assert RedactionKind.EMAIL in result.redactions
    assert RedactionKind.PHONE in result.redactions


def test_non_allowed_storage_uses_fixed_marker():
    decision = PolicyDecision(
        PolicyAction.ESCALATE,
        PolicyReason.SERIOUS_DISTRESS,
        "Get the supervising adult now.",
    )
    assert persistable_input(
        sanitize_text("SensitiveCanary", max_chars=500),
        decision,
    ) == PersistableTurnText(
        "[WITHHELD:serious_distress]",
        StorageDisposition.WITHHOLD,
        PolicyAction.ESCALATE,
        PolicyReason.SERIOUS_DISTRESS,
    )
```

Add:

- NFKC/control normalization;
- URL/address/school/age/IP/secret redaction;
- no silent truncation;
- allowed storage contains only sanitized output.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_sanitization.py -q
```

## Task 3 — Input policy

Tests:

- empty blocked;
- raw and normalized over-limit blocked;
- turn limit checked before generation;
- distress takes precedence over personal-data redirect;
- personal data prevents generation;
- configured short `why` allowed;
- in-scope acceleration question allowed;
- unrelated prompt redirected;
- secrecy/relationship request redirected;
- bounded instruction-override pattern redirected even when it contains an allowed term;
- optional clear cannot override app block;
- optional block tightens app allow;
- optional check failure does not disable app policy.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_input_policy.py -q
```

## Task 4 — Output policy and grounding

Tests:

- missing citation falls back;
- unknown fact ID falls back;
- unsupported number falls back;
- authored allowed number passes;
- too many sentences falls back;
- URL/contact/personal-data solicitation/secrecy/relationship/dependency/coercion/meeting cues fall back using the exact appendix fixtures;
- HTML/Markdown-link/image and bidirectional-control output falls back;
- exact authored fallback returned;
- raw rejected text absent from result;
- valid two-sentence draft produces joined safe text.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_grounding.py tests/explore/test_output_policy.py -q
```

## Task 5 — Orchestration

Tests:

- blocked input never calls tutor;
- tutor receives sanitized text only;
- tutor receives current step facts only;
- complete draft is gated before return;
- tutor exception returns fallback without internal details;
- unavailable tutor uses authored fallback;
- raw rejected generation absent from display result;
- raw rejected generation absent from every `TurnResult` field;
- raw rejected learner input absent from `learner_display_text`;
- allowed learner display equals sanitized input;
- blocked input has `output_decision is None`;
- authored fallback has explicit generation outcome and persistable safe text;
- harm gate can only tighten;
- generated tutor is unavailable unless every required harmful and benign probe passes;
- lesson-scope words cannot bypass harmful-input/output fixtures;
- plugin-supplied code/text canary is discarded and mapped to a fixed event code;
- tutor result cannot advance lesson;
- same inputs and fake draft produce same `TurnResult`.

Use canary strings and assert they are absent from:

- tutor requests when input is blocked;
- returned output when generation is rejected;
- event codes and exception messages.

Red/green:

```bash
"$PYTHON" -m pytest tests/explore/test_tutor_service.py -q
```

## Runtime adapter qualification tests

Any concrete tutor plugin selected later must pass a shared contract suite:

- status returns without generation;
- no secret appears in status reason;
- request timeout is finite;
- one request yields a complete `TutorDraft`;
- malformed output maps to typed failure;
- adapter does not stream;
- adapter does not mutate request;
- the request object contains no Study engine/state or telemetry reference;
- network behavior and retention are documented by the operator.

These contract tests may run against a local controlled stub. They must not call a live child-facing service in the automated suite.

## Completion criteria

- All deterministic policy tests pass.
- Blocked input cannot reach tutor.
- Rejected output cannot reach caller as child text.
- Tutor cannot advance lesson.
- Manual fallback works.
- No provider SDK or model name appears in core modules or tests.
- Residual limitations are documented.
- No live external call occurs in tests.
- No commit is made.
