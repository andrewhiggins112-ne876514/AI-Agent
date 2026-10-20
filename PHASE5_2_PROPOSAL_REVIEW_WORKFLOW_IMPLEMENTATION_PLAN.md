# Phase 5.2.4 Proposal Review Workflow — Implementation Plan

## Purpose and status

This plan specifies the smallest implementation of
[PHASE5_2_PROPOSAL_REVIEW_WORKFLOW.md](./PHASE5_2_PROPOSAL_REVIEW_WORKFLOW.md).
It is a design document only and does not add review behavior.

The workflow remains read-only, advisory only, non-modifying, and
non-executing. It presents an unchanged, validated proposal to a person and
returns an explicit in-memory human disposition. It does not persist state
or grant authority for downstream actions.

## 1. Scope

### Included

Implement a small, in-memory review boundary for the currently supported
Enhancement proposal type. The workflow will:

1. Accept an existing `Proposal` and its existing
   `ProposalValidationResult`; it will not call Proposal Construction or
   rewrite proposal fields.
2. Check that the validation result refers to the exact proposal object
   being considered and that its decision is one of the defined quality
   outcomes.
3. Expose the proposal to the human reviewer only when the validation
   decision is `ACCEPT` and the result marks it eligible for review.
4. For `NEEDS_EVIDENCE` and `REJECT`, return the validation reasons without
   presenting the proposal as review-eligible.
5. Accept one explicit human disposition for the presented proposal:
   accepted for planning, request evidence, rejected, or deferred.
6. Return immutable review and audit records that reference the unchanged
   proposal and validation result, and distinguish quality validation
   from the human's decision.
7. Keep the records and interaction in memory only. No persistent audit
   log, event history, workflow state, UI control, or downstream action is
   implemented.

### Excluded

- Proposal creation, validation logic, automatic candidate discovery, or
  evidence collection.
- Proposal types beyond Enhancement.
- Saving, exporting, serialization, database/storage, or audit persistence.
- Workflow UI, notifications, or reviewer identity integration.
- Automatic retries, reminders, planning, implementation, or action
  triggering.
- Code generation, patches, diffs, repository writes, or execution.
- Changes to `Proposal`, `ProposalStatus`, `ValidationDecision`, or the
  proposal model's lifecycle.

The workflow does not equate `ProposalStatus.READY_FOR_REVIEW` alone with
eligibility. It requires both that status and a current validation result
of `ACCEPT` whose `eligible_for_review` property is true.

## 2. Review Eligibility

The workflow uses the quality outcome from
`scripts/proposal_validation.py` as follows:

| Validation outcome | Workflow handling |
| --- | --- |
| `ACCEPT` | May be presented for human review only if the proposal is `READY_FOR_REVIEW`, has the supported type, the result references that same proposal, and `eligible_for_review` is true. |
| `NEEDS_EVIDENCE` | Do not present as review-ready. Return the proposal if safely representable with each validator reason and the evidence questions visible; request new evidence outside this workflow. |
| `REJECT` | Block review eligibility. Return only safe, non-sensitive rejection reasons; do not expose unsafe evidence or attempt to repair or reclassify the proposal. |

Missing or mismatched validation results, invalid objects, unsupported
proposal types, or inconsistent status/outcome combinations fail closed.
They must not become a human-review invitation.

### Outcome transitions

```text
ACCEPT
  + matching READY_FOR_REVIEW Enhancement proposal
  + eligible_for_review
      → Ready For Review → explicit human disposition → Reviewed

NEEDS_EVIDENCE
      → Needs Evidence → new evidence supplied outside this workflow
      → reconstruct and revalidate → ACCEPT may enter Ready For Review

REJECT
      → Rejected / blocked; no human-review presentation
```

`NEEDS_EVIDENCE` remains blocked until the caller supplies new evidence
and creates a proposal that is validated again. The workflow does not
change a validation result or promote a blocked proposal. `REJECT` is
terminal for that supplied record in this slice; a materially corrected
candidate must be resubmitted and validated as a new proposal. Only
`ACCEPT` enters human review, and only an explicit human disposition
transitions it to `Reviewed`.

An accepted review disposition cannot change the validation outcome or
proposal status. If evidence or scope changes, the caller must construct
and validate a new proposal representation before it can be presented
again.

## 3. Review State Model

Workflow states are transient in-memory concepts. Do not add these states
to the existing `ProposalStatus`; do not claim persistence or historical
tracking.

| State | Representation and behavior |
| --- | --- |
| **Draft** | A candidate is not yet presented as a complete proposal. The review workflow does not create or edit Drafts; it may report that a non-ready proposal is blocked. |
| **Needs Evidence** | Proposal is not eligible for review because evidence or a quality gate remains unresolved. Preserve the validator's questions and reasons. It may be reconsidered only after caller-supplied evidence is used to construct/revalidate a proposal. |
| **Ready For Review** | Proposal has `ProposalStatus.READY_FOR_REVIEW`, and the matching validation result is `ACCEPT` and eligible. It may be presented, but no human has yet made a disposition. |
| **Reviewed** | A human has returned an explicit disposition for the exact proposal and scope. Store only in the returned transient review record; it is not a proposal status or approval token. |
| **Rejected** | Either the validator returned `REJECT`, or a human explicitly rejected a proposal. Record which actor made the rejection; validator rejection must never be represented as a human decision. |

The human disposition values should be distinct: **Accepted for
planning**, **Request evidence**, **Rejected**, and **Deferred**.
“Accepted for planning” means only that the person is willing to use the
proposal as planning input. It does not authorize implementation,
execution, file modification, commit, merge, push, or deployment.

## 4. Review Records

Use frozen in-memory records with tuple fields and no persistence:

```text
ReviewDisposition
  accepted_for_planning | request_evidence | rejected | deferred

ReviewAuditEntry
  event_id
  proposal_id
  proposal_version_reference  # exact proposal object or stable caller ID
  event_type                  # quality_gate | human_disposition
  actor_type                  # validator | human
  validation_decision         # ACCEPT | NEEDS_EVIDENCE | REJECT
  validation_reason_codes     # tuple, not source text
  disposition                 # optional; human event only
  reviewed_scope              # exact scope for a human disposition
  reviewer_reference          # optional, privacy-approved
  rationale                   # minimal, caller-supplied and redacted
  evidence_references         # tuple of evidence IDs and locators
  occurred_at                 # timezone-aware

ProposalReviewRecord
  proposal_id
  proposal_reference          # reference to unchanged Proposal
  validation_reference        # matching ProposalValidationResult
  workflow_state              # Ready For Review | Reviewed | Rejected
  disposition                 # absent before human review
  reviewer_reference         # optional, privacy-approved, caller supplied
  reviewed_at                 # timezone-aware, only for a human disposition
  scope_acknowledged          # exact proposal scope reviewed
  rationale                   # optional human rationale
  evidence_questions          # tuple; request-evidence disposition
  audit_entries               # immutable tuple of ReviewAuditEntry
```

The initial record must not contain an action payload, execution command,
patch, generated plan, or permission grant. Use a direct immutable
reference to the existing proposal rather than copying, mutating, or
serializing its content. Capture a reviewer identity only if the caller
explicitly supplies it and an applicable privacy policy permits it.

Create an audit entry for the quality-gate decision when it enters the
workflow, and an additional entry only when an explicit human disposition
is supplied. A validator event must use `actor_type=validator` and no
human disposition; a human event must use `actor_type=human` and record
the disposition and exact scope reviewed. Keep records and entries frozen;
adding a later event returns a new record with an appended tuple, never
mutates an existing record.

`reviewed_at` records only the time supplied/created for a human
disposition. It is not evidence freshness and must not be used to infer
proposal source freshness. The record is ephemeral and is not an audit
store. A blocked `NEEDS_EVIDENCE` or `REJECT` result may have a
validator-generated audit entry, but cannot contain a human review
disposition because it was not presented for review.

## 5. Human Review Requirements

No proposal may become actionable without explicit human review. In this
slice, no proposal becomes actionable at all.

Before presentation, provide the reviewer with:

- the unchanged proposal and its exact scope;
- validation outcome and categorized reasons;
- evidence classes, citations/locators, provenance, freshness,
  applicability, and limitations;
- confidence level and all dimension rationales;
- recommendation, options, risks, assumptions, dependencies, and open
  questions; and
- the statement that acceptance for planning authorizes no later action.

The reviewer must explicitly choose a disposition for the presented
proposal. Silence, a prior decision for another proposal or version,
validation `ACCEPT`, confidence level, or proposal status cannot stand in
for human review.

Any later implementation requires separate explicit approval identifying
the proposal/version, plan, file scope, and implementation action. Test or
command execution, repository changes, commits, merges, pushes, releases,
and deployments each require their own applicable human approval. No
review disposition may trigger these actions.

## 6. Audit Requirements

### In-memory traceability and audit entries

Each immutable audit entry and its enclosing transient review record
should link:

- proposal ID and schema version;
- the exact proposal and validation result used for the event;
- event type and actor type, distinguishing machine quality-gate results
  from human decisions;
- validation decision, safe reason codes, and eligibility flag;
- proposal scope, confidence assessment, and evidence IDs/locators
  presented; and
- for human events, explicit disposition, exact scope acknowledged,
  optional rationale or evidence questions, optional privacy-approved
  reviewer reference, and timezone-aware review time.

Retain references to evidence identities and locators already present in
the proposal. Audit entries must not copy source contents or full proposal
text. Do not include secrets, credentials, unrelated user data, or full
transcripts. If sensitive content prevents safe presentation, record only
a non-sensitive reason code and keep the proposal blocked.

The event order is: quality-gate result first; only if that result is
`ACCEPT` and eligible may a human disposition follow. `NEEDS_EVIDENCE`
and `REJECT` can produce blocked validator entries but never human review
events. A missing or mismatched proposal/version reference prevents an
audit entry from being accepted.

### Persistence is out of scope

The existing model has no proposal content hash, stable revision
identifier, reviewer identity, review history, or storage API. The
smallest implementation keeps only the returned record and its audit
entries in memory and makes no durable audit or retention claim.
Persistent audit history, redaction, access control, retention/deletion,
and tamper-evidence require a separate privacy and storage design before
implementation.

## 7. Safety Constraints

The implementation must:

- inspect only the supplied proposal and validation result;
- leave both values unchanged and preserve frozen records;
- create no repository, filesystem, Git, database, or memory writes;
- run no code, tests, commands, hooks, subprocesses, or external services
  as part of review handling;
- generate no code, patches, diffs, implementation instructions, or
  executable actions;
- expose sensitive evidence only as permitted and return safe reasons
  when content cannot be shown;
- never treat a review disposition as implementation permission; and
- fail closed on missing, inconsistent, stale, or unsupported review
  inputs.

All outcomes are advisory and non-executing. No automatic implementation
or Capability Evolution is permitted.

## 8. Testing Strategy

Add focused unit tests in `tests/test_proposal_review_workflow.py` using
immutable, deterministic proposal and validation-result fixtures. No
repository scan, file read/write, UI, or persistence test harness is
required for this pure in-memory slice.

### Eligibility tests

- Matching `ACCEPT`, eligible result plus `READY_FOR_REVIEW` Enhancement
  proposal produces a review-ready record.
- `NEEDS_EVIDENCE` and `REJECT` never produce review eligibility and keep
  their validation reasons.
- `NEEDS_EVIDENCE` may proceed only after new evidence is supplied outside
  the workflow, the proposal is reconstructed and revalidated, and a
  matching `ACCEPT` result is returned.
- `REJECT` cannot be overridden for the same record; a corrected candidate
  requires a new proposal and validation result.
- Wrong proposal type, missing result, non-eligible ACCEPT, mismatched
  proposal reference, or inconsistent proposal status fails closed.

### State and disposition tests

- Draft, Needs Evidence, Ready For Review, Reviewed, and Rejected remain
  distinct workflow concepts and do not mutate `ProposalStatus`.
- Each human disposition is accepted only for an eligible presentation.
- Request evidence includes a non-empty question; accepted-for-planning
  remains non-actionable.
- Validator REJECT is recorded distinctly from human rejection.
- Repeated review or changed proposal scope/evidence requires a new
  review record and matching validation; prior disposition is not reused.

### Record and audit tests

- Review and validation records are frozen; tuple fields are immutable.
- Proposal and validation references identify the same unchanged proposal.
- Quality-gate and human-disposition audit entries have distinct event
  and actor types and preserve event order.
- Blocked outcomes cannot create human-disposition audit entries.
- Review time includes timezone information and is absent before a human
  disposition.
- Audit entries carry only references/minimal metadata and no copied
  source text, action payload, patch, or command.

### Safety tests

- No construction or validation builder is invoked by the review boundary.
- No filesystem access, writes, subprocesses, network calls, or action
  handlers occur.
- Sensitive/out-of-scope rejection paths do not disclose evidence content.

## 9. Success Criteria

The implementation is ready for review when:

1. Only a matching `ACCEPT` result and eligible `READY_FOR_REVIEW`
   Enhancement proposal can be presented for human review.
2. `NEEDS_EVIDENCE` and `REJECT` remain blocked and their reasons are
   surfaced safely.
3. Review states and human dispositions are separate from
   `ProposalStatus` and `ValidationDecision`.
4. Immutable review and audit records reference, rather than change, the
   proposal and validation result.
5. Human dispositions are explicit, scoped, and not reused across changed
   proposal versions or scopes.
6. “Accepted for planning” cannot trigger or authorize implementation,
   testing, repository writes, commits, merges, pushes, or deployments.
7. `ACCEPT` is the only outcome that enters review;
   `NEEDS_EVIDENCE` requires new evidence and revalidation; `REJECT`
   remains blocked for the supplied record.
8. Audit entries distinguish validator and human actors, preserve event
   order and traceability, and make no durable logging or retention claim.
9. Tests demonstrate no mutation, I/O, execution, persistence, or
   automated action coupling.
10. Unsupported proposal types and inconsistent inputs fail closed with
   explicit, non-sensitive reasons.

## 10. Smallest Safe Slice

Implement only:

1. A focused `scripts/proposal_review_workflow.py` module with immutable
   review disposition/result and audit-entry records, plus a function that
   checks a supplied proposal against its matching
   `ProposalValidationResult`.
2. A human disposition input accepted only after review eligibility has
   been established; return the disposition in an immutable in-memory
   record with a timezone-aware timestamp and explicit scope reference.
   Append an immutable human audit entry that points to the same proposal
   and validation result. A validator entry records ACCEPT,
   NEEDS_EVIDENCE, or REJECT with safe reason codes.
3. A `tests/test_proposal_review_workflow.py` suite for eligibility,
   ACCEPT/NEEDS_EVIDENCE/REJECT transitions, state separation,
   dispositions, audit attribution and ordering, record immutability, and
   no-action behavior.
4. No changes to the proposal model, construction, validation,
   repository/architecture awareness, persistence, UI, or project
   permissions.

The slice ends when the workflow returns an in-memory review record or a
blocked result. It performs no action following human review.

## Reference basis

- [PHASE5_2_PROPOSAL_REVIEW_WORKFLOW.md](./PHASE5_2_PROPOSAL_REVIEW_WORKFLOW.md):
  review eligibility, workflow states, dispositions, audit, and safety.
- [PHASE5_2_PROPOSAL_VALIDATION.md](./PHASE5_2_PROPOSAL_VALIDATION.md):
  quality decisions and review-gating rules.
- [PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md):
  human approval boundaries and separate authorization requirements.
- [PHASE5_2_IMPLEMENTATION_PLAN.md](./PHASE5_2_IMPLEMENTATION_PLAN.md):
  existing proposal lifecycle and distinct downstream approval gates.
- [scripts/proposal_model.py](./scripts/proposal_model.py):
  current proposal status and immutable proposal records.
- [scripts/proposal_construction.py](./scripts/proposal_construction.py):
  existing explicit-input Enhancement construction behavior.
- [scripts/proposal_validation.py](./scripts/proposal_validation.py):
  current validation outcomes and eligibility result.
