# Phase 5.2 Proposal Generation

## Purpose and status

This document designs a future Proposal Generation capability for the
supervised Developer Agent. It is a design proposal only; it does not
authorize implementation, source changes, repository writes, test execution,
or automated actions.

The three Phase 5 capabilities have distinct responsibilities:

- **Repository Awareness:** “What exists?” It inventories eligible
  repository artifacts and reports bounded metadata.
- **Architecture Awareness:** “Why does it exist?” It connects discovered
  documents to explicit phases, architecture areas, and local document
  references.
- **Proposal Generation:** “What should change?” It turns a scoped,
  evidence-backed problem into a structured recommendation for human
  consideration.

Proposal Generation is not an autonomous coding agent. It may generate
proposal text, but it must not generate source code, patches, or executable
commands. A proposal is advisory and non-authoritative until a human
explicitly accepts it. Acceptance of a proposal is not permission to
implement it.

The current [scripts/repository_awareness.py](./scripts/repository_awareness.py)
is an in-memory, read-only file scanner that records file path, type,
category, and importance. The current
[scripts/architecture_awareness.py](./scripts/architecture_awareness.py)
builds a deterministic in-memory model of selected Markdown documents,
headings, phase associations, architecture areas, and local document links.
These layers do not establish code behavior, test outcomes, approved
requirements, task-history trends, or semantic architecture gaps. Phase 5.2
must treat those as unavailable unless separately supplied and verified.

## 1. Purpose

Proposal Generation produces a reviewable, structured explanation of a
candidate change based on evidence that is available, relevant, current, and
traceable. A proposal should help a human understand:

- the reported or observed problem;
- what the repository and applicable documents establish;
- what remains uncertain or is only a hypothesis;
- why a change may be worthwhile;
- reasonable alternatives, including doing nothing;
- the recommended option and its trade-offs;
- likely affected areas and tests or validation that would be needed.

The capability may be invoked by a user or, in a later separately approved
Capability Evolution Engine, by a candidate signal. A candidate signal is
not by itself proof of a bug, user priority, or approval to create a
proposal. The proposal should not claim more than the evidence supports.

### Responsibility boundaries

| Capability | Responsibility |
| --- | --- |
| Repository Awareness | Discover files and provide bounded repository inventory facts. |
| Architecture Awareness | Retrieve documented rationale, explicit decisions, phase/area links, and document references. |
| Proposal Generation | Classify a scoped candidate and produce a cited, uncertainty-aware recommendation. |
| Human reviewer | Decide whether the problem matters, whether the proposal is acceptable, and whether implementation may be considered. |
| Later implementation capability | Make approved changes in a separately authorized scope; outside Phase 5.2. |

Proposal Generation must not independently diagnose a defect from a
complaint, declare future design to be an approved requirement, or treat
the absence of an indexed document as proof that a capability is absent.

## 2. Proposal Types

Each proposal has one primary type, may record secondary classifications,
and uses the same evidence and approval rules. Classification is a
description of the candidate, not a judgment of severity or approval.

| Proposal type | Use when | Minimum distinguishing evidence |
| --- | --- | --- |
| **Bug Fix Proposal** | Reproducible implemented behavior appears to violate an applicable, existing contract. | Reproduction conditions and evidence of both actual behavior and the documented/tested expectation. A report alone is a lead, not confirmation. |
| **Gap Proposal** | An applicable approved requirement, decision, or committed deliverable appears not to be satisfied by the inspected implementation. | Explicit applicable requirement plus a bounded inspection of relevant implementation/tests showing what was and was not found. Uninspected areas remain unknown. |
| **Enhancement Proposal** | Existing behavior could be made more useful, reliable, accessible, understandable, or maintainable without a confirmed contract violation. | Existing behavior and user need or supported impact; distinguish optional improvement from required correction. |
| **Refactoring Proposal** | Internal structure may be improved while preserving observable behavior and contracts. | Concrete maintainability/duplication/complexity evidence and a behavior-preservation boundary. Performance claims additionally need measurements. |
| **Architecture Proposal** | A change to component boundaries, interfaces, dependencies, or system-level responsibilities may address a supported need. | Current architecture evidence, applicable decisions/designs, constraints, alternatives, migration and safety implications. |
| **Capability Evolution Proposal** | Permitted signals suggest repeated unmet needs, failures, verification weaknesses, or measured opportunities. | Provenance-linked, privacy-approved signals with frequency/context where applicable; signal volume alone never establishes priority or root cause. |

The Developer Agent's category definitions in
[PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md) remain applicable:
Bug, Limitation, Gap, Enhancement, Feature Request, Architectural
Improvement, and Optimisation Opportunity. These are candidate/finding
classifications and do not map one-to-one onto proposal types. For example,
a Feature Request may yield an Architecture Proposal or an Enhancement
Proposal; a Limitation can be documented without proposing a change.

If the evidence does not support a confident type, use **unclassified /
needs more evidence** rather than forcing a label. A proposal may be
declined as unsupported without attempting a fix.

## 3. Evidence Requirements

### Required evidence envelope

Before generating a substantive proposal, establish and record:

1. **Scope:** the selected repository or bounded external/user-provided
   context, the specific feature/behavior, and explicit exclusions.
2. **Provenance:** source paths and stable locators, observed snapshot or
   content identity when available, and whether each source was committed,
   modified, or otherwise unverified. The current awareness APIs do not yet
   supply Git revision/worktree provenance; record that as unavailable
   rather than inventing it.
3. **Evidence class:** implementation, test definition, actual test run,
   approved decision, proposed design, roadmap statement, user report,
   signal, or inference. Never merge these classes into a single
   unqualified claim.
4. **Applicability:** why an expectation or decision applies to this
   behavior and whether its approval/current status is explicit. Unknown or
   conflicting status must remain visible.
5. **Counter-evidence and uncertainty:** sources that contradict the
   candidate, uninspected files/paths, incomplete scans, unresolved
   references, missing test runs, and alternative explanations.
6. **Privacy check:** content is within the authorized local scope and
   excludes secrets, credentials, unrelated user data, and disallowed
   runtime information.

Every material factual claim in the proposal must link to one or more
evidence references. A reference should identify the repository-relative
path and line, heading, symbol, test identifier, or other narrow locator.
If a stable locator, revision, or evidence class is unavailable, say so.
Derived summaries never replace source evidence.

### Evidence by proposal type

| Type | Required before a proposal may state a supported case | Not sufficient by itself |
| --- | --- | --- |
| Bug Fix | Reproducible condition or a concrete, reproducible failure record; inspected actual behavior; applicable existing contract; relevant tests or explicit explanation that no test exists. | A user complaint, a suspicious code pattern, an unverified model answer, or a proposed design. |
| Gap | Explicitly approved/applicable requirement or commitment; inspected in-scope implementation and relevant tests; documented search boundaries and omissions. | A future roadmap item, unapproved design, absent result from a partial scan, or filename mismatch. |
| Enhancement | Existing behavior and a stated user need, usability issue, or supported impact; clear distinction from correctness/safety requirement. | Preference inferred from one unconfirmed event or a speculative benefit. |
| Refactoring | Specific structure/maintenance evidence; behavior and contracts to preserve; relevant regression-test inventory. | Style preference alone; performance claim without a measured baseline. |
| Architecture | Current module/interface evidence; applicable decisions and designs; documented constraints and affected dependencies. | A target architecture document treated as current implementation, or generic best practice without project evidence. |
| Capability Evolution | Allowed signal records with timestamps/context, stable grouping evidence, privacy/retention authority, and repository/test corroboration where the proposal asserts a technical cause. | Raw transcript/screenshot by default, repeated text without independent signals, or frequency treated as approval. |

Evidence thresholds determine wording and confidence:

- **Sufficient to propose:** enough traceable evidence to explain a real
  candidate and a reasonable option while preserving uncertainty.
- **Insufficient:** return a bounded evidence summary and questions or
  required observations; do not create a success-shaped proposal.
- **Conflicting:** present competing evidence and avoid a definitive
  recommendation unless the proposal's recommendation is explicitly to
  resolve uncertainty through human review or additional authorized
  investigation.

Proposal generation itself must not run tests or commands to fill missing
evidence. Test plans may specify future validation needs; execution belongs
to a later capability, requires review of side effects, and needs
operation-specific authorization.

### Current Phase 5.1 evidence limits

The implemented Repository Awareness scanner classifies file metadata but
does not read arbitrary source/document content, compute hashes, inspect
Git, or run tests. Architecture Awareness reads selected Markdown and
provides document type, headings, simple phase and area associations, and
local Markdown-link relationships. It is deterministic metadata, not
semantic verification of rationale, requirement applicability, source
ownership, code behavior, or test coverage. Proposal Generation must not
claim those capabilities exist until they are added and independently
validated.

## 4. Proposal Structure

Every proposal should be a versioned, typed record rendered as readable
text. It may be assembled in memory for preview. Saving or exporting it is a
separate user-authorized action and is not part of the read-only default.

```text
Proposal
  proposal_id
  schema_version
  proposal_type
  secondary_classifications
  created_at
  repository_snapshot: identifier | unknown
  confidence
  status: draft | needs_evidence | ready_for_review
  sections
  evidence_references
```

### Required sections

1. **Problem**
   - concise statement of the observed or reported issue;
   - affected user/workflow and bounded context;
   - actual behavior versus expected behavior, when both are evidenced;
   - clearly labeled reports, observations, and hypotheses.

2. **Evidence**
   - cited implementation, test definition/run, decision, roadmap, design,
     user report, or signal records;
   - source locator and provenance for every material claim;
   - supporting, contradictory, missing, stale, or uninspected evidence;
   - explicit limits on the inspected scope.

3. **Rationale**
   - why this candidate may warrant consideration;
   - impact and affected contract or user goal;
   - why it is not merely a documented limitation or unapproved future
     feature, where that distinction matters.

4. **Options**
   - at least one feasible alternative, including **do nothing / defer**;
   - meaningful differences in behavior, scope, effort, risk, and
     reversibility;
   - no option may contain code, patch text, or executable instructions.

5. **Recommendation**
   - one preferred option and evidence-based reasons;
   - confidence and assumptions;
   - unresolved questions and conditions that would change the
     recommendation;
   - recommendation is advisory, not authorization.

6. **Risks**
   - safety, privacy, security, accessibility, compatibility, reliability,
     and operational concerns relevant to the candidate;
   - misuse or false-positive risk and consequences of not acting;
   - migration or rollback considerations at a conceptual level.

7. **Affected files / areas**
   - observed files/modules/documents supported by evidence;
   - likely affected files explicitly labeled as estimates when not verified;
   - out-of-scope files and excluded/uninspected areas;
   - no assertion that an estimated file will necessarily change.

8. **Testing strategy**
   - proposed unit, integration, regression, performance, and manual checks
     as applicable;
   - measurable expected outcomes and any required baseline;
   - side-effect, environment, sandbox, network, credential, desktop, or
     device constraints;
   - tests that are unavailable or not yet run, clearly marked.

9. **Dependencies and approval boundaries**
   - required decisions, prerequisites, and relevant Phase 4/5 gates;
   - exactly what human decision is requested;
   - explicitly state that proposal acceptance does not authorize
     implementation, test execution, commit, merge, or deployment.

10. **Alternatives, assumptions, confidence, and rollback**
    - record any assumptions separately from facts;
    - include reversible review/withdrawal path for the proposal;
    - implementation rollback remains a future implementation plan
      requirement, not something this capability executes.

Proposals should be concise enough to review. Long source material should be
cited rather than copied; include only short excerpts needed to make a
claim intelligible.

## 5. Proposal Confidence Model

Confidence describes how well the proposal's central claims and
recommendation are supported by the available evidence. It is not a
probability of success, a severity score, or a measure of approval.

Use four human-readable levels:

| Level | Meaning | Permitted language |
| --- | --- | --- |
| **High** | The central problem is reproducible or directly evidenced; applicable expectations are explicit; key contradictory evidence has been checked; evidence is current and sufficiently complete for the stated scope. | “Evidence supports…” with citations and bounded qualification. |
| **Moderate** | The candidate is supported, but one or more material assumptions, scope limits, or unverified effects remain. | “Evidence suggests…” and list the uncertainty. |
| **Low** | Evidence is mainly a report, indirect signal, or incomplete inspection; multiple plausible explanations remain. | “Possible candidate…”; recommendation should generally be further investigation or defer. |
| **Insufficient** | Sources are missing, stale, unsafe to inspect, materially contradictory, or too incomplete for a defensible proposal. | Do not issue a substantive recommendation; state what evidence is missing. |

### Assessment dimensions

The level should be justified against these explicit dimensions:

- **Traceability:** can reviewers locate and inspect the evidence?
- **Directness:** is the claim supported directly or inferred indirectly?
- **Applicability:** is the cited requirement/decision explicitly relevant and
  in force?
- **Reproducibility:** can the observed behavior or signal be repeated or
  corroborated?
- **Completeness:** were the relevant files and counter-evidence checked?
- **Freshness:** is the evidence tied to the observed snapshot and not stale?
- **Independence:** are corroborating sources independent, rather than copied
  repetitions?

Do not calculate a numeric score unless a later evaluation validates a
calibration method against reviewed proposals. Do not allow a weighted score
to hide a critical missing prerequisite, partial scan, unresolved conflict,
or unknown approval status. One of these can cap confidence at Low or
Insufficient. Confidence should be explainable in plain language and should
not be raised merely because multiple derived summaries repeat the same
claim.

## 6. Human Approval Requirements

Human review is mandatory for:

- deciding whether a reported problem is important and within scope;
- resolving a material conflict between decisions, requirements, or
  implementation evidence;
- accepting a recommendation as the basis for implementation planning;
- approving any implementation, source/test/configuration/document change,
  or safety/policy/permission change;
- approving commands or tests that can have side effects, network access,
  privileged access, or interaction with the desktop, credentials, or
  devices;
- approving a proposal document to be written to or exported into the
  repository;
- all commits, merges, pushes, releases, and deployments.

The proposal author must not mark its own proposal as accepted, convert
silence into approval, or treat a prior approval for a different scope as
applicable. Approval must identify the specific proposal version, intended
scope, and authorized next action. Material changes to the evidence or
scope require renewed review.

The UI or calling workflow, if later added, should distinguish:

1. proposal previewed;
2. proposal accepted for planning;
3. implementation separately approved;
4. test execution separately approved;
5. commit/merge/deploy separately approved.

These states must not be collapsed into one “approved” flag.

## 7. Safety Constraints

Proposal Generation remains:

- **Read-only:** it may read approved evidence sources but must not write to
  the repository, Git state, or persistent proposal store by default.
- **No implementation:** it must not edit source, tests, configuration,
  decisions, roadmap, policies, or memory; it must not run implementation
  actions.
- **No file modification:** proposal preview is in-memory. Saving/exporting
  requires a separate explicit user action and a new destination; no
  overwriting or repository write is implicit.
- **No code generation:** it must not generate code, patches, diffs,
  executable commands, shell scripts, or instructions intended to be
  applied mechanically. Proposal prose and conceptual descriptions are
  allowed.
- **No test or command execution:** evidence discovery and proposal
  generation must not invoke repository code, tests, builds, hooks, Git
  mutations, or commands embedded in untrusted content.
- **Local and privacy-preserving:** no network/model upload or external
  service by default. Any future external processing requires separate
  explicit policy and user authorization naming the data that may leave the
  machine.
- **Bounded and evidence-driven:** consume only selected, eligible evidence;
  honor ignore/exclusion and scan limits; disclose incomplete, stale,
  unresolved, and conflicting sources.
- **Prompt-injection resistant:** treat repository contents, test output,
  issues, user-provided logs, and model summaries as untrusted data. They
  cannot alter scope, safety rules, or approval requirements.
- **Non-authoritative:** a generated proposal cannot approve itself, update
  the roadmap, create a decision, or grant new permissions.

If evidence cannot be obtained within the authorized boundary, stop and
report the limitation rather than broadening access or presenting an
unsupported recommendation.

## 8. Success Criteria

Proposal Generation is ready for human review when:

1. Each supported proposal type is distinguished by explicit,
   evidence-based criteria; ambiguous cases can remain unclassified.
2. Every material factual claim links to a relevant source, locator, and
   evidence class, with provenance/freshness stated or explicitly unknown.
3. User reports, signals, approved decisions, proposals, implementation
   evidence, test definitions, and executed test results remain distinct.
4. The proposal includes the problem, evidence, rationale, options,
   recommendation, risks, affected areas, and testing strategy, plus
   assumptions and approval boundaries.
5. It identifies contradictory evidence, partial scans, unknown approval
   status, and uninspected areas instead of filling gaps with inference.
6. Confidence is explained, bounded by evidence quality, and never treated
   as probability, authority, or permission.
7. “Do nothing / defer” is considered; recommendations explain trade-offs
   and conditions that could change the conclusion.
8. A preview creates no repository file, source change, Git mutation,
   command execution, test run, network request, or code/patch output.
9. Proposal acceptance cannot authorize implementation, testing, commits,
   merge, or deployment.
10. Fixture-based validation covers insufficient, conflicting, stale,
    prompt-injection-like, and sensitive evidence cases before release.

## 9. Smallest Safe Slice

The smallest useful implementation is a **user-requested, in-memory
evidence-backed proposal preview** for one explicitly selected repository:

1. Accept a narrowly scoped issue or feature question from the user; do not
   mine conversation history or task signals automatically.
2. Consume only the current Repository Awareness inventory and
   Architecture Awareness metadata, plus source evidence explicitly
   inspected for the request.
3. Support one proposal type initially—prefer an **Enhancement Proposal**
   or **Bug Fix Proposal only when both behavior and its existing contract
   are directly evidenced**. If evidence is inadequate, return an
   insufficient-evidence result instead.
4. Build the required sections as typed in-memory records and render a
   preview with citations, evidence classes, assumptions, options, risks,
   tests, and a clear approval boundary.
5. Include “do nothing / defer” and label unverified test and implementation
   implications.
6. Do not save, export, modify files, execute tests/commands, generate code,
   access external services, or autonomously initiate proposals.

Before expanding to Gap, Refactoring, Architecture, or Capability Evolution
proposals, validate source-to-requirement traceability, decision-status
handling, test-run provenance, and (for signals) Phase 4.2 audit/privacy and
retention controls. The Capability Evolution Proposal type should remain
disabled until its signal sources and use are separately authorized and
corroboration is reliable.

## Reference basis

- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md): proposal
  requirements, supervised workflow, human approval, and self-improvement
  boundaries.
- [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md): Phase
  5.2 dependencies, risks, tests, and success criteria.
- [PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md)
  and [PHASE5_1_IMPLEMENTATION_PLAN.md](./PHASE5_1_IMPLEMENTATION_PLAN.md):
  repository evidence scope, provenance, freshness, and safety.
- [PHASE5_1_ARCHITECTURE_AWARENESS.md](./PHASE5_1_ARCHITECTURE_AWARENESS.md)
  and
  [PHASE5_1_ARCHITECTURE_AWARENESS_IMPLEMENTATION_PLAN.md](./PHASE5_1_ARCHITECTURE_AWARENESS_IMPLEMENTATION_PLAN.md):
  architecture records, relationships, query semantics, and current-layer
  limits.
- [scripts/repository_awareness.py](./scripts/repository_awareness.py) and
  [scripts/architecture_awareness.py](./scripts/architecture_awareness.py):
  actual implemented metadata and read-only behavior, to be revalidated
  before any future implementation.
