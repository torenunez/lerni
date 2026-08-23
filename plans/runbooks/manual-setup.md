# Explore Safe Slice — Manual Setup, Accounts, and Credentials

## Purpose

This runbook covers operator work that cannot be completed safely by code alone. It applies before implementation qualification, before each capability is enabled, and before a child pilot.

The baseline local slice requires no cloud account, API key, hosted Gradio account, Google account, tutor service, speech service, or deployment service. Manual tutor fallback, typed input, reviewed content, local SQLite, and visible text remain usable without them.

## Setup decision record

Keep a private operator record outside the repository and outside child-facing content. For each optional capability record:

- capability: tutor, speech-to-text, additional safety, browser speech, or spreadsheet editor;
- selected adapter ID/version and installation source;
- local or external data route;
- exact data sent;
- declared retention, logging, training use, region, and deletion behavior;
- account owner role;
- terms/privacy review date;
- credential logical name and source environment-variable name, never the value;
- billing limit, usage quota, and alert configuration;
- key rotation/revocation procedure;
- qualification result and readiness-report digest;
- parent decision: enabled, disabled, or blocked pending clarification.

Do not record child names, raw child text/audio, secrets, key suffixes, or account recovery data.

## Required local setup

- [ ] Use Python 3.11 or newer in an isolated project environment.
- [ ] Confirm the repository’s existing Study tests and working-tree state before installation.
- [ ] Install only the dependency profile required by the current PR.
- [ ] Create an absolute runtime root outside the repository.
- [ ] Set owner-only runtime-root permissions where the platform supports them.
- [ ] Confirm the root is not a symlink and is not cloud-synced.
- [ ] Use a parent-controlled OS account and full-disk encryption where practical; identify backups/snapshots that managed wipe cannot reach.
- [ ] Use a current browser and verify the local Gradio server binds only to `127.0.0.1`.
- [ ] Use a dedicated minimal browser profile with account sync/history extensions disabled for the pilot.
- [ ] Disable public sharing, tunnels, and hosted notebook proxying.
- [ ] Keep the child device/session free of unrelated personal information.
- [ ] Copy `examples/explore-runtime-fallback.toml` to an owner-only location outside the repository, replace the runtime root/reviewed settings, and keep credential references—not values—only.

The application creates derived runtime children; it does not create or change the operator-owned root.

## Optional tutor or additional-safety service account

No account is required when manual authored fallback and deterministic policy are selected.

Before enabling an external service:

1. Confirm the service permits the intended parent-supervised processing of a child’s text. Parent consent does not override service terms, age restrictions, or applicable law.
2. Review whether submitted data is retained, logged, used for training, reviewed by humans, or transferred to another region/subprocessor.
   Treat submitted “sanitized” text as best-effort pseudonymized, not anonymous; missed identifiers or distinctive wording can remain identifying.
3. Create a parent-owned project/workspace dedicated to this family prototype.
4. Enable multi-factor authentication.
5. Configure the lowest practical billing cap, quota, and usage alerts.
6. Create a capability-specific, least-privilege credential if the service supports scopes.
7. Record the revocation path and test that the parent can revoke it.
8. Install the provider-specific adapter separately; core Lerni code must remain provider-neutral.
9. Configure only a credential reference in the runtime profile:

```toml
[capabilities.tutor.credential_refs]
api_key = "env:LERNI_TUTOR_API_KEY"
```

10. Place the value in a launch-scoped environment through a trusted secret manager or non-echoing shell input. Never paste it into TOML, source, tests, `.env` committed to Git, chat, issue, PR, terminal command history, or spreadsheet.
11. Run synthetic qualification before any child input; atomically write the strict generated `<kind>.qualification.json`, then review/write the separate `<kind>.json` operator decision that pins its hash.
12. For generated tutor use, qualify the separate mandatory input/output harm gate against the exact installed 56-case v1 fixture from `specs/03b-harm-probe-cases.md`; any missing, blocked-benign, allowed-harmful, timeout, or drifted case disables generated mode.
13. Keep the capability disabled if any route, retention, logging, training, age-use, deletion, or harm-gate answer is unknown.

Qualification must show that `status()` is credential-free, local, idempotent, and non-billable. An adapter that pings a provider from status is ineligible; real provider contact occurs only in an explicitly approved operational/probe call and is disclosed/countable.

When disabling a previously configured plugin, move its decision/qualification records to a private archive outside active `capability-decisions/`; bootstrap rejects inactive or unknown files there to avoid ambiguous readiness.

For a local tutor/safety adapter, record package/artifact source, version/hash, license, hardware/disk needs, and whether it makes any network call. A “local model” label is not proof of no network or no logging.

If no compatible adapter already exists, implement it as a separate environment-specific package/change against the core plugin protocol. A generated-tutor pilot needs both tutor and additional-safety factories (one distribution may provide both); a voice-input pilot separately needs STT. Build/install a non-editable distribution with complete metadata/RECORD, pin its artifact hash, keep provider/model dependencies out of core, and do not treat fake-backend test success as a real capability qualification.

## Optional speech-to-text setup

Typed input remains the mandatory freeform fallback during `INTRO`/`TEACH`; deterministic retrieval uses authored choices/hints. Browser microphone permission alone does not qualify speech-to-text.

For an external STT account, repeat the account/credential steps above and additionally:

- confirm the service permits child voice processing;
- treat raw voice as potentially identifying and unsanitized because audio is routed before transcript policy can run;
- review audio and transcript retention separately;
- determine whether audio is used for product improvement or training;
- set the smallest practical request/audio limits;
- verify deletion/revocation instructions;
- run only synthetic WAV fixtures during qualification;
- obtain both parents’ explicit decision before first child audio.

For a local STT adapter:

- record package and speech-artifact versions/hashes/licenses;
- confirm whether first use downloads files or contacts a registry;
- pre-download and verify artifacts before the child session;
- qualify supported WAV sample widths/rates/channels;
- verify managed audio cleanup on success, timeout, crash, and malformed output.

Do not claim local processing until network observation and adapter review support that claim.

## Browser speech and microphone permissions

Browser speech output needs no Lerni service account, but browser/OS routing may be local or external. Review the actual browser/OS behavior before describing it to parents.

- [ ] Read-aloud starts disabled.
- [ ] Text remains visible when speech is unavailable.
- [ ] The browser requests microphone access only after a parent enables audio.
- [ ] Permission is limited to the local origin where the browser supports it.
- [ ] Qualify the selected Gradio/browser WAV capture or conversion path, including any media executable, and verify all server-side intermediates stay under the managed private temp root.
- [ ] Revoke browser microphone permission after the pilot if it is no longer needed.

## Google Sheets or local spreadsheet setup

Google Sheets is optional. The normative input is a local, versioned CSV bundle.

If using Google Sheets:

1. Use a parent-controlled account with multi-factor authentication.
2. Create a private workbook; disable link/public/domain-wide sharing.
3. Share only with the consenting parent/educator roles that need to edit or review.
4. Do not install add-ons, Apps Script, external connectors, or automatic AI features for this workbook.
5. Do not enter child name, account ID, school, address, contact details, raw transcript/audio, medical/diagnostic labels, secrets, or credentials.
6. Treat spreadsheet validation/protection as editing convenience, not an approval or security boundary.
7. Export tabs manually as UTF-8 CSV.
8. Inspect for formulas before setting `formula_free_attested=true`.
9. Validate and hash locally; never let the running child app read the live sheet.
10. Treat Google revision history, sync copies, trash, backups, and provider retention as outside Lerni’s managed wipe; review/accept that boundary or use a local editor.

No Google Cloud project, OAuth client, service account, API key, or Sheets API enablement is needed. Automatic synchronization remains deferred.

For maximum privacy, use a local CSV-capable editor. Keep the filled family copy under `runtime.root/curation-private/` if it must be covered by managed wipe; any other non-synced directory requires separate manual deletion.

## Credential handling contract

- Runtime TOML stores `env:VARIABLE_NAME` references only.
- The helper subprocess receives only standardized credential variables required by its capability.
- A missing credential disables only that optional capability.
- Parent code never puts credential values in IPC requests, readiness, telemetry, exports, SQLite, logs, exceptions, screenshots, or sheets. Exact plugin reflection is rejected and triggers rotation, but trusted/malicious plugin code is not a sandbox and transformed leakage cannot be ruled out.
- Do not verify leakage by searching for a real secret value in a shell command; use a synthetic canary credential in tests.
- Rotate immediately after suspected disclosure.
- Revoke optional service keys when the pilot ends if continued access is unnecessary.

## Pre-launch manual gate

- [ ] Both parents still consent to the specific enabled data routes.
- [ ] Required content/review attestations are real and current.
- [ ] Runtime profile contains no values that resemble credentials.
- [ ] Every enabled plugin has a passing synthetic qualification.
- [ ] Helper timeout, descendant cleanup, and forced parent-process-death containment pass on this operating system.
- [ ] The strict private framework qualification record is `pass`, has zero canary occurrences, and matches the installed framework/platform/probe hashes.
- [ ] Browser/server network inspection with speech and external plugins off shows no non-loopback framework asset, analytics, telemetry, update, or callback request.
- [ ] External declarations and unresolved limitations are visible.
- [ ] Local telemetry retention is selected.
- [ ] Export and session delete were exercised with synthetic data; managed local family-data wipe was exercised using the current parent token plus exact phrase `DELETE ALL MANAGED LOCAL FAMILY DATA`.
- [ ] `--print-readiness` was reviewed.
- [ ] The exact readiness digest was acknowledged before browser launch.
- [ ] Parent token is available to the supervising parent and absent from browser storage/logs.
- [ ] Browser password saving/autofill is off; if a launch code/token is pasted, clear the OS clipboard immediately and remember clipboard history is outside managed wipe.
- [ ] One parent remains present and can stop immediately.

## Post-session manual steps

- Review only sanitized local records.
- Delete or retain the session under the selected policy.
- Confirm managed audio temp is empty.
- Close the child browser tab/profile.
- Clear or close the launching terminal if desired; the app cannot reliably erase terminal scrollback.
- Revoke microphone permission when no longer needed.
- Review external provider dashboards for unexpected usage without uploading child data.
- Request/confirm provider deletion when available, or record the declared retention-expiry date and explicitly accept the residual when deletion cannot be verified.
- Reconfirm training-use opt-out/account setting after the session when an external service was used.
- Revoke or rotate temporary credentials.
- Remove launch-scoped credential variables from the parent shell/secret-manager session.
- If the private workbook is no longer needed, remove collaborators, delete the Google Sheet and trash copy, and delete exported/synced/downloaded CSV copies from every known device/location.
- Record only structured, sanitized pilot observations.

## Blockers

Do not enable the affected capability or run the child pilot when:

- service terms or child-data handling are unclear;
- retention/logging/training route is unknown;
- a credential appears in a file, log, report, command history, or spreadsheet;
- localhost-only launch cannot be demonstrated;
- raw framework text persistence cannot be bounded;
- audio cleanup fails;
- required content reviews are missing;
- the readiness report differs from what the parent approved.
