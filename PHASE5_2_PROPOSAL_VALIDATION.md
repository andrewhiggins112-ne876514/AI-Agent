# Phase 5.2.3 Proposal Validation

## Purpose and status

This document designs a quality-validation layer that evaluates a
constructed proposal before it can be presented as eligible for human
review. It builds on the evidence and confidence rules in
[PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md) and
the construction boundaries in
[PHASE5_2_PROPOSAL_CONSTRUCTION.md](./PHASE5_2_PROPOSAL_CONSTRUCTION.md).

Proposal Validation remains read-only, advisory only, non-modifying, and
non-executing. It evaluates an already constructed in-memory proposal and
its supplied evidence; it does not improve, repair, rewrite, or approve a
proposal automatically.

The existing `Proposal.validate()` method in
[scripts/proposal_model.py](./scripts/proposal_model.py) checks structural
and status-specific representation rules. It does not establish factual
truth, evidence authority, semantic freshness, evidence independence, or
human acceptance. Proposal Validation is a distinct quality gate layered
over that structural validator, not a replacement or a claim that this
capability is already implemented.

## 1. Purpose

Proposal Construction assembles a typed `Proposal` from an explicit
candidate and supplied evidence. Proposal Validation determines whether
that record is structurally sound, sufficiently evidenced, internally
consistent, appropriately qualified, and safe to present for human review.

Validation must answer two separate questions:

1. **Is the record valid as data?** Use `Proposal.validate()` for immutable
   record shape, required fields, references, and status-specific
   constraints.
2. **Is the proposal sufficiently supported and complete for its proposed
   quality gate?** Apply evidence, freshness, confidence, completeness,
   and safety rules to the facts represented in the record.

A successful structural check alone is not sufficient for review
eligibility. Validation must preserve distinctions among facts, user
reports, implementation evidence, test definitions, test-run evidence,
decisions, proposed designs, roadmap statements, and inferences.

Validation results are advisory outcomes, not approvals. In particular,
`ACCEPT` means only “eligible to be presented for human review”; it does
not mean that a person accepted the proposal or authorized planning,
implementation, testing, commit, merge, or deployment.

## 2. Validation Rules

### Evidence validity

For every evidence item, require:

- a unique, non-empty `evidence_id`;
- a supported `EvidenceClass` and non-empty, bounded claim;
- repository-relative `source_path` and a precise, non-empty `locator`
  when the item identifies a repository source;
- a meaningful limitation when no repository path is available;
- valid `EvidenceProvenance`, `EvidenceFreshness`, and `Applicability`
  enum values;
- immutable, non-empty limitation text when limitations are present; and
- references from options, recommendations, risks, and test
  recommendations that resolve to known evidence IDs.

For a reviewable claim, check that the evidence class is appropriate to
the claim. A `TEST_DEFINITION` does not establish a test result;
`ROADMAP_STATEMENT` or `PROPOSED_DESIGN` does not establish approved
requirements or implementation; and a `USER_REPORT` does not establish
reproducible behavior by itself. Derived summaries and duplicated copies
of a source are not independent corroboration.

For currently supported types, enforce the existing model's type-specific
gates and the authoritative design's stronger evidence requirements. For
the current Enhancement construction slice, require applicable,
traceable implementation evidence of existing behavior and an explicit
user-need report. Other proposal types remain subject to their Phase 5.2
evidence rules; Capability Evolution remains disabled.

Validation can check labels, locators, relationships, and declared source
status. Unless a separately authorized evidence reader is introduced, it
cannot inspect the cited source or prove the claim's truth. Report that
limitation instead of treating structural consistency as factual
verification.

### Evidence freshness

Assess freshness without inventing evidence timestamps or repository
revision identity:

- Preserve `CURRENT`, `STALE`, or `UNKNOWN` exactly as supplied.
- Treat stale evidence as a material limitation; it cannot support an
  `ACCEPT` outcome for claims whose current state matters.
- Treat unknown freshness as unknown, not as current. It prevents High
  confidence and may require additional evidence before review eligibility.
- Treat modified, unverified, or unknown provenance as a disclosed limit;
  do not imply that content is committed or matches the current repository.
- Treat a partial scan, exclusions, warnings, unresolved links, or missing
  snapshot identity as limits when they affect the claim. Absence in an
  incomplete scope is not proof of absence.
- Do not define freshness by filename, document order, commit recency, or
  an arbitrary time-to-live. No calibrated freshness window exists in the
  current model.

The present `EvidenceItem` has freshness and provenance enums but no
observation timestamp, source hash, or snapshot identity field. Validation
can apply declared states and flag missing context; it cannot independently
recompute freshness. Future freshness policies requiring those values
must first extend the model through a separately approved design.

### Confidence validity

Use only **High**, **Moderate**, **Low**, and **Insufficient**. No numeric
score, probability, weighted sum, threshold, or confidence-based
authorization is permitted.

For a proposal eligible for review:

- require a non-empty confidence explanation;
- require exactly one non-empty rationale for each of the seven
  dimensions: Traceability, Directness, Applicability, Reproducibility,
  Completeness, Freshness, and Independence;
- ensure the rationale and limiting conditions agree with supplied
  evidence status, scan completeness, and conflicts;
- ensure unsupported claims do not receive stronger confidence merely
  because several summaries repeat them; and
- apply non-compensating evidence gates. Missing essential evidence,
  material unresolved conflict, unsafe evidence, or stale evidence
  prevents an `ACCEPT` outcome regardless of other strengths.

Confidence is not a measure of severity, priority, probability of success,
or approval. `Insufficient` cannot be accepted for review as a substantive
proposal. It should lead to `NEEDS_EVIDENCE` unless the proposal itself is
invalid or unsafe and must be rejected.

The current `Proposal.validate()` requires all seven dimension entries for
`READY_FOR_REVIEW` and limits High confidence when freshness, provenance,
or applicability is unknown, conflicting, or unverified. It does not
verify the meaning of the rationales, independently derive confidence, or
check every qualitative cap. The new quality layer must perform those
semantic consistency checks separately.

### Proposal completeness

For a proposal to be eligible for human review, validate that it has:

- a supported proposal type, non-empty ID, schema version, timezone-aware
  creation time, bounded scope, and clear problem statement;
- traceable, type-appropriate evidence and any counter-evidence,
  limitations, provenance, freshness, and applicability needed to
  understand the claims;
- a non-empty rationale;
- at least two meaningful options, including a do-nothing/defer option,
  with trade-offs and references that resolve;
- an advisory recommendation referencing one of those options, with a
  rationale, assumptions, and conditions that could change it;
- risks and affected areas when material to the candidate, without
  presenting estimated impacts as observed facts;
- a testing strategy where relevant, with measurable expected results and
  every test recommendation marked `NOT_RUN`;
- explicit assumptions, dependencies, and unresolved questions where
  applicable; and
- a clear approval boundary separating review eligibility from all
  downstream authorizations.

Completeness is claim-relative: absence of a risk or test entry is not
automatically an error in every proposal, but material omissions must be
identified. For the initial Enhancement slice, validation must not add
content or invent a recommendation to fill a missing field. It returns
`NEEDS_EVIDENCE` or `REJECT` instead.

The existing representation validator checks many structural requirements
including options, recommendation references, evidence references,
test status, and type-specific evidence classes. Proposal Validation adds
quality checks for evidence meaning, alignment between confidence and
limitations, and completeness of material proposal content.

## 3. Proposal Quality Gates

Validation returns exactly one outcome: `ACCEPT`, `NEEDS_EVIDENCE`, or
`REJECT`. These are **quality-gate outcomes**, not `ProposalStatus` values
and not human decisions. Keep them in a separate validation result; do not
add them to the existing `ProposalStatus` enum or misrepresent them as
proposal lifecycle states.

| Outcome | Meaning | Required handling |
| --- | --- | --- |
| **ACCEPT** | The proposal passes structural validation and all applicable evidence, freshness, confidence, completeness, and safety gates for presentation to a human reviewer. | Return the unchanged proposal as eligible for review, clearly marked advisory. No acceptance, approval, or downstream action is implied. |
| **NEEDS_EVIDENCE** | The candidate is in scope and structurally representable, but evidence is missing, stale, unknown, incomplete, or materially conflicting such that review readiness is not established. | Return specific missing evidence/questions and limitations. Do not present a substantive recommendation as established. This outcome is compatible with a `NEEDS_EVIDENCE` proposal record when `Proposal.validate()` passes. |
| **REJECT** | The record is structurally invalid, outside authorized scope, unsafe/privacy-ineligible, misclassified in a material way, or otherwise cannot be represented honestly under the rules. | Return explicit reasons. Do not repair the proposal, silently discard invalid input, or turn rejection into a success-shaped record. A rejected object is not necessarily a valid `Proposal`; rejection belongs in the validation result. |

Apply this precedence:

1. If the proposal or evidence is invalid, unauthorized, unsafe, or
   materially misclassified, return `REJECT`.
2. Otherwise, if a material evidence, freshness, confidence, or completeness
   gate remains unresolved, return `NEEDS_EVIDENCE`.
3. Return `ACCEPT` only when all applicable gates pass.

`ACCEPT` is intentionally named as requested but must always be explained
as **accepted by the quality gate for human review only**. It is not
acceptance by a user, approval to implement, or permission to execute.

## 4. Validation Workflow

```text
Evidence
   ↓
Construction
   ↓
Validation
   ↓
Review Eligibility
```

### Evidence

Use only evidence supplied within an explicitly authorized scope. Preserve
source identity, evidence class, locator, provenance, freshness,
applicability, limitations, and conflicts. Do not use Validation to broaden
discovery or read sources beyond the permissions already granted.

### Construction

Proposal Construction assembles the supplied candidate and evidence into
the immutable model. The current implementation supports Enhancement
proposals only and relies on caller-supplied options and recommendation;
it does not search for a candidate or generate recommendations. Invalid
construction inputs raise explicit construction errors; insufficient
support may be represented with `ProposalStatus.NEEDS_EVIDENCE`.

### Validation

1. Confirm the object is a `Proposal` and run `Proposal.validate()`.
   Surface all structural errors.
2. Check evidence IDs, classes, locators, references, source status,
   applicability, freshness, provenance, conflicts, and scan limits.
3. Apply type-specific evidence gates and verify that claims and
   recommendations do not exceed what the evidence supports.
4. Reconcile confidence level, dimension rationales, and limiting
   conditions with the evidence; enforce non-compensating gates.
5. Check required proposal content, option quality, test status, material
   omissions, scope, and safety/privacy boundaries.
6. Return one quality-gate outcome and explicit reasons, without altering
   the proposal or triggering an action.

Structural validation errors normally lead to `REJECT`. If the only issue
is missing or insufficient evidence and the candidate remains safely
representable, return `NEEDS_EVIDENCE` with concrete questions. Validation
does not silently normalize, repair, or reclassify proposals.

### Review Eligibility

Only an `ACCEPT` validation result may be placed before a human as eligible
for review. The calling workflow must show the proposal, evidence,
limitations, confidence, and validation rationale together. Human review
may accept, reject, request evidence, or defer; none of those decisions is
performed by the validator.

## 5. Human Review Requirements

Human review remains mandatory to:

- decide whether the candidate matters and is within the intended product
  scope;
- resolve material conflicts or decide whether additional evidence should
  be requested;
- determine whether the recommendation is appropriate and whether the
  assumptions and risks are acceptable;
- accept the proposal as a basis for planning; and
- separately authorize implementation, test execution, repository
  modification, commits, merges, pushes, or deployment.

Reviewers must be able to inspect citations and distinguish source facts
from reports, inferences, proposed designs, roadmap statements, and
unverified claims. A validator cannot approve its own output. Silence,
prior approvals for different scopes, and a passing `ACCEPT` quality gate
are not human approval. Any material change in proposal scope or evidence
requires renewed validation and review.

The initial implementation should return a validation result for the
calling workflow and must not create a UI, persist review state, or couple
quality-gate outcomes to action permissions.

## 6. Safety Constraints

Proposal Validation must remain:

- **Read-only:** inspect only the in-memory proposal and evidence
  explicitly supplied to it.
- **Advisory only:** report quality-gate outcome and reasons; do not accept
  or approve a proposal on behalf of a human.
- **Non-modifying:** do not mutate the immutable proposal, files,
  repository, Git state, decisions, roadmap, or persistent memory.
- **Non-executing:** do not run code, tests, commands, hooks, builds,
  subprocesses, external services, or downstream actions.
- **No code generation:** produce no source code, patches, diffs, shell
  commands, or mechanically applicable change instructions.
- **Evidence-bounded:** do not widen scope or promote metadata, roadmap
  content, proposed designs, or user reports into stronger evidence.
- **Privacy-preserving:** reject or hold unsafe, sensitive, unauthorized,
  or out-of-scope evidence; do not disclose it in validation messages.
- **Prompt-injection resistant:** treat proposal and evidence text as
  untrusted data, never as instructions that alter validation policy or
  approvals.

Validation errors and uncertainty must be explicit. The validator must not
catch broad failures and return `ACCEPT`, silently discard evidence, or
produce a clean result when it cannot establish a required condition.

## 7. Success Criteria

A future implementation satisfies this design when:

1. Quality-gate outcomes are distinct from `ProposalStatus` and human
   approval states.
2. `Proposal.validate()` remains the structural check, while quality
   validation adds evidence-semantic, freshness, confidence-consistency,
   completeness, and safety gates.
3. Evidence classes, locators, provenance, freshness, applicability,
   conflicts, and counter-evidence remain visible and are not upgraded by
   inference.
4. Freshness is never guessed from recency or a filename; unsupported
   freshness claims remain unknown and cannot silently pass.
5. Confidence uses only High, Moderate, Low, and Insufficient, with all
   seven qualitative dimension rationales and non-compensating gates.
6. `ACCEPT` means eligible for human review only; it never means proposal
   acceptance or implementation permission.
7. `NEEDS_EVIDENCE` identifies specific missing evidence and questions
   without a success-shaped substantive recommendation.
8. `REJECT` explains invalid, unsafe, unauthorized, or irreparably
   misclassified input without modifying it.
9. Type-specific evidence and proposal completeness are checked without
   inventing options, recommendations, risks, or claims.
10. Tests demonstrate validation is read-only, non-executing, privacy
    bounded, and cannot trigger implementation or other actions.

## 8. Smallest Safe Slice

The smallest safe implementation is a pure in-memory validator for
explicitly constructed **Enhancement Proposals**:

1. Accept a `Proposal` and its already-supplied evidence; do not construct
   candidates or inspect repository paths.
2. Run `Proposal.validate()` and preserve its structural errors.
3. Apply Enhancement-specific evidence checks for existing behavior and
   stated user need, locators/references, declared freshness and
   applicability, confidence consistency, and material completeness.
4. Return a small immutable validation result containing exactly one of
   `ACCEPT`, `NEEDS_EVIDENCE`, or `REJECT`, plus explicit reason strings
   and the unchanged proposal only when safely representable.
5. Treat `ACCEPT` strictly as human-review eligibility. Do not add a
   human-approval workflow or connect outcomes to actions.
6. Add focused deterministic tests for each gate and for no I/O,
   mutation, execution, or action coupling.

Do not add source readers, freshness timestamps or scoring frameworks,
proposal rewriting, persistence, UI, other proposal types, or
Capability Evolution in this slice. Extension to other proposal types
requires separate verification of their evidence gates and proposal
completeness rules.

## Reference basis

- [PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md):
  authoritative evidence classes, proposal content, confidence, review,
  and safety requirements.
- [PHASE5_2_IMPLEMENTATION_PLAN.md](./PHASE5_2_IMPLEMENTATION_PLAN.md):
  planned evidence pipeline, model structure, testing, and type gates.
- [PHASE5_2_PROPOSAL_CONSTRUCTION.md](./PHASE5_2_PROPOSAL_CONSTRUCTION.md):
  evidence normalization, construction eligibility, confidence, and
  current model limitations.
- [PHASE5_2_PROPOSAL_CONSTRUCTION_IMPLEMENTATION_PLAN.md](./PHASE5_2_PROPOSAL_CONSTRUCTION_IMPLEMENTATION_PLAN.md):
  implemented Enhancement-only construction boundary and test plan.
- [scripts/proposal_model.py](./scripts/proposal_model.py):
  current immutable records and structural/status-specific
  `Proposal.validate()` behavior.
- [scripts/proposal_construction.py](./scripts/proposal_construction.py):
  explicit-input Enhancement constructor and current evidence checks.
- [tests/test_proposal_model.py](./tests/test_proposal_model.py) and
  [tests/test_proposal_construction.py](./tests/test_proposal_construction.py):
  current structural, confidence, construction, and safety test coverage.
