# Phase 5.2 Proposal Generation — Implementation Plan

## Purpose and status

This plan decomposes the future Proposal Generation capability defined in
[PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md). It is
a design document only; it does not authorize code changes, proposal
generation, test execution, repository writes, or automated actions.

The current Phase 5.1 implementation is a deterministic, in-memory
repository file inventory plus an in-memory Architecture Awareness model.
Repository Awareness records file path, file type, category, importance,
scan completeness, and warnings. Architecture Awareness classifies selected
Markdown documents, extracts headings, recognizes simple phase and
architecture-area associations, and resolves local Markdown document links.
It does not provide source-code symbols, source or decision semantics,
Git/revision provenance, requirement applicability, test execution
evidence, or semantic ownership and dependency resolution.

Consequently, the first Proposal Generation implementation must explicitly
limit itself to evidence it can inspect and cite. Roadmap and decision
awareness should be represented as evidence adapters over the existing
document records and directly inspected document sections, not presumed
capabilities of the current awareness APIs. Implementation should stop or
return insufficient evidence where an assertion requires unavailable
source, status, history, or test evidence.

## 1. Scope

### What Proposal Generation can do

Within one explicitly selected repository and user-specified problem scope,
Proposal Generation may:

- collect approved read-only evidence from Repository Awareness,
  Architecture Awareness, and separately validated roadmap and decision
  records;
- organize evidence into a typed, in-memory proposal record;
- classify a supported candidate as a Bug Fix, Gap, Enhancement,
  Refactoring, Architecture, or Capability Evolution proposal, or report
  that classification is uncertain;
- state problem, rationale, options, recommendation, risks, affected
  observed/estimated files, tests to consider, and unresolved questions;
- assess and explain evidence confidence and source limitations;
- render a proposal preview for human consideration.

The proposal is advice only. “Recommendation” means a reasoned option for a
human to evaluate, not a command to take action or authorization to do so.

### What Proposal Generation cannot do

- Write, edit, create, delete, rename, format, or persist files, including
  proposal documents, in the default implementation.
- Modify the repository, Git index, refs, branches, history, or worktree.
- Generate source code, patches, diffs, scripts, or executable commands.
- Execute source, tests, builds, hooks, or commands to gather evidence.
- Create commits, merges, releases, or deployments, or invoke application
  execution tools.
- Treat a complaint, future design, filename match, roadmap entry, or absent
  search result as proof of a bug, approved requirement, implementation
  gap, priority, or user consent.
- Mine conversations, task history, telemetry, or raw logs automatically
  in the smallest slice.
- Send repository content to external models or services.

Proposal Generation may identify evidence needed to resolve uncertainty,
but any further inspection that exceeds the original read-only scope,
especially test/command execution, requires a separate user decision and
authorization. It remains read-only, advisory only, non-modifying, and
non-executing.

## 2. Evidence Pipeline

### Pipeline overview

```text
User-scoped candidate
        ↓
Scope and privacy gate
        ↓
Repository Awareness inventory
        ↓
Architecture / roadmap / decision evidence adapters
        ↓
Directly inspected source or test evidence (only when requested and allowed)
        ↓
Evidence normalization, provenance, and conflict checks
        ↓
Type eligibility and confidence gate
        ↓
In-memory proposal model and preview
        ↓
Human review — no automatic action
```

Each stage must preserve evidence identity and status. Derived metadata may
help retrieve a source, but the source reference remains the basis of each
claim. If a stage cannot establish its preconditions, return a clear
incomplete/insufficient result; do not continue with fabricated defaults.

### Inputs and adapters

| Input | Current evidence available | Planned use | Limits that must be disclosed |
| --- | --- | --- | --- |
| Repository Awareness | In-memory paths, file types, categories, importance, scan completeness, warnings. | Constrain evidence discovery to files already indexed and eligible. | Does not establish file contents, code behavior, hashes, Git state, or whether absent files were excluded by incomplete scan. |
| Architecture Awareness | Document type/title/headings, simple phase and area associations, local document references, completeness and warnings. | Retrieve relevant documents and sections; classify an evidence item as documented vision/design/plan/roadmap/decision only when the source supports it. | The type/area/phase extraction is deterministic but shallow; it does not establish approval, semantic ownership, rationale, implementation, or requirement applicability. |
| Roadmap awareness | Roadmap Markdown can be discovered and directly read within scanner bounds; Architecture Awareness can identify a roadmap document and phase headings. | Preserve a roadmap statement as a plan/status claim and cite its exact document section. | A roadmap item is not an approved requirement or proof of current implementation/completion. No dedicated structured roadmap model or status reconciliation exists yet. |
| Decision awareness | Decision Markdown can be discovered and directly read; Architecture Awareness can identify a decision document and local links. | Record explicit decision text, status, rationale, and scope only when located in the source. | Current tooling does not parse or validate decision status/scope/supersession semantically. Unknown or conflicting status must remain unknown/conflicting. |
| Source code | Source files are discoverable in the inventory and may be explicitly read under the same root and file bounds by a separately scoped evidence reader. | Support claims about observed implementation only after direct inspection with exact source locators. | Repository Awareness does not parse or inspect source content. A path or name match is not implementation evidence. |
| Tests and test results | Test files can be inventoried. A user may provide a recorded result with provenance. | Distinguish test definitions from test execution evidence; use test definitions to describe planned validation. | No test execution is performed. A test file is not a passing test result. |
| User candidate | A specific user-supplied problem or request. | Define the candidate and expected scope; retain as a report unless corroborated. | A user report does not alone prove a bug, severity, priority, or permission to implement. |
| Capability Evolution signals | None in the smallest slice. | Later, ingest explicitly permitted and privacy-governed structured signals. | Do not use raw conversation/task history unless a separate phase and Phase 4 governance approve it. |

### Evidence normalization

Represent each item in a common evidence envelope before composing a
proposal:

```text
EvidenceItem
  evidence_id
  evidence_class:
    implementation | test_definition | test_run | approved_decision |
    proposed_design | roadmap_statement | user_report | signal | inference
  source_path: repository_relative_path | user_supplied_reference | unknown
  locator: line | heading | symbol | test_id | content_reference | unknown
  source_status: explicit_status | unknown | conflicting
  provenance: snapshot_or_hash | unavailable
  freshness: current_for_snapshot | stale | unknown
  inspected: true | false
  claim_summary: bounded factual description
  supports_candidate: true | false | uncertain
  limitations: list[string]
```

Evidence summaries must not be treated as stronger than their sources.
Repeated copies or derived summaries of the same source are not independent
corroboration. The pipeline should attach contradictory and limiting
evidence as well as supporting evidence.

### Type-specific evidence gates

Before a proposal is labeled substantively supported:

- **Bug Fix:** require evidence of actual behavior and an applicable
  existing contract/expectation, plus a reproducible condition or concrete
  failure record. If actual behavior was not directly observed, label it a
  report or hypothesis.
- **Gap:** require an explicit, applicable, approved requirement or
  commitment and inspection of bounded relevant implementation/tests.
  Proposed designs and future roadmap items alone do not qualify.
- **Enhancement:** require an identified existing behavior and an explicit
  user need or supported impact. Keep an optional improvement distinct from
  a correctness or safety defect.
- **Refactoring:** require concrete structure/maintenance evidence and
  behavior-preservation requirements. Performance benefit requires measured
  baseline evidence.
- **Architecture:** require current implementation/module evidence,
  applicable decisions/design constraints, and alternatives. Label
  unverified module mapping as an estimate.
- **Capability Evolution:** disabled initially. Later requires
  privacy-approved, provenance-linked signal data, stable grouping, and
  technical corroboration when claiming a cause. Signal frequency is not
  approval or priority.

If a required input is absent, partial, stale, or conflicting, the pipeline
must cap confidence or decline to produce a substantive recommendation.

## 3. Proposal Data Model

Use typed, immutable, versioned records in memory. The source repository
remains authoritative; generated proposal text is a disposable view.

```text
ProposalType
  bug_fix | gap | enhancement | refactoring | architecture |
  capability_evolution | unclassified

ProposalStatus
  needs_evidence | draft | ready_for_review

Proposal
  proposal_id
  schema_version
  proposal_type
  secondary_classifications
  status
  created_at
  scope
  repository_snapshot: identifier | unknown
  confidence
  problem
  evidence: list[EvidenceItem]
  rationale
  options: list[ProposalOption]
  recommendation
  risks: list[ProposalRisk]
  affected_files: list[AffectedFile]
  testing_strategy: list[TestRecommendation]
  assumptions: list[string]
  unresolved_questions: list[string]
  dependencies: list[EvidenceReference]
  approval_boundary

ProposalOption
  title
  description
  expected_effect
  tradeoffs
  effort: qualitative_estimate | unknown
  reversibility
  evidence_ids

Recommendation
  option_id
  rationale
  confidence_level
  assumptions
  conditions_that_change_recommendation
  advisory_only: true

ProposalRisk
  category: safety | security | privacy | compatibility |
            reliability | accessibility | operations | other
  description
  evidence_ids
  mitigation_or_open_question

AffectedFile
  path
  relationship: observed | likely | possible
  evidence_ids
  reason

TestRecommendation
  kind: unit | integration | regression | performance | manual
  objective
  expected_result
  execution_status: not_run
  side_effect_notes
  approval_required
  evidence_ids

ConfidenceAssessment
  level: high | moderate | low | insufficient
  dimensions
  explanation
  limiting_conditions
```

### Required proposal content

Each rendered proposal includes:

1. **Problem** — observed or reported condition, affected workflow, and
   bounded scope; separate facts from hypotheses.
2. **Evidence** — citations, evidence class, source status, provenance,
   freshness, counter-evidence, and inspection limits.
3. **Rationale** — impact and why the candidate may warrant consideration.
4. **Options** — reasonable alternatives, including “do nothing / defer.”
5. **Recommendation** — one advisory option and why, assumptions, confidence,
   and what evidence could change it.
6. **Risks** — applicable safety, security, privacy, accessibility,
   compatibility, reliability, and operational risks.
7. **Affected files** — observed files separately from likely/possible
   estimates, plus out-of-scope or uninspected areas.
8. **Testing strategy** — proposed tests and measurable outcomes, clearly
   marked not run; note environment and side effects.
9. **Dependencies and approval** — relevant decisions/prerequisites and
   explicit separation between proposal acceptance and implementation,
   test execution, commit, merge, or deployment authorization.
10. **Assumptions and open questions** — facts not established by the current
    evidence and the smallest safe way to resolve them.

No proposal field may contain generated code, patch content, executable
commands, or instructions designed to mechanically change the repository.

## 4. Confidence Model

Confidence describes how well the proposal's central claims and
recommendation are supported by the available evidence. It is not a
probability of success, a severity score, a measure of priority, or a
measure of approval.

Use four human-readable levels:

| Level | Meaning |
| --- | --- |
| **High** | The central problem is reproducible or directly evidenced; applicable expectations are explicit; key contradictory evidence has been checked; evidence is current and sufficiently complete for the stated scope. |
| **Moderate** | The candidate is supported, but one or more material assumptions, scope limits, or unverified effects remain. |
| **Low** | Evidence is mainly a report, indirect signal, or incomplete inspection; multiple plausible explanations remain. |
| **Insufficient** | Sources are missing, stale, unsafe to inspect, materially contradictory, or too incomplete for a defensible proposal. Do not issue a substantive recommendation; state what evidence is missing. |

Explain each assessment using these qualitative dimensions; do not assign
numeric values or calculate an aggregate:

- **Traceability:** can reviewers locate and inspect the evidence?
- **Directness:** is the claim supported directly or inferred indirectly?
- **Applicability:** is the cited requirement or decision explicitly relevant
  and in force?
- **Reproducibility:** can the observed behavior or signal be repeated or
  corroborated?
- **Completeness:** were the relevant files and counter-evidence checked?
- **Freshness:** is the evidence tied to the observed snapshot and not stale?
- **Independence:** are corroborating sources independent, rather than copied
  repetitions?

Apply non-compensating gates. For a **Bug Fix** or **Gap** proposal, if
either actual behavior or the applicable contract or requirement is not
directly evidenced, confidence is capped at **Low**; if both are missing,
confidence is **Insufficient**. Stale evidence, a partial relevant scan,
unknown or conflicting decision status, or uninspected material
counter-evidence caps confidence at **Low** or **Insufficient**, according
to impact. A user report or lexical match alone cannot support **High**
confidence. Duplicate citations and repeated summaries derived from one
source do not count as independent corroboration.

For **Capability Evolution**, do not issue a substantive recommendation
until signal provenance, privacy governance, and necessary technical
corroboration are established; otherwise leave the capability disabled or
mark confidence **Insufficient**.

State the confidence level, evidence-based rationale, applicable
dimensions, limitations, and what new evidence could change the assessment
in plain language. Do not calculate, display, or imply a numeric score,
sum, threshold, percentage, or weighted confidence value. Any future
numerical method requires a documented calibration evaluation against
human-reviewed proposals and an approved update to the design.

## 5. Human Review Workflow

### Proposal lifecycle

```text
User-scoped candidate
        ↓
Evidence collection (read-only)
        ↓
Eligibility and confidence check
        ↓
In-memory proposal draft
        ↓
Preview with citations and limitations
        ↓
Human review: accept for planning / revise / reject / request evidence
        ↓
Stop — any next capability requires separate approval
```

Proposal states:

- **Needs evidence:** required inputs are missing or the safety/scope gate
  prevents a substantive proposal.
- **Draft:** a candidate is structured but lacks one or more required
  sections or has material open questions.
- **Ready for review:** required fields and citations are present; this is
  not an approval or implementation authorization.
- **Accepted for planning:** a human explicitly accepts the proposal as
  input to a later implementation plan. This still does not authorize code
  changes or test execution.
- **Rejected / deferred / request more evidence:** human decision; retain
  only if an explicitly approved retention mechanism exists. The smallest
  slice stores no proposal history.

### Separate approval gates

No proposal may automatically result in:

- code changes or file modifications;
- test or command execution;
- commits or branches;
- merges or releases;
- deployments;
- roadmap or decision updates;
- capability or permission changes.

The approval path must keep separate human decisions for (a) accepting a
proposal for planning, (b) implementing a specific plan and file scope,
(c) executing a specific test/command/environment, and (d) committing,
merging, or deploying. Approval must identify the proposal version and
scope. Silence, previous approval, confidence assessment, and an agent-generated
status cannot count as approval.

The smallest implementation exposes only an in-memory preview and a
human-readable disposition. It has no save, export, accept-trigger, or
execution button that can initiate downstream work.

## 6. Testing Strategy

All tests below are future implementation requirements. They must use
temporary repositories, fakes, and deterministic evidence; this plan does
not execute tests.

### Unit tests

- Validate proposal/evidence schemas, required sections, allowed
  classifications, qualitative confidence levels, evidence-dimension
  explanations, and non-compensating confidence gates. Assert that no
  numeric confidence score or aggregate is calculated or displayed.
- Assert non-compensating confidence caps for incomplete, stale,
  conflicting, unapproved, and untraceable evidence.
- Ensure facts, reports, hypotheses, inferences, and source evidence retain
  distinct labels and citations.
- Verify proposal options always include “do nothing / defer.”
- Ensure likely files are labeled estimates and do not become asserted
  changes.
- Reject missing or malformed citations and empty required sections without
  converting them into a ready-for-review proposal.

### Evidence pipeline tests

- Consume repository inventory and Architecture Awareness records without
  widening root, bypassing ignores, or reading excluded files.
- Test roadmap and decision adapters using explicit, missing, conflicting,
  and superseded status fixtures; never infer approval from filename or
  recency.
- Verify partial inventory, unresolved links, stale records, unavailable
  provenance, and uninspected source/tests lower confidence or stop
  proposal readiness.
- Confirm source facts require direct bounded inspection and a stable
  locator; inventory metadata alone cannot establish behavior.
- Keep test definitions separate from recorded test runs and passing
  results.
- Ensure duplicate/derived evidence is not counted as independent
  corroboration.

### Proposal type and confidence tests

- For each of the six types, cover a supported candidate, insufficient
  evidence, and a plausible misclassification.
- Bug Fix and Gap cases require both the behavior/absence evidence and the
  applicable contract/requirement.
- Refactoring performance claims require a measured baseline.
- Capability Evolution remains disabled without permitted signal
  provenance, privacy controls, and necessary corroboration.
- Verify risk, affected-file, testing, assumptions, and approval-boundary
  sections accurately represent the input evidence.

### Human workflow and safety tests

- Preview is in-memory and does not create, modify, or delete files or Git
  state.
- No code/patch/command output is produced; no test, subprocess, network,
  desktop, credential, or external service is invoked.
- Accept, reject, revise, request evidence, and silence cannot trigger
  implementation, execution, commit, merge, or deployment.
- Prompt-injection-like repository text is treated as data and cannot alter
  scope, permissions, or approval requirements.
- Sensitive or out-of-scope fixtures do not appear in proposal content or
  logs.

### Regression and acceptance tests

- Preserve Repository Awareness and Architecture Awareness behavior and
  their read-only guarantees.
- Test a small fixed set of example scenarios with expected evidence,
  confidence ratings, unresolved questions, and output sections.
- Snapshot the fixture repository before/after proposal generation and
  assert identical file contents/tree and Git metadata.
- Human reviewers evaluate usefulness, traceability, classification,
  confidence explanations, clarity, and whether uncertainty is
  appropriately surfaced before enabling additional proposal types.

## 7. Safety Constraints

Proposal Generation remains:

- **Read-only:** it may read only evidence in an explicitly selected,
  bounded scope. No persistent proposal storage in the initial slice.
- **Advisory only:** it describes options and an evidence-based
  recommendation but cannot accept the proposal or authorize next steps.
- **Non-modifying:** no repository, filesystem, or Git mutations; no
  document export by default.
- **Non-executing:** no source, tests, builds, hooks, commands, desktop
  actions, or external service calls.
- **No code generation:** no code, patches, diffs, shell, executable
  instructions, or mechanically applicable change recipe.
- **Evidence-constrained:** incomplete, stale, unknown, or conflicting
  records remain visible; never treat a proposal/design/roadmap claim as
  verified implementation.
- **Privacy-preserving:** local-only by default; never ingest secrets,
  unrelated personal data, raw screenshots, or task history without a
  separately approved policy.
- **Prompt-injection resistant:** repository content is untrusted data and
  cannot override the authorized scope, safety rules, or human approval.
- **Least authority:** no access to tools or capabilities that could write,
  execute, commit, merge, or deploy.

If an input cannot be safely inspected or a required status cannot be
established, stop or return “needs evidence.” Do not make an ungrounded
recommendation to appear helpful.

## 8. Success Criteria

The implementation is ready for human review when:

1. It accepts one user-scoped candidate and uses only explicitly authorized
   repository evidence.
2. Repository Awareness, Architecture Awareness, roadmap statements, and
   decision records are represented as distinct evidence sources with
   source-relative locators and honest provenance.
3. Current API limitations are reflected: inventory metadata is not source
   behavior, headings/links are not semantic proof, and roadmap/decision
   status is not inferred.
4. All six proposal types have evidence gates and can remain unclassified
   or needs-evidence when requirements are unmet.
5. The data model contains problem, evidence, rationale, options,
   recommendation, confidence, risks, affected files, test strategy,
   assumptions, dependencies, and approval boundaries.
6. Qualitative confidence assessments are explainable, and non-compensating
   gates prevent a High assessment from hiding critical missing evidence.
   No numeric confidence score is calculated or displayed.
7. A human-readable preview distinguishes observed from estimated files,
   test definitions from test runs, and facts from reports/hypotheses.
8. Tests demonstrate no writes, no execution, no network use, no code or
   patch generation, and no approval-to-action coupling.
9. Proposal acceptance, test execution, implementation, commit, merge, and
   deployment are separately gated; no proposal can trigger them.
10. A human evaluation confirms the smallest slice is useful and that
    qualitative confidence explanations surface uncertainty accurately.
    Any future numerical confidence model remains out of scope until a
    calibration method has been validated against reviewed proposals and
    approved through a design update.

## 9. Smallest Safe Slice

The minimum useful implementation is a **single-request,
in-memory Enhancement Proposal preview** for a user-supplied candidate:

1. Accept a narrowly scoped enhancement request; do not mine conversation
   history or automatic capability signals.
2. Build a fresh bounded repository inventory and Architecture Awareness
   model for one selected root.
3. Use only direct source/document evidence explicitly inspected for the
   question; distinguish roadmap, decision, proposed design, implementation,
   and user-report evidence. If direct evidence is unavailable, return a
   needs-evidence response rather than a substantive proposal.
4. Populate typed sections for problem, evidence, rationale, options
   (including do nothing/defer), advisory recommendation, confidence,
   risks, observed/estimated affected areas, proposed tests, assumptions,
   and approval boundaries.
5. Render in memory with repository-relative citations and explicit
   limitations.
6. Create no files; generate no code, patches, or commands; run no tests or
   repository commands; make no network calls; and do not trigger any
   approval or downstream action.

Bug Fix proposals should be enabled only when both actual behavior and an
applicable contract are directly evidenced. Gap proposals require explicit
approved requirements and bounded implementation inspection. Refactoring,
Architecture, and Capability Evolution proposals should remain deferred
until the associated traceability, source, measurement, signal-governance,
and confidence gates have been validated.

## Reference basis

- [PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md):
  proposal types, evidence, structure, confidence, human review, and safety.
- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md):
  finding definitions, supervised workflow, and approval boundaries.
- [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md):
  Phase 5 sequence, dependencies, and Phase 5.2 delivery goals.
- [PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md)
  and [PHASE5_1_IMPLEMENTATION_PLAN.md](./PHASE5_1_IMPLEMENTATION_PLAN.md):
  repository evidence scope, limitations, provenance, and safety.
- [PHASE5_1_ARCHITECTURE_AWARENESS.md](./PHASE5_1_ARCHITECTURE_AWARENESS.md)
  and
  [PHASE5_1_ARCHITECTURE_AWARENESS_IMPLEMENTATION_PLAN.md](./PHASE5_1_ARCHITECTURE_AWARENESS_IMPLEMENTATION_PLAN.md):
  architecture records, relationships, query semantics, and current
  implementation boundaries.
- [scripts/repository_awareness.py](./scripts/repository_awareness.py),
  [scripts/architecture_awareness.py](./scripts/architecture_awareness.py),
  [tests/test_repository_awareness.py](./tests/test_repository_awareness.py),
  and [tests/test_architecture_awareness.py](./tests/test_architecture_awareness.py):
  implementation and test evidence to revalidate before any future coding.
