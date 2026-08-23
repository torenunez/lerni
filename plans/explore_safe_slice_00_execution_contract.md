# Explore Safe Slice — Execution Contract

## Purpose

This file defines the conditions under which the remaining implementation plans may be executed. It is intentionally portable: a human developer, a basic shell-driven automation, or an IDE workflow should all be able to follow it without access to any named coding agent, model, provider, credential store, or orchestration product.

The implementation target is a parent-supervised, local Gradio application that:

- preserves the existing Study CLI as maintenance-only;
- presents one reviewed acceleration lesson;
- keeps lesson progression deterministic and application-owned;
- permits a configured text-generation capability to phrase bounded responses;
- provides a curated visual and optional browser read-aloud;
- adds push-to-talk through a separately qualified speech-to-text capability;
- stores only data-minimized local telemetry under parent control;
- makes no commit.

## Normative technical plan set

These files define the technical contracts:

1. [Runtime profile and bootstrap](./explore_safe_slice_00a_runtime_bootstrap.md)
2. [Documentation alignment](./explore_safe_slice_01_documentation.md)
3. [Lesson domain and content](./explore_safe_slice_02_lesson_core.md)
4. [Safety, grounding, and tutor boundary](./explore_safe_slice_03_safety_tutor.md)
5. [Normative policy algorithms](./explore_safe_slice_03a_policy_algorithms.md)
6. [Local telemetry and parent controls](./explore_safe_slice_04_telemetry.md)
7. [Gradio UI, curated visual, and read-aloud](./explore_safe_slice_05_gradio_ui.md)
8. [Push-to-talk audio input](./explore_safe_slice_06_audio_input.md)
9. [First-slice verification and supervised pilot](./explore_safe_slice_07_verification.md)
10. [Portable curation workbook and early graph](./explore_safe_slice_08_graph_recommendations.md)
11. [Curriculum persistence](./explore_safe_slice_08a_curriculum_persistence.md)
12. [Recommendation and feedback](./explore_safe_slice_08b_recommendation_feedback.md)
13. Rerun the graph-specific and full-regression sections of the verification plan after graph/recommendation implementation.

The [master PR index](./explore_safe_slice_62964d1d.plan.md) owns execution order and gates. The [manual setup](./explore_safe_slice_manual_setup.md) and [private data priming](./explore_safe_slice_data_priming.md) runbooks own operator-only work.

Runtime-profile/path/process primitives are PR-03; complete `build_application()` is PR-06 after lesson, tutor, telemetry, and UI interfaces exist. Graph and recommendation extensions occur only in PRs 10–11.

The master index is [Explore Safe Slice](./explore_safe_slice_62964d1d.plan.md).

## Authority and conflict resolution

When requirements disagree, use this order:

1. Explicit user decisions recorded in the master plan.
2. This execution contract and the detailed technical plans.
3. PR files for decomposition/sequence.
4. Existing repository documentation.

Desktop drafts used during planning are historical research only. They are not required execution inputs. Any still-needed decision or fact must be represented in this plan set or a repository-relative reviewed artifact before implementation.

Do not silently reconcile a conflict by guessing. Record the conflict, apply the higher-authority requirement, and update every affected plan or document together.

## Portability rules

The implementation plans must not assume:

- an AI coding agent or subagent exists;
- a particular planning, memory, review, or orchestration tool exists;
- a particular language model, model identifier, provider, API shape, or SDK exists;
- a credential is present;
- an external moderation endpoint exists;
- a speech-recognition model or package is installed;
- a GPU, Apple-specific accelerator, CUDA runtime, or particular CPU exists;
- network access is available;
- the current filesystem layout exists outside the repository and operator-selected runtime directory.

The plans may assume only:

- Python 3.11 or newer, because that is already the project floor;
- the repository can be read and edited;
- a Python environment can install or expose the dependencies selected during qualification;
- parents are present for the family-only pilot.

Provider-specific implementation belongs behind capability interfaces. Environment-specific values belong in an operator-owned runtime profile, not in committed lesson data, tests, or product requirements.

A modern browser is required only for the optional local-UI qualification and family pilot. Its absence does not block headless lesson, policy, telemetry, or packaging work.

## Command variables

Before executing any command in the subplans, bind and record:

- `REPO`: absolute repository root.
- `PYTHON`: exact Python executable.
- `PACKAGE_INSTALL`: exact editable-install command for the qualified environment.
- `RUNTIME_PROFILE`: absolute path to the strict operator-owned profile.

Never encode secrets in these values, the plan files, shell history, test fixtures, telemetry, or exported session data.

Subplans invoke test/lint/type modules through `"$PYTHON" -m ...`. If an environment uses an equivalent tool that cannot be invoked as a module, record a shell argument vector and substitute it consistently; do not store a multi-word command in a single quoted scalar.

## Step 0 — Preserve the starting state

Before editing:

1. Confirm the repository root.
2. Capture `git status --short --branch`.
3. Capture `git diff --` for all tracked changes.
4. List untracked files.
5. Record that the starting branch may be `main` and that the user explicitly requested no commits.
6. Do not stash, reset, clean, checkout, amend, or overwrite the current uncommitted files.
7. Treat these starting files as user work that must survive:
   - `.claude/`;
   - `CLAUDE.md`;
   - `docs/roadmap.md`;
   - `docs/spec.md`;
   - `docs/todo.md`.

If the working tree differs from the captured baseline by the time implementation begins, re-read affected files and merge deliberately.

## Step 1 — Qualify the core environment

Run a small read-only probe or equivalent checks to verify:

- `sys.version_info >= (3, 11)`;
- `dataclasses`, `enum.StrEnum`, `importlib.resources`, `sqlite3`, `tomllib`, `typing.Protocol`, and `wave` import;
- the repository package can be imported from an editable install;
- a wheel and source distribution can be built in the available packaging setup;
- temporary files can be created and removed under the parsed profile’s derived runtime root;
- tests can run without network access or credentials.

Stop before implementation if any standard-library requirement fails.

## Step 2 — Qualify the UI framework

The product decision fixes Gradio as the first UI, but not a specific installed version.

This is optional Tier B qualification. Its failure blocks the Gradio UI and child pilot, not the headless core.

The selected Gradio version must demonstrate these capabilities in a minimal throwaway probe:

- a `Blocks` application can be constructed;
- per-browser state is available;
- chat messages support explicit user and assistant roles;
- buttons, radio choices, text input, and hidden structured state can be wired;
- launch can bind to `127.0.0.1` with public sharing disabled;
- output can be returned as one complete string rather than token streaming;
- browser JavaScript can receive a structured speech command after a Python callback.

Microphone recording is a separate Tier D probe performed only for the audio phase:

- recorder can be microphone-only;
- WAV output can be bounded;
- framework temporary files are placed under the managed root;
- no queue/cache/log persists raw audio outside that root;
- completion reaches a Python callback without auto-submission.

Record the qualified Gradio version, exact resolved transitive distribution/RECORD identities (or hash-pinned environment lock/constraints artifact), and exact API differences in the execution log. A project version range alone is not reproducible. If the available version cannot meet required UI controls, revise only the UI-specific plan; do not weaken localhost, non-streaming, state isolation, or data-handling requirements. If only microphone requirements fail, disable microphone and continue with typed input.

## Step 3 — Qualify capability adapters

### Tutor capability

A tutor implementation is acceptable only if it structurally satisfies the protocol defined in the safety/tutor plan and passes a contract test with a fixed request.

Qualification must record:

- adapter identifier and version;
- whether processing is local or external;
- what child text leaves the machine;
- explicit retention and logging declarations;
- credential source without recording the credential;
- timeout behavior;
- maximum response size;
- whether complete output can be buffered before display;
- how errors are mapped to a typed failure;
- confirmation that the interface does not pass lesson-engine or telemetry objects to the adapter.

Capability plugins run only in the helper subprocess, but remain trusted operator-selected code that could access other local resources. Qualification does not claim sandboxing.

If no tutor adapter qualifies:

- engineering and deterministic lesson tests continue with `ManualTutor`;
- the UI remains usable with authored text;
- the generated-tutor portion of the child pilot is blocked;
- documentation must say “tutor capability unavailable,” not imply generation was exercised.

An enabled child-facing plugin with `unknown` routing, retention, or logging fails qualification and is treated as unavailable. Unknowns may be investigated in an operator-only probe, but parent acknowledgement does not convert missing metadata into qualification.

### Additional safety capability

An external safety classifier is optional. If present, it may tighten an app-owned decision but must never turn `redirect`, `block`, or `escalate` into `allow`.

No external safety capability is required to run tests. Its absence must not disable deterministic policy.

### Speech-to-text capability

A speech-to-text implementation is acceptable only if it:

- satisfies the protocol in the audio plan;
- accepts a bounded local recording path;
- returns text plus optional language metadata;
- has a finite timeout;
- emits no raw audio or transcript to application logs;
- does not own deletion of the recording;
- maps implementation errors to a sanitized typed failure;
- declares whether audio leaves the machine and any retention behavior.

If none qualifies, microphone controls remain disabled and typed freeform input remains functional in the lesson phases that permit it.

### Speech output capability

The initial output capability is browser speech synthesis when available. It is runtime-detected, disabled by default, and never required for access to the visible text.

No named voice, operating system, or local-only guarantee may be assumed.

## Step 4 — Create the runtime profile and bootstrap

Follow the exact schema, derived paths, capability metadata, trust boundary, helper-process deadline, parent token, and bootstrap contract in [Runtime profile and bootstrap](./explore_safe_slice_00a_runtime_bootstrap.md).

Tests parse in-memory TOML and deterministic test plugins. They do not read the operator’s live profile or credentials.

## Step 5 — Test discipline

For every behavior change:

1. Name the production defect that the test would catch.
2. Write one failing behavior test.
3. Run only that test and confirm it fails for the intended missing behavior.
4. Implement the smallest production change.
5. Run the same test and confirm it passes.
6. Run the containing test file.
7. Refactor only while green.
8. Run the relevant subsystem suite before starting the next subsystem.

Tests must:

- assert observable behavior rather than source text;
- derive expected values independently;
- exercise real pure logic and SQLite where practical;
- fake only external, slow, browser-only, microphone, or unavailable capabilities;
- never call a live model, speech service, or network endpoint;
- use unique canary values to prove sensitive content did not cross a boundary.

Scaffold an importable empty module/API before adding behavior tests. A missing-module import error does not prove a domain invariant, validation rule, or transition is absent; each recorded red test must fail on a behavior-specific assertion.

## Global stop conditions

Stop implementation and report the evidence when:

- a proposed edit would overwrite pre-existing user work;
- a test cannot be made to fail for the intended reason;
- child-facing content has not received explicit human approval;
- no tutor adapter qualifies but an LLM pilot is about to begin;
- a safety failure would expose raw rejected content;
- a child microphone pilot is about to run but audio cannot be reliably bounded and removed;
- the app exposes a public/share URL;
- telemetry stores raw blocked text, child names, audio, credentials, arbitrary JSON, or exception details;
- the Study CLI or database schema changes unexpectedly;
- full verification repeatedly fails for reasons introduced by Explore;
- the only path forward requires a commit.

## Definition of implementation-ready

This plan set is ready to execute when:

- all linked subplans exist and agree on type names and file paths;
- the repository workspace is open;
- the starting git state has been captured;
- command variables have been bound;
- the required Tier A core environment has passed qualification;
- no unresolved choice affects the domain, safety, telemetry, or UI contracts.

The UI, browser speech, tutor, and speech-to-text tiers may remain unavailable while core implementation proceeds. Each must be selected and qualified before its corresponding child-facing capability is claimed.
