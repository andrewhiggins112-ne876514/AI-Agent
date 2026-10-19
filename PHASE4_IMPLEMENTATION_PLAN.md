# Phase 4 Implementation Plan

## Purpose and status

This plan breaks Phase 4 into independently testable increments based on the
current AI-Agent implementation and the proposed backend architecture. It is
an implementation plan, not authorization to change code.

Phase 4 is proposed as an **execution foundation and governed memory** phase.
It should not attempt to implement every backend described in
[PHASE4_EXECUTION_BACKENDS.md](./PHASE4_EXECUTION_BACKENDS.md). Preserve the
Phase 3 sequential task runner, target-awareness behavior, fail-stop
semantics, and honest verification model while introducing new boundaries
incrementally.

The current repository is a Windows/Python prototype with a Tkinter GUI,
direct desktop tools, task execution, foreground snapshots, target
assessment, and transient progress reporting. It does not yet have a
validated configuration system, durable audit store, general permission
policy, memory lifecycle UI, backend router, or UI Automation adapter.

## Recommended implementation order

1. **Phase 4.1 — Core execution contract and foreground adapter**
2. **Phase 4.2 — Configuration, policy, and durable audit**
3. **Phase 4.3 — User-controlled basic memory**
4. **Phase 4.4 — Bounded UI Automation pilot**

Each increment should have its own acceptance gate. Do not start a later
increment while its stated prerequisites are incomplete. If Phase 3 manual
acceptance is outstanding, complete it before changing execution semantics.

## Phase 4.1 — Core execution contract and foreground adapter

### Objective

Create the smallest safe backend foundation while preserving current
behavior: represent an operation, target, backend capability, dispatch
result, and verification result as distinct structured data, then wrap
existing desktop actions as an explicitly foreground-required backend.

### Deliverables

- A versioned, typed operation/request and backend-result contract containing
  only fields needed by current execution, such as operation, validated
  arguments, target, selected backend, focus requirement, dispatch status,
  error, duration, and side-effect summary.
- A minimal backend interface and capability description, including whether
  an operation is supported, requires foreground interaction, and offers
  result read-back.
- An adapter around the existing `pyautogui`/Win32 tool path. Keep the
  existing action names and visible behavior; do not add activation,
  background input, or implicit routing.
- A narrow dispatch boundary in the task runner. Preserve existing
  preflight, target mismatch gating, step/task states, event behavior, and
  `TYPE_TEXT` verification outcome.
- Backend identity and dispatch evidence must remain separate from
  `VerificationResult` and `TargetAssessment`.

### Files affected

Likely implementation files, subject to repository structure at
implementation time:

- `scripts/tools.py` — retain action validation and tool behavior; expose or
  delegate existing operations through the adapter without breaking current
  callers.
- `scripts/task_execution.py` — use the new request/adapter boundary while
  preserving sequential execution and failure behavior.
- `scripts/target_awareness.py` — reuse existing target model; change only if
  a type-compatible integration is necessary.
- `scripts/agent_ui.py` — display selected backend/focus requirement only if
  the new structured event/result requires it.
- New narrowly scoped modules, for example
  `scripts/execution_contracts.py` and `scripts/backends/foreground.py`.
- Existing and new tests under `tests/`, especially
  `tests/test_task_execution.py` and target-awareness tests.

No existing architecture documents need to be changed as part of this
implementation increment unless explicitly requested.

### Dependencies

- Phase 3 task execution and target assessment behavior must be stable and
  covered by tests.
- Confirm the manual Notepad target-match/mismatch scenarios and record any
  remaining limitation before adding a router boundary.
- No database, configuration framework, or new UI automation dependency is
  required for this slice.

### Tests required

- Contract validation for valid and malformed requests/results.
- Backend capability queries for supported and unsupported operations.
- Existing actions still call the same underlying tools with the same
  arguments and observable behavior.
- Known target mismatch still blocks typing; unknown/low-confidence behavior
  remains unchanged.
- Backend metadata does not mutate or imply verification; `TYPE_TEXT` remains
  `UNVERIFIED`.
- Existing task state, fail-stop, skipped-step, and event tests continue to
  pass.
- Manual smoke test: launch Notepad, assess target, and confirm the current
  foreground-input path is still reported as foreground-required.

### Risks

- Introducing a general abstraction too early could duplicate the action
  registry or overcomplicate the task runner.
- Conflating dispatch results, target assessment, and verification could
  overstate success.
- Compatibility changes could break the CLI or direct tool callers.
- The router may accidentally become a place for implicit focus activation
  or a silent fallback.

### Success criteria

- Existing behavior is preserved and the full relevant test suite passes.
- Current desktop tools are explicitly classified as foreground-required.
- A caller can identify backend and dispatch result without interpreting
  either as proof of task completion.
- No window is activated and no action gains background capability.
- No new action is enabled solely by adding the adapter boundary.

## Phase 4.2 — Configuration, policy, and durable audit

### Objective

Add the minimum validated configuration, authorization/confirmation, and
durable observability needed to safely enable capabilities beyond the
existing low-risk prototype actions.

### Deliverables

- Validated local configuration for model/runtime settings, data/log paths,
  privacy options, enabled backends, and policy defaults. Keep credentials
  out of plaintext configuration.
- A centralized pre-dispatch policy check with explicit allow, confirmation
  required, and denied outcomes. New or higher-impact capabilities default
  to confirmation or denial until configured.
- A durable, local audit record correlated to task and operation IDs. Record
  the minimum necessary request summary, authorization/confirmation
  decision, backend, target, dispatch result, side effects, verification,
  timestamps, and errors.
- Searchable task history or a basic audit viewer. Retain the current
  progress stream as transient UI progress; do not treat it as the durable
  ledger.
- Defined retention, export, and deletion behavior. Avoid storing full model
  prompts, screenshots, accessible text, or secrets by default.

### Files affected

Likely implementation files:

- `scripts/agent_ui.py` — load/report validated configuration and show
  confirmation or audit outcomes.
- `scripts/task_execution.py` — invoke policy before dispatch and append
  correlated audit results.
- New modules such as `scripts/configuration.py`,
  `scripts/execution_policy.py`, and `scripts/audit_store.py`.
- A new local configuration file/schema and a local database/schema
  migration mechanism, if required by the chosen storage format.
- Tests under `tests/` for configuration, policy, audit, and runner
  integration.

### Dependencies

- Phase 4.1 request/result and backend identity contracts.
- A defined minimum data-retention and privacy policy before persistence is
  enabled.
- Existing behavior inventory: identify which current actions are
  non-side-effecting, foreground-affecting, or externally consequential.
- Choose the lightest storage/configuration approach that meets local
  validation, migration, and testability needs; do not select a distributed
  service or complex framework without a requirement.

### Tests required

- Invalid, missing, or incompatible configuration fails clearly before
  execution; safe defaults are explicit rather than silent.
- Policy allow/confirm/deny paths, including proof that denial causes no
  backend side effect.
- Confirmation cancellation/decline never dispatches.
- Audit records correlate to task/operation IDs and capture the actual
  backend, policy decision, dispatch result, and verification separately.
- Restart/reopen persistence, malformed/partial record handling, and storage
  errors are surfaced.
- Retention/export/delete behavior and exclusion of secrets/full prompts by
  default.
- Failure paths are also audited without converting a failed operation into
  success.

### Risks

- Persisting prompts, screen content, window titles, or accessible text can
  reveal sensitive information.
- A policy check that is bypassable through direct tool calls offers false
  assurance.
- Audit write failures can make an executed side effect untraceable.
- Configuration migration or corruption may prevent startup.
- Logging and confirmation UI may add friction or block the Tk event loop if
  implemented synchronously.

### Success criteria

- All dispatch paths pass through the same policy gate.
- Denied/declined actions produce no side effects and an explicit result.
- Every attempted operation has a durable correlated audit record, or an
  explicit surfaced audit failure that prevents unsafe dispatch where
  required by policy.
- The user can inspect and export history and understand retention/deletion
  controls.
- Secrets and full prompts are absent from ordinary records by default.
- Foreground mismatch behavior and verification semantics remain unchanged.

## Phase 4.3 — User-controlled basic memory

### Objective

Add modest continuity through local episodic summaries and explicitly
approved preferences, while keeping memory separate from the audit ledger
and model working context.

### Deliverables

- Local storage for concise task/conversation summaries and user-approved
  preferences. Do not automatically persist every tool event or derive
  high-sensitivity facts without review.
- A memory view with inspect, edit/correct, export, and delete controls.
- Clear user controls for retention and whether a memory is eligible for
  future context injection.
- Explicit provenance and timestamps for stored facts; distinguish
  user-entered/approved facts from generated summaries.
- A narrowly scoped retrieval function for relevant preferences or recent
  context. No vector store, knowledge graph, or automatic fact extraction
  in this increment.

### Files affected

Likely implementation files:

- New modules such as `scripts/memory_store.py` and
  `scripts/memory_service.py`.
- `scripts/agent_ui.py` — memory inspection and user controls, either as a
  minimal panel/dialog or the repository's established UI pattern.
- The request/context assembly module (currently in the agent/UI path) only
  to inject explicitly eligible memory.
- New memory schema/migrations and focused tests under `tests/`.
- `scripts/audit_store.py` only if a deliberate foreign-key/reference
  relationship is needed; memory content must not be duplicated into audit.

### Dependencies

- Phase 4.2 local storage, configuration, privacy, and retention controls.
- Stable task identity and concise audit summaries from Phase 4.1/4.2.
- User-visible review and deletion behavior designed before any preference
  is automatically reused.

### Tests required

- Store and retrieve approved memory across application restarts.
- Generated but unapproved facts are not retained or injected.
- Edit, correction, export, retention expiry, and deletion behave as
  specified, including deletion from retrieval indexes.
- Audit and memory remain separate: deleting a memory does not rewrite the
  audit ledger, and audit content is not automatically injected as memory.
- Sensitive content is excluded or requires the explicit review path.
- Context retrieval is bounded, relevant, and does not alter unrelated
  requests when no memory matches.

### Risks

- Incorrect summaries can become persistent false facts.
- Memory can leak between users or contexts if provenance and eligibility
  are unclear.
- Deletion may be incomplete if data is duplicated in logs, caches, or
  indexes.
- Automatically adding memory to prompts can affect model behavior
  unpredictably or expose private information.

### Success criteria

- A user can inspect, correct, export, and delete persisted memory.
- Only approved/eligible memory is available for future context injection.
- Audit records remain separate, and no semantic/vector/graph system is
  introduced without demonstrated need.
- Memory behavior is deterministic enough to test and can be disabled via
  configuration/privacy controls.

## Phase 4.4 — Bounded UI Automation pilot

### Objective

Demonstrate one small semantic desktop operation against an explicitly
identified target, with no requirement to take foreground focus and with
independent read-back where the selected control supports it.

### Deliverables

- A Windows UI Automation adapter behind the Phase 4.1 backend contract.
- Begin with read-only inspection of a small known control set; record
  target/control identity, supported patterns, and provider limitations.
- Add at most one low-risk operation with deterministic read-back, selected
  only after confirming that the chosen application/control actually exposes
  the needed UIA pattern. Do not assume Notepad or any other application
  supports a particular text pattern across Windows versions.
- Return explicit unsupported, unavailable, timeout, stale-element, and
  operation-failed results. No silent fallback to pyautogui.
- Enforce Phase 4.2 authorization and audit policy; retain separate target,
  dispatch, and verification records.

### Files affected

Likely implementation files:

- A new Windows-specific module, for example
  `scripts/backends/windows_uia.py`.
- `scripts/task_execution.py` and the backend/capability module from Phase
  4.1 — register and select the pilot only for its explicitly supported
  operation.
- `scripts/execution_policy.py` and `scripts/audit_store.py` — apply and
  record policy for the new backend.
- New UIA unit and controlled integration tests under `tests/`.
- `scripts/agent_ui.py` only if it needs to present the selected backend or
  a clear unsupported/read-back result.

### Dependencies

- Phase 4.1 typed contracts, foreground adapter, target metadata, and
  backend-selection boundary.
- Phase 4.2 validated configuration, centralized policy, and durable audit.
- A test application/control with a confirmed UIA provider and an operation
  whose outcome can be read back.
- Windows-specific integration test environment; pure selection and result
  handling must remain testable without live UIA.

### Tests required

- Unit tests for capability declaration, target scoping, policy gating,
  timeouts, and each structured result category.
- UIA provider/control missing or unsupported pattern produces explicit
  unsupported/unavailable; it never routes to global input.
- Read-only discovery is bounded and does not collect unrelated accessible
  content.
- Pilot operation selects the intended control and confirms its
  postcondition by read-back.
- Foreground window remains unchanged in the supported background test;
  where a provider unexpectedly changes focus, report failure/limitation.
- Stale element, ambiguous target/control, changed UI, elevated/integrity
  boundary, and provider timeout cases fail safely.
- Confirm `TYPE_TEXT` and all existing foreground actions preserve their
  prior verification and focus behavior.
- Manual validation while the user actively interacts with a separate
  application; document supported application/version and limitations.

### Risks

- UIA support varies by control, application framework, and OS version.
- A test that passes for one provider may be wrongly generalized to all
  desktop applications.
- Accessible content may contain sensitive data; discovery must be narrowly
  scoped.
- UIA calls can block or return stale elements; timeouts and re-resolution
  are necessary.
- Adding fallback to global input after a UIA failure would violate the
  explicit-backend and no-surprise principle.

### Success criteria

- At least one documented, low-risk operation works through UIA without
  changing foreground focus and with deterministic postcondition read-back.
- Unsupported cases are explicit and cannot trigger hidden foreground input.
- Target, selected element, backend, policy, dispatch, and verification
  evidence are distinguishable in results/audit.
- Existing task execution, target mismatch, and verification tests still
  pass.
- Claims are limited to the tested application/control/version combination.

## Key prioritization decisions

### Smallest possible Phase 4 implementation slice

The smallest useful, independently testable slice is **Phase 4.1's
foreground adapter seam**:

- define a minimal typed request/result and capability contract;
- wrap the existing foreground tool path without changing what it does;
- preserve target mismatch gating and current verification behavior;
- add unit and regression tests showing no behavior drift.

This establishes the backend boundary and provides a safe base for later
policy and integrations, without enabling new side effects or requiring
configuration/database/UIA dependencies.

### Which backend should be implemented first?

Implement the **Foreground Automation Backend adapter first**, as the first
runtime backend, because it is already implemented in `pyautogui`/Win32 and
can validate the contract without changing behavior.

The first **new background-capable backend** should be a bounded **UI
Automation pilot** in Phase 4.4, after policy and audit. Start with read-only
discovery and add one operation only after provider support and read-back
have been confirmed. Do not implement hidden-window input or generic Win32
keyboard-message simulation as a shortcut.

### Which backend gives the largest practical benefit?

For the project's stated need to interact with desktop applications while
the user works elsewhere, **UI Automation has the largest practical benefit
among the proposed general desktop backends** when the target exposes the
required controls. It can avoid global focus and can offer semantic
read-back, but its coverage is not universal.

For immediate file/project workflows, the **Workspace Backend** is likely
the highest-value low-risk capability because operations can be scoped and
verified directly. It is a Phase 5 candidate in the current backend roadmap
and does not replace UI automation for an application's live interface.

### Which backend aligns best with the current codebase?

The **Foreground Automation Backend** aligns best today: it wraps the
existing `scripts/tools.py` operations and target checks, requires no new
platform dependency, and can be introduced while preserving the current
sequential runner.

The backend most aligned with the **long-term architecture** is the
capability-based hybrid router, with small typed adapters and explicit
selection; this is an architectural boundary, not one backend implementation.

## Approval and scope gates

- Do not change task states or introduce retries/cancellation as part of
  these backend increments.
- Do not implicitly activate windows, claim that virtual desktops or a
  second monitor provide background input isolation, or route silently from
  semantic execution to global input.
- Treat API/UIA invocation and target match as dispatch/precondition evidence,
  not verification. `TYPE_TEXT` remains `UNVERIFIED` until exact resulting
  text is read from the intended control.
- Keep Home Assistant, browser automation, broad workspace writes/shell,
  autonomous routines, and multi-agent orchestration outside this Phase 4
  implementation plan.
- At each increment, report changed files, tests, untested/manual scenarios,
  and rollback scope before requesting approval to proceed.
