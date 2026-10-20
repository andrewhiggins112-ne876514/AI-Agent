# Phase 5.3 Options

## Option A - Testing Awareness

### What it is

Add a read-only test inventory and proposal-to-test mapping capability.
It would identify test files, frameworks, configuration, fixtures, and known
platform constraints from an explicitly selected repository snapshot. For a
supplied proposal, it would describe relevant unit, integration, regression,
performance, and manual checks, expected outcomes, and possible side effects.
It would distinguish a test that exists or is recommended from one that has
actually run.

The initial scope would not execute tests or commands. Any later execution
would require a separate approval and safety design.

### Benefits

- Builds directly on the current repository inventory and proposal
  `testing_strategy` fields.
- Makes test coverage and validation gaps visible without expanding the
  system's authority.
- Creates the test-plan and result concepts needed before sandboxed test
  execution or signal-driven improvement work.
- Reduces the risk of inventing runnable commands from incomplete or
  malformed project configuration.
- Fits the dependency order in the Phase 5 implementation plan: establish
  test discovery and result formats before sandbox validation.

### Risks

- Test configuration and names can be incomplete or misleading; discovery
  must not imply that a test is safe or runnable.
- A proposed mapping may omit behavior or side effects if source and test
  evidence are incomplete.
- Future execution could be mistakenly assumed to be included unless the
  non-executing boundary is explicit.
- Test inventory may inherit stale or incomplete repository evidence because
  current awareness does not bind files to a Git revision or content hash.

### Approximate effort

**Small to medium** for a read-only inventory and mapping slice with focused
tests. Effort becomes **large** if the scope expands to approved command
execution, result parsing, environment capture, or user-interface
integration. These are relative estimates; exact effort depends on the
repository's supported test configurations and integration scope.

## Option B - Sandbox Validation

### What it is

Build the ability to validate an explicitly approved patch in a disposable,
restricted environment, with a known baseline, bounded commands and
resources, controlled network and filesystem access, traceable results, and
verified cleanup. The proposed architecture uses a worktree for revision
management together with a least-privilege container for ordinary tests,
and a disposable VM or isolated Windows session where GUI validation is
required.

This option is distinct from merely creating a branch or worktree; neither
alone provides runtime or host-resource isolation.

### Benefits

- Provides a safer and more reproducible place to validate approved changes.
- Can limit exposure of the user's primary checkout, credentials, desktop,
  and unrelated files during testing.
- Produces result and artifact provenance tied to a patch and environment.
- Is a necessary dependency for higher-risk test execution and meaningful
  sandbox-validation claims.

### Risks

- Container mounts, privileges, control sockets, shared folders, clipboard,
  credentials, or network access can defeat intended isolation.
- A sandbox manager and cleanup process could affect host resources or user
  data if incorrectly scoped.
- Windows GUI/UIA testing adds VM, interactive-session, and environment
  complexity.
- Dependency installation may execute untrusted build hooks or contact
  external services.
- Building this before a test-request/result contract exists risks
  implementing infrastructure without a clear, bounded workload.

### Approximate effort

**Large to extra large.** Even a non-GUI container path requires threat
analysis, environment verification, command controls, resource limits,
artifact collection, failure/cancellation handling, and cleanup tests.
Cross-platform GUI support or automated VM lifecycle would increase effort
substantially.

## Option C - Proposal Quality Improvements

### What it is

Strengthen the existing in-memory proposal pipeline without adding
autonomous finding, code generation, or execution. Improvements could focus
on evidence provenance and freshness, binding evidence to a repository
revision or snapshot, clearer distinctions between facts and hypotheses,
review record traceability, and quality gates for completeness and
confidence across the supported proposal types.

This is a broad option rather than a single defined feature; it would need
to be narrowed to a concrete, measurable deficiency before implementation.

### Benefits

- Improves the trustworthiness of proposal review before adding more
  powerful capabilities.
- Addresses a documented limitation: current evidence metadata is supplied
  by callers and is not independently verified or bound to content hashes
  or Git revision.
- Could reduce stale or misattributed evidence and prevent an `ACCEPT`
  quality result from being mistaken for proof of correctness.
- Preserves the current read-only, advisory model and can be delivered
  incrementally.

### Risks

- Scope can expand into persistence, Git integration, schema migrations, or
  review UI unless boundaries are explicit.
- Better metadata and validation still cannot prove that a claim is true or
  that a behavior reproduces.
- Changes to proposal schemas may affect existing constructors, validation,
  tests, and serialized or future persisted data.
- Without a specifically identified shortcoming and acceptance measure,
  quality work could add process without a demonstrable improvement.

### Approximate effort

**Small to medium** for one bounded improvement, such as attaching snapshot
identity and freshness metadata to supplied evidence with focused
validation. **Medium to large** if generalized across proposal types or
expanded to Git status, durable review history, UI, and migrations.

## Option D - Capability Evolution Engine Foundations

### What it is

Establish groundwork for later signal-based opportunity triage, without
automatically collecting sensitive history or implementing candidates. A
strictly bounded foundation could define privacy-minimized signal schemas,
source and provenance requirements, category/uncertainty rules, and
candidate deduplication and ranking criteria. Actual ingestion of runtime
task/tool history would depend on approved opt-in, retention, deletion, and
durable audit controls.

This option means foundations only; it is not the full Capability Evolution
Engine and does not imply that signals may change code, roadmap, policy, or
permissions.

### Benefits

- Clarifies the data and governance prerequisites for future signal-driven
  candidate triage.
- Helps prevent raw conversations, screenshots, and sensitive logs from
  becoming default inputs.
- Can define how candidates retain provenance and uncertainty, and why
  frequency alone is not proof of importance or approval.
- Provides a path toward supervised improvement while retaining human
  control.

### Risks

- The current review records are transient, and durable Phase 4 audit,
  privacy, and retention foundations are not established by the reviewed
  Phase 5 modules.
- Building schemas without reliable repository revisions and structured
  test results may produce weak or untraceable candidates.
- Even metadata-only signals can reveal private behavior or project
  activity.
- Early ranking can create false confidence, noise, or a misleading sense
  that popular requests are approved priorities.
- The work may create abstractions that need redesign once actual,
  privacy-approved signal sources exist.

### Approximate effort

**Medium** for governance and schema foundations alone; **large to extra
large** for a useful engine with ingestion, privacy controls, retention,
deduplication, ranking, review lifecycle, and durable provenance. The latter
also depends on reliable test results and applicable Phase 4 audit/privacy
controls.

## Recommendation

Choose **Option A - Testing Awareness**, starting with a read-only test
inventory and proposal-to-test mapping. It is the best next step after the
current implementation because it extends repository and proposal awareness
without introducing command execution, while establishing structured test
evidence needed by later sandbox validation and Capability Evolution.

Keep the first increment explicitly non-executing: inventory what is
present, map supplied proposals to candidate checks, report uncertainty and
side-effect concerns, and distinguish recommended tests from executed
results. Defer command execution until its exact approval contract and
runtime boundary are separately reviewed. Revisit Option C if a concrete
proposal-quality defect blocks this work; defer Option B until test
execution needs and result contracts are established; defer Option D until
repository provenance, structured test results, and privacy/retention
governance are dependable.
