# PR-03 — Runtime Profile and Capability Process Boundary

## Goal

Add strict provider-neutral runtime configuration, private path derivation/process lock, credential references, bounded helper-subprocess IPC, capability status metadata, local-admission/parent guards, and code/config/setup-bound readiness data types. Full application assembly waits for PR-06.

## Depends on

- PR-02 lesson/build identity. Tutor/safety codecs are added in PR-04 and STT codecs in PR-07.

## Normative plans

- [Execution contract](../specs/00-execution-contract.md)
- [Runtime profile and bootstrap](../specs/00a-runtime-bootstrap.md)
- [Manual setup](../runbooks/manual-setup.md)

## Files

Create:

- `src/lerni/explore/contracts.py`
- `src/lerni/explore/runtime_config.py`
- `src/lerni/explore/capability_runner.py`
- `src/lerni/explore/capability_supervisor.py`
- `src/lerni/explore/capability_worker.py`
- `src/lerni/explore/readiness.py`
- `examples/explore-runtime-fallback.toml` with the exact disabled-capability schema and an intentionally invalid absolute-root placeholder
- focused runtime/runner/readiness tests

Create only the parent guard and assembly-independent bootstrap primitives needed by later PRs. PR-06 creates the complete `ApplicationBundle` and launch path.

PR-03 defines strict hash/input schemas and canonical hashing with synthetic fixtures only. PR-04 supplies the installed policy/probe identities; PR-06 supplies the installed framework qualification command/record and first complete `LaunchReadinessReport`. PR-03 does not require Gradio or a real `framework.json`.

## Manual prerequisites

- [ ] Select an absolute private runtime root outside the repository.
- [ ] Qualify the Python executable used for helper subprocesses.
- [ ] Decide fallback-only versus optional plugin qualification.
- [ ] If a plugin needs a service credential, complete the account/credential review in the manual setup plan.

The fallback-only profile requires no account or key.

## Implementation tasks

- [ ] Add exact immutable capability metadata/status/enums.
- [ ] Write strict runtime-profile parser tests before parser behavior.
- [ ] Add a bounded no-follow owner-private profile-file loader and revalidate it during fresh readiness computation.
- [ ] Reject unknown keys, unsafe host/path/permissions, secret values, invalid declarations, and invalid credential references.
- [ ] Derive all mutable paths under the existing operator-owned root.
- [ ] Add the secret-free fallback profile example; instruct operators to copy it outside the repository and replace only reviewed values/references.
- [ ] Create missing child directories privately without creating/changing the root.
- [ ] Require owner-only root/DB files and hold one exclusive runtime lock before any store.
- [ ] Implement `env:VARIABLE_NAME` references without resolving values during parsing.
- [ ] Implement fixed frame grammar plus shared status/error codecs; leave operation payload codecs to their owning PRs.
- [ ] Launch a blocking minimal supervisor without a shell; only after atomic registry admission may it spawn `python -I -m lerni.explore.capability_worker`.
- [ ] Pass a minimal environment plus only standardized referenced credentials.
- [ ] Redirect plugin stdout/stderr away from protocol output.
- [ ] Enforce frame bounds, schema, invocation ID, operation/kind pair, semantic limits, deadline, terminate/kill/join, and cleanup.
- [ ] Add an epoch-scoped helper process-group registry with race-safe cancellation for Stop/Reset/Delete/wipe.
- [ ] Add qualified supervisor/worker lifetime channels and out-of-group watchdog behavior that kill the full worker group on parent or supervisor death.
- [ ] Add only the contract-neutral `ProcessCapabilityClient` for status/framing/supervision; typed tutor/safety/STT adapters belong to PR-04/07.
- [ ] Implement parent token issue/verify/rotate with in-memory constant-time comparison.
- [ ] Implement one-time child admission/nonce plus launch/session/capability-call budgets.
- [ ] Implement strict generated capability-qualification records, separate operator decision records that pin them, and generic canonical build/dependency/profile/setup hash primitives; leave policy/framework input finalization to PR-04/06.

## Required concrete tests

- Missing runtime root is rejected and never created.
- Relative/symlink/insecure/multi-link/oversized/replaced profile files are rejected without echoing content.
- Existing private root with absent children succeeds; symlink/insecure child fails.
- Literal credential values and secret-like settings fail; valid references parse.
- Missing referenced value disables only that capability.
- Real subprocess round-trips shared status/error envelopes; PR-04/07 add tutor/safety/STT operation round-trips.
- Malformed prefix/JSON, duplicate key, trailing bytes, wrong ID/kind/schema, oversize, timeout, crash, and metadata drift fail with fixed sanitized codes.
- Barrier tests prove cancellation cannot miss a just-created helper and stale unregister cannot remove a newer invocation.
- Forced parent/supervisor death and cancellation at every spawn/register/group-report barrier remove a hanging worker and descendant; unsupported containment makes operational plugins unavailable.
- Helper receives the expected synthetic credential and no unrelated environment canary.
- STATUS receives no credential and a network-observed side-effecting/billable status fixture fails qualification.
- Synthetic secret is absent from parent request/status/readiness/output/error; exact plugin reflection is rejected and disables capability.
- Readiness digest is independently reproducible and changes for every displayed decision field.
- Exact v1 readiness rejects missing/extra/wrong-version fields; later STT population changes only existing capability collections, not the v1 shape.
- Application-build hash changes for an Explore editable-source mutation; dependency hash changes for a RECORD/file mutation, and editable/unrecorded third-party capability distributions are rejected.
- Initial admission and parent-authorized reset grants are one-time, epoch-bound, and share the exact per-launch session budget.

Run:

```bash
"$PYTHON" -m pytest tests/explore/test_runtime_config.py -q
"$PYTHON" -m pytest tests/explore/test_capability_runner.py -q
"$PYTHON" -m pytest tests/explore/test_readiness.py -q
```

## Acceptance

- Core runtime accepts no credential value.
- Plugin code never loads in the parent process.
- Deadline/cleanup behavior is proven with real subprocesses.
- Fallback-only configuration works.
- No provider/model/service name is embedded.

## Out of scope

- Concrete tutor or STT provider adapter.
- Complete app bootstrap/Gradio launch.
- Live external network calls.
- Graph/recommendation fields.
- Commit, push, or PR creation.
