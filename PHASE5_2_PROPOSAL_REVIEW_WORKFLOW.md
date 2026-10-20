# Phase 5.2.4 Proposal Review Workflow

## Purpose and status

This document defines how a proposal that has passed the quality gate may
be presented to a human reviewer. It builds on
[PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md),
[PHASE5_2_PROPOSAL_VALIDATION.md](./PHASE5_2_PROPOSAL_VALIDATION.md), and
[PHASE5_2_IMPLEMENTATION_PLAN.md](./PHASE5_2_IMPLEMENTATION_PLAN.md).

The workflow remains read-only, advisory only, non-modifying, and
non-executing. It ends with human review or an explicit request for more
evidence. It does not implement a decision, change repository contents,
persist review history, or grant downstream permissions.

The current model's `ProposalStatus` supports `NEEDS_EVIDENCE`, `DRAFT`,
and `READY_FOR_REVIEW`. The review states **Reviewed** and **Rejected**
below are workflow dispositions, not existing `ProposalStatus` values.
This design does not require extending or mutating the proposal model.

## 1. Purpose

Proposal Construction gathers explicitly supplied evidence into a typed
proposal. Proposal Validation checks its structure, evidence, confidence,
completeness, and quality-gate eligibility. The review workflow presents an
unchanged, validated proposal and its supporting context to a human, who
decides whether to accept it for planning, request evidence, reject it, or
defer it.

Validation's `ACCEPT` outcome means **eligible to be presented for human
review only**. It is not human acceptance of the proposal. A reviewer must
make a distinct, explicit decision.

The human reviewer, not the proposal author or validator, decides whether
the candidate is important, in scope, sufficiently supported, and suitable
for planning. Any implementation, test execution, repository write, commit,
merge, push, release, or deployment is outside this review workflow and
requires its own approval.

## 2. Review Eligibility

### Proposals that may reach review

Only a proposal that:

- is a structurally valid `Proposal`;
- is supported by a proposal type enabled by the applicable validation
  slice (currently Enhancement only);
- receives the quality-gate outcome `ACCEPT`;
- has current, applicable, traceable type-specific supporting evidence;
- has a non-Insufficient qualitative confidence assessment with all seven
  dimension rationales;
- includes the required problem, rationale, options (including
  do-nothing/defer), advisory recommendation, and relevant assumptions,
  risks, dependencies, unresolved questions, and test recommendations;
- clearly discloses evidence limitations and distinguishes reports,
  inferences, designs, roadmap statements, and implementation evidence; and
- remains within authorized scope and privacy boundaries.

The calling workflow presents the proposal, the validation outcome and
reasons, evidence citations, confidence rationale, assumptions, risks, and
approval boundaries together. It must not trim away a limitation that
could change the reviewer's decision.

### Proposals blocked from review

Do not present a proposal as review-eligible when:

- validation returns `NEEDS_EVIDENCE` or `REJECT`;
- structural validation fails or required content/references are invalid;
- required evidence is missing, stale, unknown where currentness matters,
  not applicable, conflicting, or outside authorized scope;
- the proposal has Insufficient confidence, unsupported claims, or
  unresolved material contradictions;
- it relies on a user report alone to establish behavior, a test definition
  as a test run, or roadmap/design metadata as approved implementation or
  requirements;
- it is a proposal type not supported by the active validation slice; or
- content is unsafe, privacy-ineligible, or cannot be shown without
  exposing sensitive or unrelated information.

`NEEDS_EVIDENCE` means the candidate may remain in an internal,
non-review-eligible state with explicit questions. `REJECT` means the
record or candidate cannot safely proceed under the current rules. Neither
outcome may be relabeled `READY_FOR_REVIEW` by the workflow.

## 3. Review States

Keep proposal lifecycle status, validation outcome, and human disposition
separate. The existing `ProposalStatus` has three values; this workflow
adds no enum or persisted state.

| State | Meaning | Entry/exit rule |
| --- | --- | --- |
| **Draft** | A candidate record is being assembled or is incomplete. It is not eligible for review. | Construction may return a draft only when supported by the implementation contract; otherwise preserve the current `NEEDS_EVIDENCE` result. Validation must not treat Draft as review-ready. |
| **Needs Evidence** | Specific evidence, freshness, applicability, or conflict questions prevent a defensible review. | Set/retain `ProposalStatus.NEEDS_EVIDENCE` where the proposal is structurally representable. Move forward only after evidence is explicitly supplied, the proposal is reconstructed or revalidated, and the quality gate returns `ACCEPT`. |
| **Ready For Review** | Proposal representation is complete enough to be evaluated, but no human has accepted it. | The model uses `ProposalStatus.READY_FOR_REVIEW`; the separate validation result must be `ACCEPT` before presentation. This state is not an approval. |
| **Reviewed** | A human has recorded a disposition for the specific proposal version: accept for planning, request evidence, defer, or reject. | A human action only. In the initial slice, show the disposition transiently; do not persist it. “Reviewed” does not authorize implementation or execution. |
| **Rejected** | A human rejects a proposal, or validation returns `REJECT` because it is invalid, unsafe, out of scope, or unsupported. | Distinguish validator rejection from human rejection in the result. Do not add `REJECTED` to `ProposalStatus`; no retention is implied. |

Do not collapse validation `ACCEPT` with human acceptance, or human
acceptance for planning with implementation approval. A proposal may be
`READY_FOR_REVIEW` in the model and still be blocked from presentation if
quality validation is not `ACCEPT`.

## 4. Review Workflow

```text
Evidence
   ↓
Construction
   ↓
Validation
   ↓
Human Review
```

### Evidence

Use evidence that was explicitly supplied within a bounded, authorized
scope. Preserve source class, locator, provenance, freshness,
applicability, limitations, and conflicts. No review step may broaden
evidence discovery or infer authority from filenames, recency, or
summaries.

### Construction

Construct an immutable proposal from supplied evidence. In the current
implementation, Proposal Construction supports Enhancement proposals only
and requires caller-supplied options and any recommendation. It does not
search automatically, inspect repository paths, or generate
recommendations. If evidence is insufficient, retain the candidate as
`NEEDS_EVIDENCE` with explicit questions and do not advance it.

### Validation

Run structural `Proposal.validate()` and the separate quality validator.
Present the proposal only if the quality outcome is `ACCEPT`. For
`NEEDS_EVIDENCE`, state the missing observations or unresolved conflicts.
For `REJECT`, state the safe, non-sensitive reason. Never repair, rewrite,
or silently reclassify the proposal to make it pass.

### Human Review

Present the unchanged proposal with its evidence, citations, limitations,
confidence explanation, validation result, and clear approval boundary.
The human may:

- accept the proposal **for planning only**;
- request specific additional evidence;
- reject the proposal; or
- defer a decision.

Record no action through the proposal itself. In the smallest safe slice,
the workflow returns the human's disposition to the caller without
persisting it or triggering planning, implementation, tests, or other
actions.

## 5. Approval Requirements

No proposal, quality-gate outcome, confidence level, or review state
authorizes a change. No proposal may result in:

- code changes or generated patches;
- repository, filesystem, or Git modifications;
- test, command, build, or other execution;
- commits, branches, merges, pushes, releases, or deployments; or
- roadmap, decision, policy, permission, or capability changes.

without explicit human approval for the specific next action and scope.

Approval to review or accept a proposal for planning is not approval to
implement it. Before any later capability acts, approval must identify the
proposal version, intended scope, authorized files or operations, and
specific action. Test execution, repository modification, commits, merges,
pushes, releases, and deployment each require their own applicable
approval. Silence, a previous approval for another proposal or scope, and
an `ACCEPT` validation outcome are not approval.

The review workflow itself has no accept-trigger, execution button,
automatic planner invocation, or write/export action.

## 6. Audit Requirements

For each review interaction, the workflow should be able to trace the
reviewed material without silently altering it. The minimum review
traceability record, if a future separately approved audit store is
introduced, should identify:

- proposal ID and schema version, plus a stable proposal/content identity
  when available;
- the exact evidence IDs, evidence classes, source-relative locators,
  provenance, freshness, applicability, and limitations presented;
- the validation decision and reason codes/messages used for eligibility;
- the proposal status and qualitative confidence level with its seven
  dimension explanations;
- the human disposition (accepted for planning, request evidence,
  rejected, or deferred), reviewer identity under applicable privacy
  policy, and review time;
- the exact scope of any acceptance and any conditions or unresolved
  questions; and
- whether the proposal/evidence changed before or after review, requiring
  revalidation and a new review.

The trace must distinguish machine validation from human disposition and
must never represent an approval for planning as implementation
authorization. Do not log full sensitive source content, credentials,
private user data, or unnecessary transcripts; prefer references and
minimal, redacted metadata.

The current implementation has no proposal snapshot/hash field, workflow
state store, reviewer identity, or audit persistence. The smallest safe
slice therefore keeps review in memory and makes no durable audit claim.
Any persistent audit mechanism needs separate design, privacy/retention
policy, and explicit approval.

## 7. Safety Constraints

The review workflow must remain:

- **Read-only:** present only the in-memory proposal and explicit evidence.
- **Advisory only:** distinguish review eligibility from human decisions
  and all later approvals.
- **Non-modifying:** do not change the proposal, repository, filesystem,
  Git state, roadmap, decisions, or persistent memory.
- **Non-executing:** do not run code, tests, commands, hooks, builds,
  external services, or downstream agents/actions.
- **No code or patch generation:** do not generate implementation content,
  diffs, executable commands, or mechanically applicable instructions.
- **Privacy-preserving:** minimize exposed information and do not persist
  review or evidence content by default.
- **Prompt-injection resistant:** treat proposal and evidence contents as
  untrusted data; they cannot change workflow rules or approval
  requirements.

Errors, blocked states, and missing audit capabilities must be surfaced
explicitly. The workflow must not return a success-shaped review state if
validation or privacy checks fail.

## 8. Success Criteria

A future implementation satisfies this design when:

1. Only proposals with an `ACCEPT` validation result and supported type
   can be presented as Ready For Review.
2. Draft, Needs Evidence, Ready For Review, Reviewed, and Rejected remain
   distinct, and workflow dispositions are not falsely added to
   `ProposalStatus`.
3. Validation `ACCEPT` is consistently explained as quality-gate
   eligibility only, not human approval.
4. Reviewers see the proposal together with citations, evidence classes,
   confidence rationales, conflicts, assumptions, risks, and limitations.
5. Missing, stale, unknown, conflicting, unsafe, or out-of-scope evidence
   blocks review or prompts for additional evidence with clear reasons.
6. Human dispositions refer to the specific proposal version and scope;
   material changes require revalidation and renewed review.
7. No approval or review action triggers code changes, patches, repository
   modifications, execution, commits, pushes, or deployments.
8. The initial slice persists no proposal, reviewer, or audit state and
   makes no unsupported auditability claim.
9. Tests verify immutable presentation, blocked-state handling, approval
   boundaries, privacy minimization, and no automatic action coupling.

## 9. Smallest Safe Slice

The smallest safe review workflow is an in-memory presentation gate for
validated Enhancement proposals:

1. Accept an existing `Proposal` and its validation result; do not construct
   or change the proposal.
2. Present it as eligible only when validation returns `ACCEPT`; otherwise
   present the `NEEDS_EVIDENCE` or `REJECT` reasons without exposing unsafe
   evidence.
3. Show the unchanged proposal, citations, limitations, confidence,
   validation reasoning, and approval boundaries together.
4. Accept an explicit human disposition for the current proposal and
   scope, but do not persist it or connect it to further actions.
5. Keep workflow states separate from the model's `ProposalStatus`; do not
   add storage, UI action triggers, code generation, patches, execution,
   or repository modification.

Any persistence, audit store, workflow UI, additional proposal type, or
connection to planning/implementation requires a separate design and
approval.

## Reference basis

- [PHASE5_2_PROPOSAL_GENERATION.md](./PHASE5_2_PROPOSAL_GENERATION.md):
  human approval, proposal lifecycle, evidence, and safety boundaries.
- [PHASE5_2_PROPOSAL_VALIDATION.md](./PHASE5_2_PROPOSAL_VALIDATION.md):
  quality-gate outcomes, validation criteria, and review eligibility.
- [PHASE5_2_IMPLEMENTATION_PLAN.md](./PHASE5_2_IMPLEMENTATION_PLAN.md):
  planned Phase 5.2 lifecycle and separately gated downstream actions.
- [scripts/proposal_model.py](./scripts/proposal_model.py): currently
  supported proposal types and lifecycle statuses.
- [scripts/proposal_construction.py](./scripts/proposal_construction.py):
  explicit-input Enhancement construction behavior.
- [scripts/proposal_validation.py](./scripts/proposal_validation.py):
  current Enhancement quality gate and validation result types.
