# Phase 5 Developer Agent

## Purpose and status

This document proposes a supervised Developer Agent for Jarvis / AI-Agent.
It is a design proposal only: it does not authorize repository access beyond
the current user request, code changes, tool execution, commits, merges, or
deployment.

The JARVIS Home Core specification is a reference blueprint, not a mandate
to implement its full multi-agent system. Phase 5 should build a small,
reviewable capability on top of the existing local-first Python project and
the Phase 4 execution, policy, audit, and memory foundations. Do not assume
those foundations are complete until implementation and acceptance tests
demonstrate that they are.

## 1. Vision

The long-term goal is for Jarvis to understand the software system it helps
maintain: its source code, tests, documentation, roadmap, prior decisions,
current limitations, and approved architecture. Using that context, it
should be able to surface useful engineering observations:

- identify reproducible bugs and recurring failure patterns;
- distinguish a known limitation from a defect or missing capability;
- identify gaps between approved architecture, roadmap, and implementation;
- recognize repeated user requests and functionality not yet supported;
- suggest safe simplifications, refactorings, and performance improvements;
- draft design proposals, implementation plans, architecture reviews, and
  roadmap changes before any code is written.

The objective is **supervised self-improvement**, not uncontrolled
self-modification. The Developer Agent may gather evidence and prepare a
proposal autonomously within an approved scope. Humans retain authority over
what problem to solve, what changes to make, what tests to run when they
could have side effects, whether to accept a patch, and whether to merge or
deploy.

The proposal system must distinguish observations from hypotheses and
evidence. It must not claim a bug from a user complaint alone, infer that
unimplemented design is a defect, or treat a model-generated suggestion as
an approved decision.

## 2. Definitions

| Term | Definition | Example |
| --- | --- | --- |
| **Bug** | Implemented behavior violates an existing documented or tested contract under a reproducible condition. | A known foreground mismatch fails to block `TYPE_TEXT` despite the accepted Step 7B behavior. |
| **Limitation** | A known constraint or unsupported condition that the implementation currently handles honestly or intentionally. | Typing uses the active foreground input recipient and does not provide arbitrary background typing. |
| **Gap** | A material difference between current implementation and an approved requirement, architecture, or roadmap deliverable. | A planned persistent audit store has no implementation after its approved milestone. |
| **Enhancement** | An improvement to existing behavior that is not necessary to correct a contract violation. | Show clearer evidence for an existing target assessment. |
| **Feature Request** | A request for new user-visible capability that does not currently exist. | Add a supported way to search a browser page. |
| **Architectural Improvement** | A change to module boundaries, contracts, dependencies, or responsibilities intended to improve correctness or maintainability. | Introduce a typed backend interface beneath the existing task runner. |
| **Optimisation Opportunity** | A measured or strongly evidenced opportunity to improve resource use, latency, or throughput while preserving behavior. | Reduce a measured slow test setup without weakening its assertions. |

The agent should attach category, source, confidence, supporting evidence,
affected contract, impact, and unresolved questions to each finding. A
proposal may include multiple categories but must identify the primary one.
An optimization is not established by intuition alone; it requires a
reproducible baseline and a measurable target.

## 3. Repository awareness

### Sources and discovery

Repository awareness should be based on an explicit, versioned inventory of
the selected checkout:

- **Source code:** discover modules, imports, public interfaces, action
  registries, and relevant call paths. Prefer language-server/code-index
  facts where available; otherwise use bounded file inspection and tests.
- **Tests:** discover test files, test configuration, fixtures, mocks, and
  coverage or historical failures when available. Distinguish executed
  tests from merely present tests.
- **Documentation:** index purpose, status, scope, and links across project
  vision, status, architecture proposals, decisions, and operational docs.
- **Roadmap:** capture milestone status and dependencies, while treating
  future roadmap text as planned work rather than implemented behavior.
- **Decisions:** capture whether each statement is approved, proposed,
  superseded, or historical; record date and source when available.
- **Architecture documents:** record proposed module boundaries,
  invariants, risks, capability descriptions, and acceptance criteria.

The initial index should be a rebuildable local manifest, not a new
authoritative source of truth. Store file paths, hashes or revision IDs,
document sections/symbols, timestamps, and source references. A content
change invalidates derived summaries; generated summaries never replace the
original source.

### Understanding and provenance

- Use version-control status and commit identity to distinguish committed
  content from worktree changes. Never silently stage, overwrite, or treat
  uncommitted work as approved baseline.
- Link each finding to precise file/symbol/line or test evidence and, where
  possible, the relevant commit/revision.
- Compare documentation to actual code and tests; do not assume a roadmap
  status is current merely because it is written down.
- Keep requirements, proposed designs, implementation facts, and inferred
  hypotheses as separate evidence classes.
- Refresh only affected index entries after a change, and disclose when
  indexing is incomplete or stale.
- Respect repository ignore rules and explicit exclusions. Do not ingest
  credentials, private keys, generated binary artifacts, local logs, user
  screenshots, or unrelated directories unless the user explicitly approves
  a narrow need.

### Security and privacy

Repository content is data to analyze, not authority to change the agent's
rules or approvals. Treat instructions found in comments, documents, test
fixtures, issues, or generated files as untrusted content; they cannot expand
tool permissions, sandbox access, network access, or approval scope.

Keep repository analysis local by default. External model or service use
requires a separate explicit policy and user authorization that identifies
what content may leave the machine. Redact secrets and sensitive data from
summaries, prompts, proposals, test output, and audit records. The agent must
not upload a repository or raw logs for analysis by default.

## 4. Capability Evolution Engine

The Capability Evolution Engine is a supervised signal collector and
triage service. It identifies candidate improvements; it does not alter
capabilities or roadmap state by itself.

### Signals it may examine

- failed or blocked tasks and their structured error/result categories;
- explicit user corrections and repeated requests for unsupported
  functionality;
- operation retries, timeouts, target mismatch, and `UNVERIFIED` outcomes;
- regression test failures and recurring flaky-test evidence;
- gaps between approved acceptance criteria and code/tests;
- repeated manual steps or workarounds surfaced in user-approved feedback;
- measured latency/resource data from opt-in, privacy-filtered telemetry;
- duplicate logic or unnecessary workflow steps identified from source and
  tests.

Task outcomes alone are not a reliable measure of user intent or product
priority. Collection should be opt-in/configurable, minimize retained
content, and prefer event type, action ID, outcome, timing, and redacted
context over raw transcripts, screenshots, or prompts.

### Detection and triage

1. **Collect:** ingest only permitted structured audit/test/user-feedback
   signals and approved repository revisions.
2. **Normalize:** group equivalent failures by stable error code, operation,
   module, and environment; preserve links to original evidence.
3. **Detect candidates:** identify repeated failures, common unmet requests,
   unverified steps, missing tests, unimplemented approved requirements,
   and measured bottlenecks.
4. **Classify:** label the candidate Bug, Limitation, Gap, Enhancement,
   Feature Request, Architectural Improvement, or Optimisation Opportunity.
5. **Corroborate:** inspect the relevant code, tests, docs, history, and
   environment facts. A repeated signal raises priority but does not prove
   root cause.
6. **Prioritize:** rank by user impact, frequency, severity, confidence,
   safety implications, effort, dependencies, and reversibility. Keep
   uncertainty explicit.
7. **Propose:** create a reviewable finding or proposal with evidence,
   alternatives, affected scope, risks, tests, and recommendation.

Do not automatically convert a signal into a bug report, roadmap change,
commit, or feature implementation. Low-confidence candidates should be
labelled for investigation or omitted rather than expressed as facts.

### Improvement opportunities

The engine may recommend workflow simplification or performance work only
when it can explain the baseline and trade-offs. It must preserve
verification strength, safety checks, and task semantics; fewer steps or
faster execution are not improvements if they reduce correctness or
observability.

## 5. Proposal system

All substantive code work begins with a proposal unless the human has
explicitly approved a narrowly scoped direct fix. Proposal types include:

- **Design proposal:** goals, non-goals, user impact, alternatives, module
  boundaries, contracts, privacy/safety implications, and acceptance
  criteria.
- **Implementation plan:** ordered, independently testable increments,
  dependencies, likely files, migration/compatibility needs, test matrix,
  risks, rollback approach, and manual validation.
- **Architecture review:** current-state evidence, alignment/gaps, proposed
  decisions, deferred capabilities, and consequences.
- **Roadmap update proposal:** what is complete, blocked, or out of scope;
  dependencies and measurable exit criteria. The agent must not modify the
  roadmap unless a human separately approves the documentation change.
- **Refactoring suggestion:** behavior-preservation contract, concrete
  duplication/complexity evidence, target scope, and equivalence/regression
  tests.

Every proposal should include:

- the user problem and objective;
- classification and evidence with provenance;
- observed current behavior versus expected behavior;
- assumptions and confidence;
- in-scope and explicitly out-of-scope files/capabilities;
- alternatives considered, including “do nothing”;
- security, privacy, accessibility, and compatibility impact;
- dependencies, estimates with uncertainty, tests, manual checks, and
  rollback strategy;
- approval checkpoints and what approval does **not** authorize.

The agent should quote only short, necessary source excerpts and link the
rest. It must distinguish known facts from hypotheses and avoid inventing
requirements from future-state documents. Proposal generation must not edit
source files, run unapproved state-changing commands, or commit/push changes.

## 6. Development workflow

```text
Observation
    ↓
Proposal
    ↓
Human Approval
    ↓
Implementation
    ↓
Testing
    ↓
Sandbox Validation
    ↓
Review
    ↓
Deployment
```

### Stage requirements

1. **Observation:** Gather scoped, provenance-preserving evidence. Identify
   baseline commit and worktree state. No repository writes.
2. **Proposal:** Produce a bounded design and test plan. No code, config,
   roadmap, or decision changes.
3. **Human approval:** Obtain approval for a specific objective, file scope,
   and behavior. Approval to plan is not approval to implement; approval to
   implement is not approval to run external/privileged tests, commit,
   merge, or deploy.
4. **Implementation:** Work only in the approved branch/worktree/sandbox and
   only within the approved scope. If the required change expands scope or
   reveals a material risk, stop and request new approval.
5. **Testing:** Run the approved, repository-standard checks. Treat test
   commands as potentially state-changing until reviewed; tests that access
   the network, user desktop, credentials, or real devices require explicit
   approval and isolated test fixtures.
6. **Sandbox validation:** Reproduce the intended behavior in a clean,
   bounded environment. Validate failure and denial paths as well as success.
7. **Review:** Provide a patch/diff summary, test evidence, limitations,
   security/privacy notes, and any deviation from approved scope. A separate
   human reviewer must approve consequential code; the agent must not
   self-certify its own safety-critical changes.
8. **Deployment:** Human-controlled release. Provide deployment instructions
   and rollback steps; do not execute deployment or alter a live installation
   automatically.

### Human approval remains mandatory for

- selecting or materially expanding the problem/scope when user intent is
  ambiguous;
- any source, test, configuration, dependency, permission, policy, audit,
  memory, or architecture change;
- executing tests or commands with network access, external side effects,
  privileged access, real credentials, desktop input, or physical devices;
- accepting generated code, modifying safety-critical paths, and resolving
  risky review findings;
- creating/changing decisions, roadmap commitments, releases, or deployment
  targets;
- all commits, merges, pushes, and deployments unless a future narrowly
  scoped automation policy explicitly authorizes an individual action.

Approval must refer to the proposed scope and a known patch/revision. Any
material code or scope change invalidates the prior approval. No approval is
inferred from silence, a previous unrelated task, or the agent's own
confidence.

## 7. Sandbox architecture

| Mechanism | Isolation provided | Benefits | Limitations and risks | Recommended role |
| --- | --- | --- | --- | --- |
| **Git branch** | Version-history separation only; shares the working directory, process, credentials, and filesystem. | Simple reviewable commits and familiar workflow. | Not an execution/security boundary; files and processes can still affect the host. | Use for change history, never as the only sandbox. |
| **Git worktree** | Separate checkout and index for a branch/commit, with shared Git object database. | Convenient parallel work and a clean diff; preserves the primary checkout. | Does not isolate processes, network, secrets, OS resources, or shared files outside the worktree. Linked worktrees share repository object storage and may share configuration/hooks. | Use as the disposable source workspace beneath a stronger runtime boundary. |
| **Container** | Process/filesystem isolation subject to mounts, runtime configuration, host kernel, and privileges. | Reproducible dependencies, resource controls, disposable environment, network restrictions, suitable for unit/integration tests. | A writable host mount, privileged container, exposed socket, or credentials can defeat isolation. GUI/Windows UI automation may not be available. | Preferred default for non-GUI tests and build validation when configured least-privilege. |
| **Virtual machine** | Separate guest OS and kernel, with isolation dependent on hypervisor, integration features, and shared folders/devices. | Stronger boundary for risky builds, untrusted test code, or Windows-specific integration. Can snapshot and revert. | Higher resource and setup cost; shared clipboard/folders/devices and network can reintroduce access; desktop interaction and licensing need planning. | Use for Windows/UI integration or higher-risk validation after threat-based review. |
| **Managed isolated sandbox** | Depends on provider; may isolate filesystem/process and optionally network. | Can provide ephemeral environments, policy enforcement, and resource limits. | Must verify actual controls, persistence, data handling, external network policy, and provider trust. | Accept only after security review and explicit data-sharing approval. |

### Recommended architecture

Use layered isolation rather than assuming one Git feature is a security
boundary:

1. Pin a clean baseline commit and create a dedicated branch/worktree for the
   approved task. Preserve any unrelated dirty user work; do not copy it into
   the task unless approved.
2. Run ordinary unit tests/builds in an ephemeral, least-privilege container
   with a read-only source mount where possible and a separate writable
   output/test directory. Disable network by default and set CPU, memory,
   process, and time limits.
3. For Windows UIA, GUI, or other OS-specific tests, use a disposable VM or
   explicitly approved isolated test account/session. Do not automate the
   user's active desktop or attach real personal credentials/devices.
4. Expose only the required test artifacts and a patch/diff back to the
   review area. Do not mount home directories, credential stores, SSH keys,
   browser profiles, or the primary checkout as writable.
5. Record image/version, command, environment, network policy, test results,
   and artifacts. Destroy ephemeral environments after preserving approved
   outputs.

Container and VM use must be validated against the actual threat model;
neither is automatically secure when privileged or broadly mounted. A
separate test environment is not permission to access unrelated data or
external systems.

## 8. Automated testing

Tests support a proposal and implementation; passing tests do not replace
human review or prove safety. The proposal must map every changed behavior
and invariant to at least one test or explicitly explain why it cannot be
automated.

### Unit tests

- Exercise pure functions, contracts, validators, classifiers, policy
  decisions, and proposal evidence generation with deterministic fixtures.
- Cover success, invalid input, ambiguity, denial, timeout, and error paths.
- Assert that forbidden side effects are not invoked on failed validation or
  denied approval.

### Integration tests

- Exercise interactions between the task runner, backend adapters,
  configuration, policy, audit, and persistence using fakes or local test
  services.
- Verify correlation IDs, event/audit semantics, timeouts, error propagation,
  and restart behavior.
- Use explicit test credentials/services only where necessary; no real user
  accounts, devices, or production endpoints by default.

### Regression tests

- Run all relevant existing tests and preserve established task states,
  fail-stop ordering, target mismatch behavior, and verification semantics.
- Add a regression test for each confirmed bug before or alongside the fix
  where feasible.
- Check compatibility for CLI and GUI entry points, configuration
  migrations, and saved data formats.
- Treat flaky tests as a reliability issue; do not simply weaken assertions
  or disable the test.

### Performance tests

- Establish a repeatable baseline before claiming an optimization.
- Measure relevant latency, throughput, memory/CPU use, and startup cost
  under declared hardware/software conditions.
- Use repeated runs and report variance; compare equivalent workloads and
  include correctness checks.
- Define an agreed threshold and confirm no unacceptable regression in
  safety, verification quality, or responsiveness.

### Proposal-completion gate

A proposal is considered technically complete when it specifies the
applicable unit, integration, regression, performance, and manual tests;
expected outcomes; environment; side-effect controls; and acceptance
thresholds. Tests requiring unavailable hardware, Windows UI, external
services, or human judgement must be listed as not performed or manual
validation—not represented as passed.

An implementation is not complete until its required automated tests and
approved sandbox validation have actually run, failures are resolved or
explicitly accepted by a human, and the resulting patch is reviewed. A test
failure or environment error must be reported, not converted into a
success-shaped fallback.

## 9. Self-improvement boundaries

The Developer Agent must never take the following actions automatically:

- deploy or install changed code into a live/user environment;
- merge a branch, create a release, publish an artifact, or push commits;
- commit, amend, rebase, reset, or discard user work without explicit,
  operation-specific approval;
- disable, weaken, bypass, or silently alter safety checks, target gates,
  policy, confirmation, sandbox restrictions, audit, logging, kill switches,
  or test protections;
- alter or delete audit records to hide an action, failure, or decision;
- grant itself, another agent, or a tool new filesystem, network,
  credential, process, desktop, or device permissions;
- read, export, or transmit secrets, browser profiles, unrelated personal
  files, raw microphone/camera/screen streams, or private logs without
  explicit scoped authorization;
- access production accounts, real smart-home devices, payment/message
  systems, or external infrastructure as test fixtures;
- rewrite its own policy, approval rules, system instructions, or sandbox
  configuration;
- mark its own proposal, patch, or tests as human-approved;
- implement a roadmap item, feature, or design solely because it appears in
  documentation or repeated usage signals.

Safety, policy, audit, approval, and isolation code is a protected change
class. Changes to those areas require explicit human approval, security
review, dedicated negative tests, and independent review before any release.
A change that prevents audit or approval from functioning is a hard stop,
not a recoverable warning.

## 10. Phase 5 roadmap

### Phase 5.1 — Repository Awareness

**Goal:** Build a local, read-only, provenance-aware view of an explicitly
selected repository and its engineering artifacts.

**Scope:** Inventory source, tests, docs, roadmap, decisions, architecture
files, commit/worktree state, and links between requirements and evidence.
Respect ignores/exclusions and label stale or unindexed content.

**Exit criteria:** The agent can answer bounded questions with precise source
references, distinguish committed state from local changes, and state when
evidence is missing. It performs no repository writes or external uploads.

### Phase 5.2 — Proposal Generation

**Goal:** Turn an evidence-backed finding into reviewable engineering
documents before code changes.

**Scope:** Generate the proposal types and required fields in Section 5;
classify findings and expose confidence, alternatives, scope, tests, risks,
and approval boundaries.

**Exit criteria:** Proposals separate facts from hypotheses, link claims to
evidence, distinguish bugs from limitations and requests, and can be reviewed
without source changes.

### Phase 5.3 — Automated Testing

**Goal:** Let a human-approved proposal identify and, when explicitly
authorized, execute an appropriate test plan.

**Scope:** Test discovery and mapping; deterministic unit and integration
tests; regression selection; opt-in performance baselines; structured
results with environment and failure evidence.

**Exit criteria:** Tests run only within approved scope/environment; results
are reproducible and accurately reported; state-changing or external tests
are gated; test failures never cause an automatic code rewrite or disablement
of the test.

### Phase 5.4 — Sandbox Validation

**Goal:** Validate an approved patch outside the user's primary working
environment.

**Scope:** Disposable worktree plus restricted container for ordinary tests;
VM or isolated Windows session where GUI/UIA validation requires it; resource
and network controls, artifact collection, cleanup, and provenance.

**Exit criteria:** A clean baseline and isolated patch are identifiable;
tests run with declared limits; the sandbox cannot access user secrets or
unapproved resources; results and patch are reviewable; cleanup does not
remove primary user data.

### Phase 5.5 — Capability Evolution Engine

**Goal:** Surface ranked, evidence-backed opportunities from permitted task,
test, and repository signals without making changes automatically.

**Scope:** Privacy-minimized signal aggregation; recurring issue and
verification weakness detection; feature/gap/optimization triage; proposal
generation and user-configurable opt-in/retention.

**Exit criteria:** Each candidate has provenance, category, confidence,
impact, evidence, and a human review path; duplicate/noisy signals can be
dismissed; no candidate changes code, roadmap, policy, or permissions without
fresh approval.

### Recommended dependency order

Implement 5.1, then 5.2. Establish the basic test catalog and result format
in 5.3 before enabling sandbox execution in 5.4. Build the 5.5 signal engine
last, after task/audit data and repository evidence have reliable schemas,
privacy controls, and retention behavior. Phase labels are proposed
milestones and do not imply prior phases or the Phase 4 foundations are
complete.

## 11. Recommendation

The smallest safe Phase 5 slice is **Phase 5.1 read-only repository
awareness for one explicitly selected checkout**:

- identify the baseline commit and worktree status;
- inventory allow-listed source, tests, and project documentation;
- build a rebuildable local index with file hashes and source references;
- answer one bounded architecture/status question with citations to
  repository files;
- demonstrate stale-index invalidation and exclusion of ignored/local
  sensitive data;
- make no code, document, configuration, network, or Git changes.

This slice is useful because it supplies verifiable context for later
proposals while adding no code-writing capability. Require tests for path
allow-listing, ignore handling, source provenance, dirty-worktree reporting,
staleness, and no-write/no-network behavior before expanding it.

Only after a human approves and the read-only slice passes should Phase 5.2
generate proposal documents. Do not begin autonomous patch generation or
execution in the initial implementation.

## Reference basis

- [PROJECT_VISION.md](./PROJECT_VISION.md) and [ROADMAP.md](./ROADMAP.md):
  current local desktop assistant goals and implementation-grounded
  milestone sequence.
- [DECISIONS.md](./DECISIONS.md): local Ollama, structured actions,
  validation, and honest verification decisions.
- [ARCHITECTURE_ALIGNMENT_REVIEW.md](./ARCHITECTURE_ALIGNMENT_REVIEW.md):
  recommendation to stage configuration, policy, audit, memory, and
  capabilities before broad autonomous integrations.
- [BACKGROUND_AUTOMATION_OPTIONS.md](./BACKGROUND_AUTOMATION_OPTIONS.md) and
  [PHASE4_EXECUTION_BACKENDS.md](./PHASE4_EXECUTION_BACKENDS.md):
  explicit capabilities, no silent backend fallback, and clear separation
  of dispatch from verification.
- [PHASE4_IMPLEMENTATION_PLAN.md](./PHASE4_IMPLEMENTATION_PLAN.md):
  proposed foundation dependencies and phased acceptance gates.
- *JARVIS Home Core — Specification v1.0*, user-provided PDF:
  modular interfaces, structured tools, sandboxed shell, human-in-the-loop
  confirmation, editable local memory, separate append-only audit, visible
  agent status, and boundaries against unsupervised irreversible actions.
