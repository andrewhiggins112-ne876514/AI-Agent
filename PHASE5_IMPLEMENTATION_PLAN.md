# Phase 5 Implementation Plan

## Purpose and scope

This plan decomposes the proposed supervised Developer Agent into five
testable phases. It is based on
[PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md),
[PHASE4_IMPLEMENTATION_PLAN.md](./PHASE4_IMPLEMENTATION_PLAN.md),
[PHASE4_EXECUTION_BACKENDS.md](./PHASE4_EXECUTION_BACKENDS.md),
[PROJECT_VISION.md](./PROJECT_VISION.md), [ROADMAP.md](./ROADMAP.md), and
[DECISIONS.md](./DECISIONS.md).

Phase 5 is a proposal for future work, not a statement that Phase 4 or the
older roadmap milestones are complete. The current roadmap still describes
Phase 3 as its active milestone, while the Phase 4/5 architecture documents
are proposed. Before implementation, confirm the actual code, tests, manual
acceptance status, and worktree at the approved baseline.

The Developer Agent should progress from read-only repository awareness to
evidence-backed proposals, then authorized test execution and sandbox
validation. Signal-driven capability evolution comes last. No phase grants
permission to modify code, roadmap, decisions, policy, or deployment targets
without the corresponding human approval.

## Recommended implementation order

1. **Phase 5.1 — Repository Awareness**
2. **Phase 5.2 — Proposal Generation**
3. **Phase 5.3 — Automated Testing**
4. **Phase 5.4 — Sandbox Validation**
5. **Phase 5.5 — Capability Evolution Engine**

The ordering is dependency-driven. Repository evidence enables proposals;
proposal and test contracts are needed before sandbox execution; capability
evolution depends on reliable repository/test evidence and, if it consumes
runtime task signals, a governed durable audit source.

## Phase 5.1 — Repository Awareness

### Objective

Provide a local, read-only, provenance-aware view of one explicitly selected
repository so Jarvis can answer bounded engineering questions using actual
source, test, documentation, roadmap, decision, and architecture evidence.

### Deliverables

- Explicit repository-root selection and an allow-listed set of file
  categories/paths. Respect ignore rules and exclusions.
- Rebuildable local manifest of indexed paths, hashes/revision IDs,
  timestamps, document sections, symbols where available, and source
  references.
- Git baseline facts: current commit/branch and clean/dirty status, with
  uncommitted work identified separately from committed code.
- Read-only discovery of source code, tests, documentation, roadmap,
  decisions, and architecture documents; future-state proposals are labeled
  as proposals, not implemented requirements.
- Evidence-linked answers that disclose stale, missing, or unindexed
  sources; derived summaries remain subordinate to source files.
- No repository writes, external uploads, code execution, or automatic
  roadmap/decision edits.

### Files likely affected

Likely new modules and tests, depending on the existing application
structure:

- `scripts/repository_awareness.py` — orchestrate bounded discovery and
  answer assembly.
- `scripts/repository_index.py` or `scripts/repository_manifest.py` — local
  index, hashes, invalidation, and source provenance.
- `scripts/repository_policy.py` — repository root, exclusions, ignore
  handling, and no-network/no-write constraints, if not already covered by
  an approved policy module.
- `tests/test_repository_awareness.py`
- `tests/test_repository_index.py`
- A configuration/schema entry only if explicit repository selection cannot
  be managed through an existing approved mechanism.

Avoid creating persistent indexes under the repository itself by default;
use the configured local application-data location if one exists.

### Dependencies

- **No Phase 4 runtime execution adapter is required** for this
  read-only-only slice.
- A clear selection of repository root and excluded paths.
- Phase 4 configuration is preferred for stable data paths and user
  settings, but a narrowly scoped explicit root supplied per session can
  support an initial prototype.
- If answers use external models/services, they require a separate approved
  data-sharing policy; local operation is the default.

### Risks

- Dirty user work could be mistaken for approved baseline code.
- Ignore/exclusion mistakes could index credentials, logs, screenshots, or
  unrelated personal files.
- Stale or incomplete summaries could be presented as current facts.
- Repository content may contain prompt-injection-like instructions; indexed
  text must remain untrusted data and cannot grant permissions.
- Broad indexing may produce excessive latency or expose more code than a
  specific question requires.

### Testing requirements

- Root allow-list and path traversal rejection, including paths resolving
  outside the selected repository.
- Ignore rules and explicit exclusions are applied; sensitive fixtures and
  local artifacts are not read.
- Worktree/commit state is reported accurately and dirty changes are not
  silently treated as approved.
- Hash/revision changes invalidate affected index entries and stale summaries
  are identified.
- Source citations resolve to the correct file, section/symbol, and revision.
- Read-only/no-network behavior is verified with test doubles or process
  instrumentation; no writes occur in the selected repository.
- Malformed, missing, unreadable, and binary files produce explicit
  incomplete-index results rather than fabricated summaries.

### Success criteria

- A bounded architecture/status question is answered with precise local
  citations and a clear committed-versus-uncommitted distinction.
- Findings separate implementation facts, approved requirements, proposals,
  and hypotheses.
- Stale or incomplete evidence is disclosed.
- No code, document, configuration, Git, or network side effect occurs.
- A user can rebuild or discard the index without changing source files.

## Phase 5.2 — Proposal Generation

### Objective

Convert evidence from repository awareness into concise, reviewable
engineering proposals before any source or project document is changed.

### Deliverables

- Structured proposal types for design proposals, implementation plans,
  architecture reviews, roadmap-update proposals, and refactoring
  suggestions.
- Required proposal fields: objective, classification, source evidence,
  observed versus expected behavior, assumptions/confidence, alternatives,
  scope/non-scope, risks, privacy/security/compatibility effects,
  dependencies, tests/manual checks, rollback, and approval boundaries.
- Definitions and classification for Bug, Limitation, Gap, Enhancement,
  Feature Request, Architectural Improvement, and Optimisation Opportunity.
- Source links and provenance for material claims; proposals label
  hypotheses and uncertainty.
- Preview/export in the existing UI or as an explicitly requested document;
  proposal generation itself does not save or edit repository files unless
  the user approves that output.
- No autonomous patch creation or modification of roadmaps, decisions, or
  code.

### Files likely affected

- `scripts/proposal_generation.py` — proposal orchestration and evidence
  composition.
- `scripts/proposal_models.py` — typed proposal categories and required
  fields.
- `scripts/repository_awareness.py` — read-only evidence interface, if
  Phase 5.1 is implemented separately.
- `scripts/agent_ui.py` — proposal preview and explicit save/export action,
  only if integrated into the GUI.
- `tests/test_proposal_generation.py`
- `tests/test_proposal_models.py`

### Dependencies

- Phase 5.1 evidence and source references for repository-specific claims.
- A stable distinction between approved decisions, historical statements,
  and proposed architecture.
- Phase 4 audit is **not required** to generate proposals from repository
  evidence alone. It is required before proposals rely on prior task/tool
  history or user behavior signals.
- User approval for any proposal document to be written into the repository.

### Risks

- Confident-sounding but unsupported claims, category confusion, or
  requirements inferred from future-state documents.
- Proposal generation may unintentionally overwrite a user-authored file or
  turn a suggestion into an apparent approved decision.
- Sensitive code or logs may be sent to a non-local model if data policy is
  unclear.
- Excessive boilerplate can make proposals difficult to review.

### Testing requirements

- Required-field and schema validation; invalid proposals are not presented
  as complete.
- Evidence references resolve and support the associated claims.
- Approved/proposed/historical source distinctions remain intact.
- Uncertain evidence yields explicit uncertainty, not a fabricated bug or
  success-shaped conclusion.
- Proposal generation has no filesystem/Git side effect by default.
- Explicit save/export is scoped to a new user-selected destination and does
  not overwrite without confirmation.
- Sensitive data redaction and local-only behavior are tested according to
  the configured model policy.

### Success criteria

- Given a bounded question and repository evidence, Jarvis creates a
  reviewable proposal with cited facts, labeled hypotheses, alternatives,
  test requirements, and approval gates.
- The proposal distinguishes a bug from a limitation, gap, enhancement,
  feature request, architecture change, or optimization.
- No code or roadmap/decision file is changed.
- Users can reject, revise, or request a different proposal without
  modifying the repository.

## Phase 5.3 — Automated Testing

### Objective

Discover applicable tests and provide a controlled, accurately reported test
workflow for a human-approved change or proposal.

### Deliverables

- Test inventory: test framework, selectors, fixtures, configuration,
  dependencies, and known platform requirements.
- A proposal-to-test mapping that identifies unit, integration, regression,
  performance, and manual validation requirements as applicable.
- A test execution request containing approved command/selector, working
  directory, environment, timeout/resource limits, network policy, and
  permitted side effects.
- Structured test result with command, revision, environment, duration,
  exit status, test counts, failures, output references, and whether execution
  was blocked or incomplete.
- Dry-run/preview of commands before execution and clear separation between
  discovery, approval, and execution.
- No automatic code edits, test weakening, failure suppression, commit, or
  merge as a response to test failure.

### Files likely affected

- `scripts/test_discovery.py` — identify test configuration and candidates.
- `scripts/test_execution.py` — approved command execution and result
  capture, if the repository does not already have a safe task runner.
- `scripts/test_results.py` — typed result and provenance.
- `scripts/agent_ui.py` — command preview, approval, and result display if
  user-facing execution is added.
- `tests/test_test_discovery.py`
- `tests/test_test_execution.py`
- `tests/test_test_results.py`
- A narrow project test manifest/configuration only if required to constrain
  approved commands.

### Dependencies

- Phase 5.1 test discovery and baseline revision identification.
- Phase 5.2 proposal/test mapping, or an explicit user-supplied test command
  and scope.
- Human approval for the specific test command and environment.
- Phase 4 policy/configuration should govern external, privileged,
  state-changing, desktop, or device tests; such tests remain disabled until
  that governance exists.
- Unit tests using deterministic fixtures can begin before sandbox
  implementation, but untrusted or higher-risk test execution should wait
  for Phase 5.4.

### Risks

- A test can modify files, use network access, access credentials, or operate
  the live desktop despite its name.
- Shell expansion or user-controlled test configuration could execute
  unexpected commands.
- Environment drift or incomplete output could lead to false pass/fail
  reports.
- Automatically retrying a stateful integration test may duplicate side
  effects.

### Testing requirements

- Test discovery handles missing/malformed config without inventing a
  runnable command.
- Execution requires approval bound to the exact command, revision, working
  directory, and environment.
- Denied, timed-out, interrupted, or environment-failed runs are reported as
  such, never as passed.
- Command argument handling prevents unintended shell expansion or scope
  escape according to the chosen execution mechanism.
- Result parsing handles zero tests, partial results, crashes, and malformed
  output explicitly.
- Test execution itself is tested with harmless fixture commands; tests that
  would alter the real desktop, network, credentials, or devices are not run
  without explicit approval.
- Regression mapping includes existing Phase 3 task, target mismatch, and
  verification contracts when execution code is affected.

### Success criteria

- Jarvis can show the proposed test plan before executing it.
- Only the approved command/selector runs, within the approved scope and
  timeout.
- Results identify revision, environment, failures, and limitations.
- No failed test causes automatic code modification, disabled assertions, or
  silent retry.
- Manual/external/platform-specific validation is clearly marked as not run
  unless actually performed.

## Phase 5.4 — Sandbox Validation

### Objective

Validate an approved patch in a disposable environment that limits access to
the user's primary checkout, credentials, network, and desktop.

### Deliverables

- Sandbox policy and threat model for code checkout, dependencies, network,
  writable paths, secrets, resource quotas, and artifacts.
- Disposable branch/worktree for revision management, combined with a
  least-privilege container for ordinary unit/build tests.
- VM or isolated Windows session for Windows GUI/UIA testing only when
  required; prohibit automation of the user's active desktop.
- Reproducible setup, command allow-list, timeout/resource limits, result
  capture, and cleanup.
- Patch/diff and approved test artifacts returned to a review area; no
  automatic merge or deploy.
- Explicit report when the current environment cannot provide a meaningful
  isolation boundary.

### Files likely affected

- `scripts/sandbox_policy.py` — environment capabilities and constraints.
- `scripts/sandbox_manager.py` — create/run/collect/cleanup lifecycle, if
  automated lifecycle is approved.
- `scripts/test_execution.py` and `scripts/test_results.py` — run through
  sandbox and preserve provenance.
- Container/VM definition or scripts, such as a narrowly scoped
  `Dockerfile`/compose configuration or VM setup scripts, only after threat
  review and user approval.
- `tests/test_sandbox_policy.py`
- `tests/test_sandbox_manager.py`
- Operational documentation for supported environments and cleanup.

### Dependencies

- Phase 5.3 approved test request/result contract.
- A selected sandbox technology with verified filesystem, network,
  privilege, resource, and cleanup controls.
- Human approval for sandbox configuration, dependency downloads, and any
  network-enabled test.
- Phase 4 configuration/policy/audit is required if the sandbox uses
  application credentials, records execution history, or invokes Jarvis
  tools. The preferred first sandbox has no such credentials or tool
  privileges.

### Risks

- Writable mounts, Docker/VM control sockets, shared folders, clipboard,
  network, or host credentials can defeat isolation.
- A Git worktree or branch alone may be mistaken for a security sandbox.
- Cleanup could delete user data or leave background processes/resources
  running.
- Windows UI automation in a VM may behave differently from the host and
  may require separate licensing or interactive-session setup.
- Dependency installation can execute untrusted build hooks or contact
  external services.

### Testing requirements

- Verify sandbox identity, baseline revision, writable mount list, network
  policy, privilege level, and resource limits before execution.
- Confirm the sandbox cannot read designated secret/home fixtures or write
  outside approved output locations.
- Validate timeout, crash, cancellation/termination, artifact collection,
  and cleanup paths using disposable fixtures.
- Confirm no host foreground focus changes and no live user desktop/device
  is touched.
- Re-run selected tests from a clean sandbox and compare result provenance.
- Audit or report attempted sandbox escapes; never silently continue after
  isolation fails.

### Success criteria

- The approved test runs in a reproducible environment separated from the
  user's primary working state.
- The sandbox has only the explicitly approved files, network access, and
  privileges.
- Artifacts and results are traceable to the exact patch and environment.
- Cleanup is verified and does not affect the primary checkout or user data.
- If isolation cannot be proven, execution is blocked or clearly downgraded
  with renewed human approval; the agent does not claim sandbox validation.

## Phase 5.5 — Capability Evolution Engine

### Objective

Identify and rank improvement opportunities from permitted repository,
testing, and user/task signals, then produce evidence-backed proposals
without making changes automatically.

### Deliverables

- Opt-in/configurable signal sources with minimal collection and retention:
  failed/blocked tasks, structured verification outcomes, user corrections,
  repeated unmet requests, test failures/flakiness, and measured performance.
- Normalization/grouping for recurring patterns with links to original
  evidence and applicable revision/environment.
- Candidate classification using the seven definitions in
  `PHASE5_DEVELOPER_AGENT.md`.
- Prioritization by impact, frequency, confidence, severity, effort,
  dependencies, and reversibility; uncertainty and user priority remain
  visible.
- Human-review queue with accept, dismiss, defer, and request-more-evidence
  actions; no automatic code, policy, roadmap, decision, or permission
  changes.
- Explainable trend/performance reports with baseline and measurable
  comparison, not intuition-only optimization claims.

### Files likely affected

- `scripts/capability_evolution.py` — signal aggregation and candidate
  ranking.
- `scripts/signal_models.py` — normalized source, provenance, and candidate
  types.
- `scripts/proposal_generation.py` — generate proposals from accepted
  candidates.
- `scripts/audit_store.py` or an approved task-history interface — read
  privacy-minimized runtime signals, if Phase 4 provides this store.
- `scripts/agent_ui.py` — candidate review and privacy/retention controls.
- `tests/test_capability_evolution.py`
- `tests/test_signal_privacy.py`
- `tests/test_candidate_review.py`

### Dependencies

- Phases 5.1 and 5.2 for repository evidence and proposal generation.
- Phase 5.3 for structured test results; Phase 5.4 where candidates rely on
  sandbox test results.
- Phase 4.2 durable audit and privacy/retention controls are mandatory before
  ingesting task/tool history. If not complete, restrict the engine to
  repository and explicitly imported test evidence.
- User approval for telemetry collection, retention, and any external
  model/service processing.

### Risks

- Frequency may be confused with importance; repeated requests do not equal
  approval to build.
- Noisy/flaky signals may overwhelm the user or create false diagnoses.
- Raw conversations, source, test output, screenshots, or audit records may
  contain sensitive content.
- Self-reinforcing model conclusions could inflate confidence without new
  evidence.
- Performance suggestions may trade away correctness, safety, or
  verification quality.

### Testing requirements

- Repeated and noisy signal fixtures produce stable, explainable grouping
  and ranking.
- Candidate provenance links back to the correct test/task/revision and
  evidence is not fabricated.
- Opt-out, retention expiry, deletion, and exclusion of sensitive/raw content
  work end-to-end.
- Unknown/low-confidence evidence stays a hypothesis and does not become a
  confirmed bug or approved roadmap item.
- Dismissed candidates do not reappear immediately without new evidence or
  an explicit reset.
- No candidate triggers source/document/permission edits, external data
  transmission, or code execution.
- Optimization recommendations require a reproducible baseline and
  measurable threshold.

### Success criteria

- The engine surfaces a small, ranked set of explainable opportunities with
  category, confidence, impact, provenance, and review controls.
- Users can opt out, dismiss, defer, and request more evidence.
- Only permitted, privacy-minimized signals are processed and retained.
- No candidate changes code, policies, decisions, roadmap, or privileges
  without fresh explicit approval.
- Proposals generated from signals satisfy Phase 5.2 evidence and review
  requirements.

## Cross-phase gates

- Keep the repository index and runtime memory/audit separate. Repository
  content and event history are not automatically injected into prompts.
- Keep generated proposals non-authoritative until reviewed and approved.
- Treat repository text, issue content, test output, and model summaries as
  untrusted data; they cannot grant tool permissions or bypass approval.
- Preserve current task/target/verification contracts. A tool dispatch,
  passing test, or target match is not proof of a higher-level requested
  outcome.
- No network, external service, privileged command, user desktop, credential,
  or physical device access by default.
- Every phase has a stop condition when scope, environment, source evidence,
  or isolation cannot be established.

## Phase 4 prerequisites and ordering decisions

### Does Phase 4 need to be complete first?

**No, not in its entirety.** The read-only Phase 5.1 slice can start before
Phase 4 runtime backends or memory are complete, provided it uses an
explicitly selected repository, local processing, no writes, and no external
uploads.

However, the following Phase 4 work is a prerequisite before corresponding
Phase 5 capabilities:

- **Before using task history, failure patterns, or user behavior in Phase
  5.5:** complete Phase 4.2 configuration, policy, durable audit, privacy,
  and retention controls. Until then, Phase 5.5 must use repository and
  explicitly supplied test evidence only.
- **Before automated execution of tests with external, privileged,
  state-changing, desktop, or device access:** complete and validate the
  relevant Phase 4 policy/confirmation controls; then still require
  operation-specific user approval and sandbox controls.
- **Before injecting memory or stored task context into proposals:** complete
  Phase 4.3 review, edit, export, deletion, and eligibility controls. This
  injection is optional and not needed for the initial Phase 5 slices.
- **Before running tests through Jarvis' own backend/tool system or with
  credentials:** complete Phase 4.1 contracts and Phase 4.2 policy/audit.
- **Before adding UIA, browser, Home Assistant, or workspace capabilities to
  the Developer Agent:** use the relevant approved backend/security
  foundations; these are not needed for read-only repository awareness.

Phase 4.1's foreground adapter and Phase 4.4's UIA pilot are not prerequisites
for the read-only repository index, proposal generation, or isolated
unit-test discovery. Phase 4.2 is the critical governance dependency for
automated side effects and runtime signal use.

### Prioritization questions

1. **Smallest safe implementation slice:** Phase 5.1 read-only inventory of
   one explicitly selected repository: report commit/worktree status,
   enumerate allow-listed code/tests/docs, compute local hashes, and answer
   one bounded question with source references. No model upload, execution,
   or repository writes.
2. **Earliest user-visible benefit:** Phase 5.1's evidence-linked repository
   status/architecture answers. Users get immediate, checkable answers
   without waiting for automatic test execution or an evolution engine.
3. **Phase to implement first:** Phase 5.1 Repository Awareness.
4. **Foundation for all later phases:** Phase 5.1's repository inventory,
   provenance, revision awareness, and freshness model. Phase 5.2 depends on
   its evidence links; later phases also need reliable revision and source
   context. Phase 4.2 audit/privacy remains a separate foundation for
   runtime-signal and side-effect use, not a replacement for repository
   awareness.
5. **Phase 4 work required first:** Phase 4 is not a blanket blocker.
   Complete Phase 4.2 before consuming persisted runtime signals or
   authorizing side-effecting test execution through Jarvis. Phase 4.1 is
   needed if tests invoke Jarvis backends. Phase 4.3 is needed only if
   approved memory will be included. Read-only Phase 5.1 does not require
   those runtime subsystems.
6. **Recommended implementation order:** 5.1 → 5.2 → 5.3 → 5.4 → 5.5.
   Complete the relevant Phase 4 gate at each boundary rather than delaying
   safe, read-only repository work until every Phase 4 feature is finished.

## Rollback strategy

Each phase should be independently disableable and should keep derived
indexes, candidate queues, and sandbox outputs outside the source tree.
Rollback should remove only the new feature/data and preserve user files,
existing audit history, and unrelated worktree changes. For schema-backed
state, provide a tested export/backup and migration rollback before enabling
persistent writes. Sandbox cleanup must target only a specifically resolved
temporary environment and never the repository root or user home.
