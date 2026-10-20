# Phase 5 Review

## Completed Capabilities

The implemented Phase 5 work is a constrained foundation for repository
understanding and human-reviewed proposals:

- **Repository Awareness (`scripts/repository_awareness.py`)** builds a
  bounded, in-memory inventory for an explicitly selected repository root.
  It classifies supported source, documentation, and configuration files,
  applies hard exclusions and `.gitignore` rules, avoids following symbolic
  links, and reports limits, warnings, excluded items, and whether the scan
  is complete. A snapshot can be explicitly refreshed.
- **Architecture Awareness (`scripts/architecture_awareness.py`)** consumes
  that inventory and reads candidate Markdown documents to build in-memory
  metadata for document types, titles, headings, explicit phase associations,
  architecture areas, and local document links. It exposes lookups by
  document type, phase, and area and reports unresolved references and
  incomplete inputs.
- **Proposal Representation (`scripts/proposal_model.py`)** defines frozen
  records for proposals, evidence, qualitative confidence, options,
  recommendations, risks, and test recommendations. The model covers five
  proposal types and performs structural and status-specific validation.
  This is a data model, not a proposal generator.
- **Proposal Construction (`scripts/proposal_construction.py`)** constructs
  Enhancement proposals only from explicitly supplied repository and
  architecture awareness records and caller-provided evidence, options, and
  recommendation. It does not search for gaps or inspect source contents to
  invent evidence or recommendations. Missing or uncertain required inputs
  result in a `NEEDS_EVIDENCE` proposal.
- **Proposal Validation (`scripts/proposal_validation.py`)** evaluates
  Enhancement proposal structure, evidence metadata, confidence,
  completeness, and review eligibility. It returns `ACCEPT`,
  `NEEDS_EVIDENCE`, or `REJECT` with categorized reasons. `ACCEPT` means
  eligible for human review, not approval to implement.
- **Proposal Review Workflow (`scripts/proposal_review_workflow.py`)**
  requires a matching validation result and admits only an eligible
  `READY_FOR_REVIEW` Enhancement proposal to human review. It records the
  validator outcome and explicit human dispositions in frozen, in-memory
  records. Exact scope acknowledgement is required; a request for evidence
  must include a question. No disposition triggers downstream work.

The current status records focused and full-suite test results for these
slices in [PROJECT_STATUS.md](./PROJECT_STATUS.md). Those tests verify the
implemented contracts; passing them does not establish the unimplemented
Phase 5.3–5.5 capabilities.

## Remaining Capabilities

The current code does not implement the full capabilities in
[PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md) or the later phases
of [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md):

- **Repository provenance and change awareness:** no persistent or
  rebuildable manifest with file hashes/revision IDs, source-symbol index,
  Git baseline commit/branch/worktree status, or committed-versus-uncommitted
  evidence model.
- **Evidence-linked answers:** no query/answer layer that synthesizes
  bounded findings from repository evidence, resolves source claims to
  revisions, or separates approved requirements, proposals, implementation
  facts, and hypotheses in generated answers.
- **Complete proposal generation:** no orchestrator that discovers and
  classifies candidate findings, generates the full set of proposal forms,
  or assembles evidence-backed design documents, implementation plans,
  architecture reviews, roadmap proposals, or refactoring suggestions.
  Construction currently supports only a caller-supplied Enhancement
  proposal; other proposal types are representable but not constructed or
  quality-validated by this slice.
- **Proposal UI and persistence:** no review queue, UI, durable proposal
  store, durable audit history, reviewer identity integration, or
  cross-session lifecycle.
- **Phase 5.3 Automated Testing:** no test discovery/catalog, proposal-to-test
  mapping, approved test request, command preview/approval workflow,
  controlled execution service, or structured execution result model.
  The presence and execution of unit tests in development are not an
  implementation of this agent capability.
- **Phase 5.4 Sandbox Validation:** no disposable worktree/container/VM
  lifecycle, sandbox policy enforcement, environment verification, artifact
  collection, or cleanup verification.
- **Phase 5.5 Capability Evolution:** no opt-in signal ingestion, privacy
  and retention controls, normalization, recurrence detection, ranking,
  candidate queue, or signal-derived proposal workflow. The current review
  record is not a persistent candidate queue.
- **Cross-cutting foundations:** no end-to-end integration with durable
  Phase 4 policy, audit, configuration, or memory foundations is established
  by the reviewed modules. Their completion must not be inferred from this
  Phase 5 code.

## Current Architecture

The reviewed modules form a sequential, caller-orchestrated, in-memory
pipeline. They do not provide a top-level agent or autonomous coordinator.

```text
Caller selects repository root
             |
             v
RepositoryIndex.build(root)
  bounded file inventory, exclusions, warnings
             |
             v
ArchitectureKnowledgeModel.build(index)
  reads indexed Markdown; derives document metadata and links
             |
             |  caller explicitly supplies ProposalEvidenceInput
             |  with evidence, options, and recommendation
             v
construct_enhancement_proposal(index, architecture, input)
  validates supplied metadata; returns immutable Proposal
             |
             v
validate_proposal(proposal)
  ACCEPT | NEEDS_EVIDENCE | REJECT
             |
             v
begin_proposal_review(proposal, validation)
  blocked state or Ready For Review
             |
             | explicit human disposition and scope acknowledgement
             v
record_human_disposition(...)
  immutable in-memory record; no downstream action
```

The primary data flow is typed, immutable records passed through Python
functions. Repository indexing and architecture-document reading are the
only repository-facing operations in the reviewed modules. Proposal
construction, validation, and review operate on supplied in-memory values.
The modules have no persistence or UI layer and expose no execution or
code-writing interface.

This is a foundation pipeline, not yet an integrated Developer Agent:
selection, evidence gathering, calls between stages, presentation to a
reviewer, and lifecycle management are performed by an external caller.

## Safety Boundaries

The reviewed design and implementation establish these boundaries:

- **Read-only repository awareness:** scanning creates an in-memory index;
  the scanner excludes sensitive-looking names and artifact types, respects
  discovered ignore rules, bounds traversal, and does not follow symbolic
  links. Architecture Awareness reads only indexed Markdown candidates,
  checks paths remain under the repository root, and reports incomplete or
  unresolved inputs.
- **Explicit evidence only:** Proposal Construction does not scan for gaps,
  inspect code to create claims, generate recommendations, or infer missing
  evidence. Evidence, options, and recommendations are supplied explicitly.
- **Advisory validation:** validation checks representation and declared
  evidence metadata; it cannot prove that evidence claims are true or
  independently establish that a behavior is reproducible.
- **Human review gate:** only a matching `ACCEPT` result for a
  `READY_FOR_REVIEW` Enhancement proposal reaches the ready state. Blocked
  results cannot receive a human disposition through the workflow.
- **No implied implementation authority:** `accepted_for_planning` is a
  review disposition only. It does not authorize implementation, testing,
  repository changes, commits, pushes, or deployment.
- **No execution or generated changes:** the reviewed modules create no
  code, patches, commands, or automated actions. Review and audit records
  exist only in memory and are not durable or tamper-evident audit storage.

These are boundaries of the reviewed modules, not a guarantee about every
caller or the whole application. Any integration must preserve explicit
scope, approval, and side-effect controls and must not treat repository
content or model output as permission.

## Gaps Before Capability Evolution

Capability Evolution should not begin until its evidence sources and
governance can support reliable, privacy-conscious decisions. Key gaps are:

1. **Reliable repository baseline and provenance.** Add a clear relationship
   between evidence and a specific revision/worktree state, including
   hashes or equivalent invalidation facts. Report dirty or incomplete
   inputs rather than silently treating them as committed baseline.
2. **Structured test evidence.** Phase 5.3 must discover tests and represent
   test plans and actual results separately. A test definition, a proposed
   test, and an executed result must remain distinct evidence classes.
3. **Safe execution boundary.** Before running untrusted or side-effectful
   tests, require exact human approval and verify the command, revision,
   environment, permissions, network policy, resource limits, and result
   provenance. A branch or worktree alone is not a sandbox.
4. **Privacy and retention governance.** Define opt-in signal sources,
   minimization, redaction, retention, deletion, and exclusion rules before
   importing task, tool, user, or test-history signals. Do not ingest raw
   transcripts or screenshots by default.
5. **Durable audit and review lifecycle.** The current review records are
   transient. Any signal engine or review queue needs a separately designed,
   access-controlled, privacy-aware, traceable storage layer before relying
   on historical decisions or behavior.
6. **Candidate quality and uncertainty handling.** Establish stable signal
   schemas, deduplication, confidence calibration, category definitions,
   impact/priority criteria, and links back to original evidence and
   revision. Frequency must not be treated as proof, severity, or user
   approval.
7. **Integration and negative testing.** Demonstrate that blocked,
   incomplete, stale, or low-confidence inputs cannot create actionable
   candidates, bypass approvals, trigger execution, or alter code,
   permissions, roadmap, or policy.

Capability Evolution can begin only as a supervised signal collector and
triage service. It must surface explainable candidates for human review and
must not change project state automatically.

## Recommended Phase 5.3 Direction

Proceed with **Phase 5.3 — Automated Testing**, beginning with the smallest
non-executing slice: test discovery and proposal-to-test mapping. This
builds on the existing proposal `testing_strategy` records while avoiding
premature command execution.

Recommended increments:

1. Inventory test files, framework/configuration, fixtures, and known
   platform requirements from explicitly selected repository evidence.
   Record missing or malformed configuration as incomplete; do not invent a
   runnable command.
2. Define immutable test-plan and test-result records that distinguish
   proposed, approved, blocked, not-run, failed, and passed states, and
   record revision/environment provenance when known.
3. Map a specific proposal and changed behavior to unit, integration,
   regression, performance, and manual checks. Identify side effects and
   approval requirements; mark unavailable validation as not performed.
4. Add a human-readable preview and explicit approval contract bound to the
   exact test selector/command, revision, working directory, environment,
   timeout, network policy, and permitted side effects.
5. Keep execution out of the initial slice. Design and test controlled
   execution only after its policy and isolation requirements are reviewed;
   later execution must report denial, timeout, interruption, environment
   failure, and partial results distinctly and never as success.

This direction follows the dependency order in the Phase 5 implementation
plan: reliable repository evidence and proposals first, testing contracts
next, sandbox validation before higher-risk execution, and Capability
Evolution last. It does not authorize running tests or adding an execution
backend.

## Risks

- **Overstating implementation:** Phase 5 design documents describe a much
  broader Developer Agent than the current modules implement. Treating
  represented proposal types as generated/validated capabilities, or
  treating development test runs as Phase 5.3, would misstate progress.
- **Evidence can be stale or misattributed:** the current inventory records
  metadata rather than content hashes or a Git revision; a later consumer
  could conflate indexed files, current files, committed changes, and local
  modifications.
- **Metadata is not verification:** Construction relies on supplied
  evidence metadata and does not inspect evidence content. Validation
  cannot prove claims, and an `ACCEPT` result is a quality gate rather than
  proof of correctness.
- **Transient auditability:** frozen audit entries are immutable objects,
  but they are not persisted, tamper-evident, or a complete historical
  record. They can be lost when the process ends.
- **Integration can widen authority:** a future caller could invoke
  filesystem, test, or action APIs beyond these module boundaries. The
  current read-only contracts do not substitute for enforcement at an
  execution boundary.
- **Incomplete awareness may mislead:** bounded scans and excluded files
  can omit relevant context. Warnings and `complete` flags must be surfaced
  rather than hidden.
- **Privacy exposure:** source paths, claims, reviewer rationale, or
  evidence metadata may be sensitive. The current workflow does not provide
  durable storage controls or an end-to-end redaction/retention policy.
- **Human review ambiguity:** `accepted_for_planning` could be mistaken for
  implementation approval unless every interface clearly communicates its
  limited meaning and obtains separate approval for later actions.

## Successes

- The implementation has advanced in small, reviewable increments with
  explicit design and implementation plans.
- Awareness, proposal construction, validation, and review are separated
  into focused modules with typed immutable records.
- Repository scanning has explicit bounds, exclusions, incomplete-state
  reporting, and a manual refresh rather than a persistent, authoritative
  index.
- Proposal Construction is deliberately evidence-fed rather than an
  autonomous gap finder or recommender.
- Validation makes uncertainty and missing evidence explicit, and the
  review workflow distinguishes validator decisions from human dispositions.
- The human-review boundary leaves the proposal unchanged and does not
  expose implementation, patch, test-trigger, or repository-write actions.
- Focused and full-suite test results are recorded in
  [PROJECT_STATUS.md](./PROJECT_STATUS.md), providing regression evidence
  for the delivered slices.

## Next Milestone Recommendation

Approve **Phase 5.3.1: Read-only Test Inventory and Proposal-to-Test
Mapping** as the next milestone. Its exit criteria should be:

- Given an explicitly selected repository snapshot, return an immutable
  inventory of discovered test files, relevant test configuration, and
  platform/fixture notes, with incomplete or unknown findings stated
  explicitly.
- Given a supplied proposal, map its stated behavior and risks to proposed
  automated and manual checks, including expected outcomes and side-effect
  notes.
- Keep discovery and test planning read-only: no command execution,
  subprocesses, network access, filesystem writes, code generation, or
  automatic fixes.
- Clearly distinguish a test that is merely present or recommended from a
  test that has actually run; do not claim a pass without a recorded result.
- Add focused tests for missing/malformed configuration, incomplete
  inventories, evidence references, proposal mappings, and blocked or
  not-run states.
- Update project status only after implementation and tests verify these
  criteria.

After this milestone is accepted, separately design the approved test
request and execution boundary. Sandbox validation and signal-driven
Capability Evolution remain later milestones.
