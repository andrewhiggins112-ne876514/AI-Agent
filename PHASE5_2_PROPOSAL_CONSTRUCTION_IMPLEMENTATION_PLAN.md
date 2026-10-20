# Phase 5.2.2 Proposal Construction — Implementation Plan

## Purpose and status

This plan defines a future, minimal implementation of the Proposal
Construction design in
[PHASE5_2_PROPOSAL_CONSTRUCTION.md](./PHASE5_2_PROPOSAL_CONSTRUCTION.md).
It does not implement the capability or authorize repository actions.

The implementation remains read-only, advisory only, non-modifying, and
non-executing. Its output is an immutable `Proposal` held in memory for
human review. It does not search for candidates, inspect additional files,
or invoke any downstream action.

## 1. Scope

### Included in the smallest slice

Implement an explicit-input constructor for one user-provided
**Enhancement Proposal** candidate. It will:

1. Accept an already-built `RepositoryIndex` and
   `ArchitectureKnowledgeModel` for one selected repository.
2. Accept a bounded candidate, scope, and a tuple of explicitly supplied
   `EvidenceItem` values. The caller must supply all evidence claims and
   locators; the constructor will not read evidence sources.
3. Check input types, repository-root consistency, evidence identity and
   structure, indexed path membership, relevant awareness warnings and
   completeness, and Enhancement-specific evidence requirements.
4. Assign one qualitative confidence level and explanatory assessments
   across the seven existing confidence dimensions. No numeric score or
   aggregation is used.
5. Assemble a `Proposal`, call its structural `validate()` method, and
   return either that in-memory record or explicit validation/construction
   errors.

### Explicitly excluded

- Automatic candidate discovery, task-history mining, telemetry, or
  Capability Evolution.
- Creating or refreshing awareness indexes within the constructor.
- Reading source files, tests, or documents; running tests or commands.
- Proposal types other than Enhancement.
- Saving, exporting, rendering to a file, or persisting proposals.
- Code generation, patches, diffs, implementation instructions, or
  automated actions.
- Changes to `proposal_model.py`, Repository Awareness, or Architecture
  Awareness in this implementation slice.

Repository Awareness and Architecture Awareness currently expose
read-only builders that inspect a bounded repository. The construction
function must not call those builders; it only accepts their already-built
in-memory results supplied by its caller.

## 2. Evidence Inputs

### Explicit inputs

The constructor accepts:

- **Repository index:** the caller-supplied `RepositoryIndex`, including
  its indexed paths, `complete` flag, `excluded_count`, warnings, timestamp,
  root, and configured limits.
- **Architecture model:** the caller-supplied
  `ArchitectureKnowledgeModel`, including document metadata,
  relationships, `complete` flag, warnings, and root.
- **Evidence items:** explicitly supplied `EvidenceItem` values. For an
  Enhancement eligible for `READY_FOR_REVIEW`, these must include:
  - an `IMPLEMENTATION` item describing existing behavior, with a path
    present in the supplied index and a non-empty locator; and
  - a `USER_REPORT` item describing the stated need, with a locator or
    limitation that explains its provenance.

The candidate and scope are explicit constructor arguments. A user
candidate is not implementation evidence. If the candidate is itself
represented by an evidence item, preserve its `USER_REPORT` class.

### Use of Repository Awareness

Use the supplied `RepositoryIndex` only to:

- confirm the `IMPLEMENTATION` evidence path is among indexed paths;
- confirm the awareness inputs refer to the same resolved repository root;
- disclose `complete`, exclusions, warnings, and scan limits; and
- identify that an indexed path is metadata, not proof of its contents.

An indexed path, category, file type, or importance value cannot create an
`IMPLEMENTATION` claim or establish file behavior. If the path is absent
from the supplied index, reject that evidence as out of indexed scope; do
not search for it.

### Use of Architecture Awareness

Use the supplied `ArchitectureKnowledgeModel` only as contextual metadata:

- recognize an explicitly supplied document path and its
  `ArchitectureDocumentType`, title, headings, phase/area associations,
  and relationships;
- retain the model's completeness and warnings as limitations; and
- avoid treating a heading, link, phase association, or document type as
  semantic proof, approval, requirement applicability, or implementation.

Architecture metadata is optional context for this Enhancement slice. It
cannot replace either required Enhancement evidence item. A document
evidence claim must be explicitly supplied as an `EvidenceItem`; the
constructor must not promote roadmap or proposed-design metadata into an
approved decision.

### Evidence that cannot be inferred

The current awareness records do not establish source contents, Git
revision/worktree state, a decision's approval or supersession, or whether
a test ran. Do not infer these facts. Preserve the supplied
`EvidenceProvenance`, `EvidenceFreshness`, `Applicability`, and limitations;
unknown values remain unknown. Test recommendations remain
`TestExecutionStatus.NOT_RUN`.

## 3. Construction Pipeline

```text
Explicit RepositoryIndex + ArchitectureKnowledgeModel + candidate + evidence
                                      ↓
                               Input validation
                                      ↓
                         Evidence and eligibility checks
                                      ↓
                       Qualitative confidence assessment
                                      ↓
                       In-memory Proposal construction
                                      ↓
                            Proposal.validate()
                                      ↓
                    Proposal or explicit error outcome
```

### 1. Evidence

Receive only values explicitly passed to the function. Do not invoke
`RepositoryIndex.build`, `RepositoryIndex.refresh`,
`ArchitectureKnowledgeModel.build`, or
`ArchitectureKnowledgeModel.from_repository`; do not read paths, resolve
links by additional I/O, or call external services.

### 2. Validation

Check non-empty candidate/scope, expected model instances, matching
repository roots, unique evidence IDs, typed evidence fields, allowed
repository-relative paths and locators, and membership of repository paths
in the supplied index. Preserve warnings, incomplete scans, conflicts,
unknown statuses, and evidence limitations. Confirm the two required
Enhancement evidence classes and prevent derived metadata from being
counted as independent evidence.

If the evidence envelope is structurally invalid, return an explicit
failure with reasons and create no `READY_FOR_REVIEW` proposal. If the
candidate is representable but lacks sufficient support, use
`NEEDS_EVIDENCE` only when an explicit evidence item and concrete
unresolved questions can be retained. Do not fabricate a rejected or
unclassified `ProposalStatus`; neither status exists in the model.

### 3. Confidence assessment

Select `HIGH`, `MODERATE`, `LOW`, or `INSUFFICIENT` qualitatively. Populate
all seven `ConfidenceDimensionAssessment` entries with non-empty
rationales when constructing a ready-for-review record. Explain the effect
of incomplete indexes, warnings, unknown freshness/provenance,
non-applicable evidence, or conflict. Do not calculate numeric ratings,
weights, totals, percentages, thresholds, or probabilities.

For this smallest slice, a material incomplete scan, unknown or conflicting
applicability, or unverified central evidence prevents `HIGH`. If existing
behavior or the user need is not directly evidenced, do not mark the
proposal ready for review; retain the missing evidence as unresolved.

### 4. Proposal creation

Assemble an immutable `Proposal` using values from the explicit inputs.
Include the candidate, scope, evidence, rationale, qualitative confidence,
affected area labels only when supported, assumptions and unresolved
questions, at least two options including a defer option for
`READY_FOR_REVIEW`, and an advisory recommendation only when supported.
Keep any test recommendations at `NOT_RUN`.

Call `Proposal.validate()` and surface every returned error. A
validation-passing record is structurally valid only; construction's
evidence gates remain responsible for substantive eligibility. Return the
proposal in memory and stop.

### Proposed module boundary

Add a focused `scripts/proposal_construction.py` module containing a
single public construction function and a small explicit result type if
needed to distinguish a constructed proposal from validation errors.
It imports the existing awareness record types and proposal model; it
does not modify them. Keep policy checks in the construction function
unless tests show a specific reusable helper is needed.

No separate reader, scanner, persistence layer, confidence scoring
framework, adapter registry, or generic multi-proposal orchestration is
needed for this slice.

## 4. Eligibility Rules

### Minimum for a ready Enhancement Proposal

- One explicit, non-empty candidate and bounded scope.
- Both awareness objects were supplied and refer to the same repository
  root.
- The supplied index is complete for the stated evidence scope; if it is
  incomplete, exclusions or warnings affect the claim, do not claim
  completeness or absence.
- At least one traceable `IMPLEMENTATION` item whose repository-relative
  source path is present in the supplied index.
- At least one explicit `USER_REPORT` item representing the stated user
  need.
- Evidence IDs are unique; claims, locators, paths, provenance, freshness,
  applicability, and limitations conform to the model.
- No unresolved material contradiction prevents an evidence-based
  recommendation.
- Confidence is not `INSUFFICIENT`; the record includes the required
  confidence dimensions, defer option, recommendation, and other
  ready-for-review structure accepted by `Proposal.validate()`.

Index membership is only a scope check. It does not independently verify
the implementation claim. The evidence item must be supplied with a
specific locator and honest provenance; this implementation does not
inspect that locator.

### Reject construction

Return an explicit error outcome, without a substantive proposal, when:

- required awareness objects are missing, malformed, or have different
  roots;
- candidate or scope is empty;
- an evidence item is malformed, duplicated, untraceable, or references a
  path outside the supplied index;
- the evidence is outside authorized scope or cannot safely be represented;
- an invalid or unsupported proposal type is requested; or
- model validation fails.

Do not silently drop invalid evidence or replace errors with defaults.

### Insufficient evidence

When the candidate is in scope but evidence is incomplete, contradictory,
stale, or not directly supported, return `NEEDS_EVIDENCE` only if it can
truthfully preserve the candidate, supplied evidence, and specific
unresolved questions. It must have no unsupported substantive
recommendation. Otherwise return an explicit insufficient-evidence
outcome without a `Proposal`.

An incomplete index, architecture warning, or absent metadata is not proof
that a feature or implementation is absent. Lower confidence or hold
readiness according to the missing information's relevance.

## 5. Integration with `proposal_model.py`

Use the existing model as the sole proposal representation:

- `ProposalType.ENHANCEMENT` and `ProposalStatus` describe the supported
  type and construction state.
- `EvidenceItem` and `EvidenceClass` preserve supplied evidence claims and
  source classifications; `EvidenceProvenance`, `EvidenceFreshness`, and
  `Applicability` remain explicit.
- `ConfidenceAssessment`, `ConfidenceLevel`, and
  `ConfidenceDimensionAssessment` carry qualitative confidence and its
  explanations.
- `ProposalOption` represents alternatives, including the required
  do-nothing/defer option for ready proposals.
- `ProposalRecommendation` carries an advisory recommendation and
  rationale when evidence supports one.
- `TestRecommendation` may describe future validation only and must use
  `TestExecutionStatus.NOT_RUN`.
- `Proposal.validate()` checks the assembled record's structural and
  status-specific constraints.

The model currently defines only five proposal types and three statuses;
do not extend either enum in this slice. It does not define a construction
result, rejection status, or public serializer. A small result wrapper may
return either a proposal or explicit errors but must not pretend that a
rejected candidate is a `Proposal`. Avoid adding fields to the model or
mutating its frozen records.

Validation does not establish that supplied evidence is true, authorized,
current, independent, or semantically applicable. The constructor must
apply its stated gates before setting `READY_FOR_REVIEW`.

## 6. Testing Strategy

Add focused tests in `tests/test_proposal_construction.py` using manually
constructed, deterministic `RepositoryIndex`,
`ArchitectureKnowledgeModel`, and evidence fixtures. Do not create or scan
a real repository as part of constructor unit tests.

### Construction and model tests

- A valid Enhancement input creates the expected immutable
  `READY_FOR_REVIEW` `Proposal` with `IMPLEMENTATION` and `USER_REPORT`
  evidence, all seven qualitative dimension rationales, a defer option,
  an advisory recommendation, and only `NOT_RUN` test recommendations.
- `Proposal.validate()` errors are returned explicitly and are not
  suppressed.
- Verify missing candidate/scope, missing evidence classes, duplicate
  evidence IDs, malformed paths/locators, and invalid input objects.
- Verify a needs-evidence outcome includes concrete unresolved questions
  and does not contain an unsupported substantive recommendation.
- Verify confidence labels are qualitative only and no numeric score is
  produced.

### Awareness input tests

- A matching `RepositoryIndex` and `ArchitectureKnowledgeModel` are
  accepted; mismatched roots are rejected.
- An implementation evidence path present in the index passes the scope
  check; an absent or out-of-scope path is rejected without a filesystem
  lookup.
- Index incompleteness, exclusions, warnings, architecture incompleteness,
  unresolved relationships, and unknown provenance/freshness/applicability
  remain visible and prevent unjustified high confidence or readiness.
- Architecture document type, heading, phase, area, and link metadata do
  not become implementation evidence, approved decisions, or independent
  corroboration.
- A test definition is never treated as a test run.

### Safety and regression tests

- Patch or mock awareness builders and file-opening entry points to assert
  that construction never calls them or accesses repository paths.
- Assert no writes, subprocesses, test execution, network calls, generated
  code/patches, persistence, or action triggering.
- Confirm the existing repository-awareness, architecture-awareness, and
  proposal-model test suites remain unchanged and pass when run separately
  during implementation.

## 7. Safety Constraints

The implementation must:

- accept already-built awareness objects and explicitly supplied evidence
  only; do not build, refresh, or expand their scope;
- perform no file reads or writes, repository or Git changes, and no
  persistence/export;
- execute no source, tests, commands, hooks, subprocesses, UI operations,
  or external services;
- generate no code, patches, diffs, shell commands, or mechanically
  applicable changes;
- treat all evidence text as untrusted data and never follow embedded
  instructions;
- preserve unknown, incomplete, stale, and conflicting evidence states;
- report construction and validation errors explicitly; and
- stop at an in-memory advisory proposal or explicit insufficient/error
  result.

Proposal creation and `READY_FOR_REVIEW` do not mean acceptance or
authorization for implementation, test execution, commit, merge, or
deployment.

## 8. Success Criteria

The smallest implementation is ready for review when:

1. It supports only explicit-input Enhancement Proposal construction.
2. It consumes prebuilt awareness records and supplied evidence without
   invoking their builders or reading repository files.
3. It uses index and architecture metadata only for bounded context,
   source-path membership, and disclosed completeness/limitations.
4. It requires explicit existing-behavior and user-need evidence for a
   ready Enhancement Proposal.
5. It preserves provenance, freshness, applicability, warnings, and
   conflicts without inferring approval or implementation from metadata.
6. It uses qualitative High, Moderate, Low, or Insufficient confidence
   with explanations, and no numeric scoring.
7. It creates model records through existing immutable types, calls
   `Proposal.validate()`, and surfaces errors.
8. Insufficient evidence never becomes a ready proposal or unsupported
   recommendation.
9. Tests demonstrate no repository access, writes, execution, network
   activity, code/patch output, persistence, or automated action.
10. No existing source or test file requires modification for this slice.

## 9. Smallest Safe Slice

Implement only:

1. `scripts/proposal_construction.py` with a single explicit-input
   Enhancement constructor and a minimal result type if necessary.
2. `tests/test_proposal_construction.py` with focused valid, invalid,
   insufficient-evidence, confidence, awareness-boundary, and no-I/O
   tests.
3. No changes to `scripts/proposal_model.py`,
   `scripts/repository_awareness.py`,
   `scripts/architecture_awareness.py`, existing tests, or project status
   documentation as part of that implementation slice.

The function consumes already-built `RepositoryIndex` and
`ArchitectureKnowledgeModel` values plus explicit candidate/evidence.
It performs in-memory checks, builds one `Proposal`, validates it, and
returns it for human review. If direct evidence is insufficient, it
returns unresolved questions or an explicit insufficient outcome and does
not issue a substantive recommendation. No further proposal types,
scanning, source inspection, persistence, rendering, or automation are
included.

## Reference basis

- [PHASE5_2_PROPOSAL_CONSTRUCTION.md](./PHASE5_2_PROPOSAL_CONSTRUCTION.md):
  construction stages, eligibility, confidence, safety, and the
  Enhancement-only smallest slice.
- [PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md):
  authoritative evidence classes, type requirements, qualitative
  confidence, and approval boundaries.
- [PHASE5_2_IMPLEMENTATION_PLAN.md](./PHASE5_2_IMPLEMENTATION_PLAN.md):
  existing proposal-generation pipeline and project-level testing/safety
  expectations.
- [scripts/repository_awareness.py](./scripts/repository_awareness.py):
  actual `RepositoryIndex` fields and bounded read-only builder behavior.
- [scripts/architecture_awareness.py](./scripts/architecture_awareness.py):
  actual `ArchitectureKnowledgeModel` metadata and read-only document
  discovery behavior.
- [scripts/proposal_model.py](./scripts/proposal_model.py):
  available immutable records, enums, and `Proposal.validate()` checks.
