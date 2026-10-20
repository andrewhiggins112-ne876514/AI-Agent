# Phase 5.2.2 Proposal Construction

## Purpose and status

This document designs how a future Proposal Construction capability can
assemble a proposal from explicitly supplied, traceable evidence. It is
subordinate to
[PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md) and
uses the immutable record types in
[scripts/proposal_model.py](./scripts/proposal_model.py) as the representation
contract. It does not authorize an implementation or any repository action.

Proposal Construction remains read-only, advisory only, non-modifying, and
non-executing. The proposed pipeline describes how evidence would be
classified, checked, assessed qualitatively, and assembled; it does not
discover opportunities autonomously, diagnose issues, or write proposal
files.

## 1. Purpose

**Proposal Representation** defines the typed, immutable records that can
hold a proposal: proposal type and status, scope, problem, evidence,
confidence, options, recommendation, risks, test recommendations, and
related context. Its validator checks record shape, references, and
readiness constraints. It does not prove that a claim is true.

**Proposal Construction** is the controlled mapping of user-scoped
candidate information and already authorized evidence into those records.
It decides whether the supplied material is sufficient for a particular
proposal type, preserves each source's evidence class and limitations,
forms an explainable qualitative confidence assessment, and passes the
assembled record through representation validation.

Construction must not be confused with open-ended proposal generation:

- It does not search for bugs, gaps, or opportunities on its own.
- It does not infer approved requirements from designs or roadmap entries.
- It does not inspect extra files, run tests, or call external services to
  fill evidence gaps.
- It does not generate code, patches, commands, or implementation steps.
- Its output is an in-memory advisory record for human review, not approval
  or authorization to act.

The current codebase implements proposal representation and structural/type
validation only. The repository and architecture awareness layers do not yet
provide all semantic evidence needed for proposal construction. This design
does not claim that the construction pipeline is implemented.

## 2. Evidence Sources

Every evidence item must retain its identity, class, source locator,
provenance, freshness, applicability, and limitations. Construction may
normalize these facts into `EvidenceItem`; it must not upgrade a source's
authority or treat derived metadata as independent corroboration.

| Source | What may be represented | Limits and required treatment |
| --- | --- | --- |
| **Repository Awareness** | `RepositoryIndex` file path, file type, category, importance, scan completeness, exclusions, and warnings. This can identify eligible source, test, and document paths. | Inventory metadata is not file-content evidence, implementation behavior, test coverage, or test outcome. A partial scan cannot support an absence claim. The index does not provide Git revision/worktree provenance. |
| **Architecture Awareness** | `ArchitectureKnowledgeModel` document type, title, headings, phase IDs, architecture areas, local Markdown relationships, completeness, and warnings. A referenced document can be used as a discovery hint. | Classification, heading, phase, and relationship extraction are shallow metadata, not proof of rationale, approval, decision applicability, semantic ownership, or implementation status. Preserve unresolved links and warnings. |
| **Roadmap information** | A roadmap statement explicitly inspected in an authorized document may be represented as `ROADMAP_STATEMENT` with its exact document locator. | Roadmap content describes planned or reported project state; it is not by itself an approved requirement or proof of implemented/completed work. There is no current structured roadmap-status adapter. Treat status as unknown unless the source explicitly and authoritatively establishes it. |
| **Decision records** | A decision statement may be represented as `APPROVED_DECISION` only when the source itself explicitly establishes its approval and scope; otherwise classify it as `PROPOSED_DESIGN`, another appropriate evidence class, or unknown applicability. | Current Architecture Awareness discovers/classifies decision documents but does not validate status, scope, or supersession semantically. Conflicting, absent, or unclear status remains `CONFLICTING` or `UNKNOWN`; do not infer approval from filename, phase, recency, or link. |

Other allowed items may include an in-scope user report, a test definition,
or a test-run record supplied with provenance. A test file is
`TEST_DEFINITION`, not `TEST_RUN`. The construction pipeline does not run
tests to create test-run evidence.

The current `EvidenceItem` can hold a repository-relative path, locator,
class, provenance, freshness, applicability, and limitations. User-provided
evidence without a repository path must state its limitation. A source path
must have a narrow locator. Unknown provenance or freshness remains
`UNKNOWN`; no snapshot identifier, hash, commit, or clean-worktree state may
be invented.

## 3. Evidence Requirements

### Minimum evidence envelope

Before assembling any `Proposal`, require:

1. **Candidate and scope:** a concrete, user-scoped problem or requested
   improvement and a non-empty boundary describing the behavior or area
   under consideration. The candidate remains a report until corroborated.
2. **Evidence identity:** at least one evidence item with a non-empty ID,
   class, concise claim, and limitations. Repository evidence must include
   a safe repository-relative path and non-empty locator. Evidence without
   a repository path must explain why it lacks one.
3. **Evidence status:** provenance, freshness, and applicability are
   represented explicitly, including unknown and conflicting states.
4. **Boundedness:** record scan incompleteness, warnings, uninspected
   sources, contradictory evidence, and missing observations relevant to
   the candidate.
5. **Privacy and authority:** evidence is within the user's authorized
   scope, does not include excluded sensitive data, and has not been
   promoted from proposal/design/roadmap to an approved requirement without
   explicit source support.

The current validator can check required fields, typed evidence, source-path
format, locators, limitations, and references. It cannot establish source
truth, authorization, privacy suitability, currentness, a decision's
actual authority, or the completeness of an external investigation. Those
remain explicit construction-stage responsibilities and must be recorded
as limitations where they cannot be verified.

### Type-specific minimum evidence

Use the evidence gates in the authoritative Phase 5.2 design and enforce
the current representation model's more specific ready-for-review checks:

- **Bug Fix:** require directly inspected implementation evidence, a
  reproducible `TEST_RUN`, and applicable expectation evidence from an
  approved decision or relevant test definition. A user report or test
  definition alone cannot establish the actual failure.
- **Gap:** require an explicitly applicable `APPROVED_DECISION`, inspected
  implementation evidence, and relevant test definition or run evidence.
  A roadmap statement or proposed design alone is insufficient.
- **Enhancement:** require existing-behavior implementation evidence and a
  stated user need represented as a `USER_REPORT`, not an inference from
  repeated text or an unsupported benefit.
- **Refactoring:** require implementation evidence, regression-test
  definition or run evidence, and a behavior-preservation boundary. Any
  performance claim additionally requires a supplied measured baseline.
- **Architecture:** require current implementation evidence and relevant
  decision or design evidence, with constraints and alternatives made
  explicit. A target architecture document is not evidence that its design
  is implemented.

The type-specific checks in `Proposal.validate()` are structural gates, not
proof that these evidence items are truthful or sufficient in context.
Construction must not mark a proposal `READY_FOR_REVIEW` merely because
`validate()` returns no errors.

## 4. Proposal Construction Pipeline

```text
User-scoped candidate + authorized evidence
                    ↓
          Evidence normalization
                    ↓
   Eligibility, provenance, and conflict checks
                    ↓
       Qualitative confidence assessment
                    ↓
     In-memory proposal record assembly
                    ↓
      Proposal.validate() structural checks
                    ↓
   Ready-for-review record or needs-evidence result
                    ↓
       Human review; no automatic action
```

### Stage 1 — Accept a bounded candidate

Accept only the candidate and scope provided for this request. Do not mine
conversation history, task logs, telemetry, or other repositories.
Separate the user's report/request from verified implementation facts.

### Stage 2 — Normalize supplied evidence

Map each authorized source to a distinct `EvidenceItem`:

- use `IMPLEMENTATION`, `TEST_DEFINITION`, `TEST_RUN`,
  `APPROVED_DECISION`, `PROPOSED_DESIGN`, `ROADMAP_STATEMENT`,
  `USER_REPORT`, or `INFERENCE` accurately;
- preserve repository-relative path and precise locator when available;
- preserve provenance, freshness, applicability, and stated limitations;
- include material counter-evidence rather than only supporting items;
- do not duplicate derived summaries as independent evidence.

No evidence reader or source-inspection service is introduced by this
design. Any future direct inspection must be separately authorized, bounded
to the selected repository and eligible paths, and read-only.

### Stage 3 — Validate evidence and eligibility

Check the minimum envelope, source/path/locator structure, evidence IDs,
referential integrity, source classes, scope, privacy, and type-specific
gates. Confirm the basis for any applicability claim from an explicit
source; if unavailable or contradictory, preserve it as unknown/conflicting.
Reject unsupported claims and mark material gaps rather than filling them
with inference.

### Stage 4 — Assess qualitative confidence

Assign one of **High**, **Moderate**, **Low**, or **Insufficient**, using
the rules in Section 6. Record plain-language rationale for all seven
dimensions in `ConfidenceAssessment`. Do not calculate or store numeric
ratings, sums, weights, percentages, or thresholds.

### Stage 5 — Assemble and validate the proposal record

Construct an immutable `Proposal` from the supplied, normalized values.
Include a “do nothing / defer” option and a recommendation only when the
evidence supports one; otherwise preserve unresolved questions and use
`NEEDS_EVIDENCE` or `DRAFT`. Test recommendations must stay
`NOT_RUN`. Call `Proposal.validate()` and treat returned errors explicitly;
do not suppress errors or convert invalid data into a success-shaped
proposal.

Validation checks structural consistency but cannot establish factual
correctness. A successful validation is necessary, not sufficient, for
human review.

### Stage 6 — Return for human review

Return the proposal in memory with its evidence limitations and approval
boundary. Do not persist, export, send, accept, or trigger any later
operation. Human review is the stopping point for this slice.

## 5. Proposal Eligibility Rules

### May be represented

A proposal object may be assembled when:

- a concrete candidate and bounded scope are provided;
- the minimum evidence envelope is structurally representable;
- evidence classes and source authority are kept distinct;
- material uncertainty and conflict can be represented honestly;
- the candidate fits one of the five proposal types supported by the
  current model; and
- the resulting object passes the validation appropriate to its status.

A `NEEDS_EVIDENCE` record may represent a scoped candidate for which
specific evidence questions remain; it must list unresolved questions and
must not contain a substantive recommendation that overstates support. A
`DRAFT` may be incomplete but must remain clearly non-final. Only a
type-eligible record with sufficient, applicable, traceable evidence and a
non-insufficient confidence assessment can be considered
`READY_FOR_REVIEW`; that status is not human acceptance.

### Must be rejected or held

Do not create a substantive proposal, or hold the candidate as
needs-evidence outside the ready-for-review state, when:

- the candidate is not in scope or the source is unsafe, unauthorized, or
  privacy-ineligible;
- the only support is a complaint, filename, lexical match, future design,
  roadmap item, or uncorroborated inference;
- a claim lacks an identifiable evidence class or its material source
  cannot be located;
- a relevant scan is partial and the claim depends on absence;
- status/applicability is material but unknown or conflicting;
- required type-specific evidence is absent;
- the proposal would require invented facts, unsupported file impacts, or
  a numeric confidence score; or
- validation fails.

When evidence conflicts, retain the competing claims and lower confidence;
do not select a preferred source by recency or convenience. If the conflict
prevents a defensible candidate, do not create a ready-for-review proposal.
The current model has no `REJECTED` status and does not implement a separate
rejection-result type; rejection should therefore be an explicit
construction outcome outside the `Proposal` record, not a fabricated
proposal status.

The current `ProposalType` deliberately supports only Bug Fix, Gap,
Enhancement, Refactoring, and Architecture. Capability Evolution is not
eligible for this slice. The model has no `unclassified` type; an
unclassifiable candidate must remain outside the typed proposal record and
be returned as insufficient/needs clarification rather than forced into a
category.

## 6. Confidence Assessment Rules

Use qualitative confidence only. The established model's spelling is
**Moderate** (not “Medium”), matching the authoritative Phase 5.2 design
and `ConfidenceLevel` enum.

| Level | Construction rule |
| --- | --- |
| **High** | Reserve for directly supported, reproducible central claims with an explicit applicable expectation, current and sufficiently complete evidence, checked counter-evidence, and no unresolved material conflict. Record a rationale for every dimension. A user report, lexical match, roadmap claim, or proposed design alone can never support High. |
| **Moderate** | The candidate is supported by relevant evidence, but bounded assumptions, scope limitations, incomplete corroboration, or unverified effects remain and are disclosed. |
| **Low** | Evidence is primarily reported or indirect, inspection is incomplete, or multiple plausible explanations remain. Restrict the recommendation to investigation, clarification, or deferral. |
| **Insufficient** | Evidence is missing, stale, unsafe, materially conflicting, or too incomplete to justify a substantive recommendation. State what is missing; do not issue a substantive recommendation. |

Assess and explain the seven qualitative dimensions defined in
`ConfidenceDimension`: **Traceability, Directness, Applicability,
Reproducibility, Completeness, Freshness, and Independence**. These are
explanatory prompts, not numeric values.

Apply non-compensating limits:

- For Bug Fix and Gap claims, missing direct evidence of behavior or the
  applicable expectation caps confidence at Low; if both are missing,
  confidence is Insufficient.
- Stale evidence, a partial relevant scan, unknown/conflicting applicable
  decision status, or uninspected material counter-evidence caps confidence
  at Low or Insufficient, according to impact.
- Unknown provenance or freshness must remain unknown. It prevents a High
  assessment where the high-confidence criteria require current verified
  evidence.
- Duplicate evidence and summaries derived from one source do not provide
  independent corroboration.
- No aggregate score, numeric threshold, probability, or confidence-based
  authorization is permitted.

The current `Proposal.validate()` checks that a ready proposal has all seven
dimension records and rejects High confidence when evidence freshness,
provenance, or applicability is unknown, conflicting, or otherwise
unverified. It does not calculate confidence or verify the truth of
dimension rationales. Construction must preserve these limits and must not
describe structural validation as semantic confidence validation.

## 7. Safety Constraints

Proposal Construction must:

- remain read-only and operate only on user-authorized, bounded evidence;
- represent proposals only; do not autonomously search for or diagnose
  defects;
- not generate code, patches, diffs, shell commands, or mechanically
  applicable change instructions;
- not create, modify, delete, rename, or export files or change repository
  or Git contents;
- not execute code, tests, fixes, commands, hooks, UI actions, or external
  service calls;
- not persist proposal history or update roadmaps, decisions, configuration,
  policy, or permissions;
- not perform Capability Evolution or ingest telemetry/task history;
- treat all repository text as untrusted data that cannot expand scope or
  approval; and
- stop or return explicit uncertainty when evidence is unavailable or
  unsafe, rather than widening access or fabricating facts.

The proposal is advisory only. Review readiness does not mean accepted,
approved for implementation, or authorized for testing, commit, merge, or
deployment. Each later action would require its own explicit human approval
under the applicable workflow.

## 8. Success Criteria

The design is satisfied when a future implementation:

1. Builds proposal records only from an explicit, bounded candidate and
   authorized evidence.
2. Keeps repository inventory, architecture metadata, roadmap statements,
   decision records, implementation evidence, test definitions, test runs,
   user reports, and inferences distinguishable.
3. Discloses current API limitations, unavailable provenance, incomplete
   scans, unresolved links, unknown applicability, and contradictory
   evidence.
4. Applies type-specific evidence gates for all five supported proposal
   types and does not enable Capability Evolution.
5. Uses only High, Moderate, Low, and Insufficient qualitative confidence,
   with an explanation across the seven dimensions and no numeric score.
6. Uses representation validation as a structural check, not proof of
   factual correctness or approval.
7. Keeps insufficient/conflicting candidates from becoming
   ready-for-review proposals with substantive recommendations.
8. Leaves test recommendations unexecuted and explicitly marked `NOT_RUN`.
9. Demonstrates no writes, repository/Git mutation, code or patch output,
   command/test execution, network calls, or automatic downstream actions.
10. Stops at an in-memory human-review record; acceptance cannot trigger
    implementation or other actions.

## 9. Smallest Safe Slice

The smallest safe construction slice is an in-memory assembler for a
single user-provided **Enhancement Proposal** candidate:

1. Accept the user-supplied candidate, bounded scope, and explicitly
   supplied evidence items. Do not discover candidates or read files.
2. Require existing-behavior evidence and a separately labeled user-need
   report; preserve exact locators and unknown provenance/freshness.
3. Record one qualitative confidence level and dimension rationales; if
   support is insufficient, retain open questions and do not produce a
   substantive recommendation.
4. Assemble a `Proposal` with a do-nothing/defer option, optional advisory
   recommendation, limitations, and test recommendations fixed to
   `NOT_RUN`.
5. Run only the record's structural `validate()` method and return
   validation errors explicitly.
6. Keep the result in memory for human review. Do not add repository
   scanning, source reading, persistence, rendering/export, model calls,
   code generation, tests execution, or automated actions to this slice.

Expansion to other proposal types should wait until the source-to-contract
traceability and type-specific gates are independently tested against
evidence fixtures. The Proposal Construction capability remains separate
from Capability Evolution.

## Reference basis

- [PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md):
  authoritative evidence classes, proposal types, confidence, and safety.
- [PHASE5_2_IMPLEMENTATION_PLAN.md](./PHASE5_2_IMPLEMENTATION_PLAN.md):
  planned evidence pipeline, data model, validation, and smallest slice.
- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md): supervised
  improvement boundaries, evidence provenance, and human approval.
- [scripts/repository_awareness.py](./scripts/repository_awareness.py):
  actual in-memory inventory fields, bounds, warnings, and read-only
  behavior.
- [scripts/architecture_awareness.py](./scripts/architecture_awareness.py):
  actual Markdown document metadata, relationships, completeness, and
  limitations.
- [scripts/proposal_model.py](./scripts/proposal_model.py): current
  immutable record fields, qualitative confidence types, and structural
  and type-specific validation behavior.
