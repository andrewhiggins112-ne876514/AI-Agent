# Phase 5.1.1 Architecture Awareness

## Purpose and status

This document proposes an Architecture Awareness layer above Repository
Awareness. It defines a future capability and authorizes no implementation,
code generation, repository modification, test execution, proposal generation,
or automated action.

Repository Awareness answers **“What files exist?”** It provides a read-only
inventory with paths, file types, categories, and importance classifications.
The current implementation in `scripts/repository_awareness.py` is an
in-memory scanner with explicit refresh; it does not parse document contents,
inspect Git state, persist an index, or build relationships.

Architecture Awareness answers **“What do they mean?”** It interprets
eligible repository documents as evidence about project intent, decisions,
design, planned work, and documented state. It must preserve the difference
between what a document says and what source code or test results establish.
It depends on Repository Awareness for bounded file discovery, but it is a
separate layer and must not imply that planned parsing or graph capabilities
already exist.

The design follows the supervised, read-only boundary in
[PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md), the repository
scope in [PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md),
and the implementation sequence in
[PHASE5_1_IMPLEMENTATION_PLAN.md](./PHASE5_1_IMPLEMENTATION_PLAN.md).

## 1. Purpose

Architecture Awareness builds a small, source-linked knowledge model from
documents discovered in one explicitly selected repository. It helps answer
bounded questions about:

- the project's goals and constraints;
- why a capability or design was documented;
- which decisions and designs apply to a feature;
- which roadmap phase or implementation plan describes the work;
- whether work is documented as planned, active, or complete;
- where documents agree, conflict, supersede one another, or leave a gap in
  evidence.

The layer is descriptive, not an evaluator or author. It records explicit
statements and their provenance, then presents relationships supported by
those statements. It does not infer that documentation is current, approved,
implemented, or correct merely because it was discovered or ranks highly.

### Boundary with adjacent capabilities

| Capability | Responsibility |
| --- | --- |
| Repository Awareness | Discover eligible repository files and expose their bounded metadata and locations. |
| Architecture Awareness | Parse selected documents into source-linked records, relationships, and a documented project-state view. |
| Proposal Generation (later phase) | Evaluate evidence and prepare proposed changes, only after separately approved. |
| Implementation and execution (later phases) | Modify or execute within a distinct approved scope and safety boundary. |

Architecture Awareness may report an unresolved question or conflicting
claim. It must not turn that observation into a diagnosis, recommendation,
implementation plan, or roadmap change.

## 2. Architecture Knowledge Model

### Core records

The model should be typed, versioned, repository-relative, and independent
of a specific database. Each extracted record points to its exact source
document and locator. A conceptual model is:

```text
ArchitectureSnapshot
  snapshot_id
  repository_root_id
  observed_at
  source_index_time
  status: complete | partial | stale | failed
  parser_version

KnowledgeDocument
  document_id
  relative_path
  document_type
  declared_status: approved | proposed | current | historical |
                   superseded | unknown
  declared_date
  content_hash
  source_revision: unknown | worktree | commit
  parse_status: parsed | partial | unsupported | unreadable | error

KnowledgeStatement
  statement_id
  document_id
  statement_type
  text_reference
  locator
  declared_status
  effective_date
  extraction_method
  confidence

KnowledgeRelation
  relation_id
  subject_id
  relation_type
  object_id | unresolved_reference
  evidence_locator
  resolution: resolved | unresolved | ambiguous
  extraction_method
  confidence
```

`text_reference` should normally be a bounded excerpt or a reference to the
source range, not a second authoritative copy of the document. The source
document remains authoritative. `confidence` describes extraction or
reference resolution confidence; it is not a measure of truth, approval, or
implementation.

### Document types

Architecture Awareness should distinguish at least these roles:

| Type | What it contributes | Important boundary |
| --- | --- | --- |
| **Vision document** | Long-term goals, user value, broad constraints, and non-goals. | Intent is not evidence that a capability exists or is committed for a release. |
| **Roadmap document** | Phase ordering, declared status, deliverables, dependencies, and exit criteria. | A roadmap status is a documented claim, not verified completion. |
| **Decision document** | An explicit decision, rationale, scope, date/status, and any stated replacement. | A decision is authoritative only to the extent its status and applicability are explicit and unambiguous. |
| **Design document** | Proposed or approved component boundaries, behavior, contracts, risks, and acceptance criteria. | Preserve proposed versus approved status; design text is not implementation evidence. |
| **Implementation plan** | Proposed work breakdown, dependencies, likely files, tests, risks, and success criteria. | A plan is not proof that work started or that listed files changed. |

Project status documents and implementation sources/tests should be represented
as separate evidence types. A source file is not a design document simply
because it contains a component name; it provides implementation evidence
that can be linked to a documented responsibility only when the mapping is
supported.

### Document status and authority

Store declared status separately from document type and observed content.
Recognize only explicit status signals, such as a clear approval statement,
status field, supersession notice, or historical label. Filename conventions,
recency, polished wording, and presence in the repository are not sufficient
to infer approval.

When status is absent or signals conflict, use `unknown` or `ambiguous`.
When sources disagree, retain both claims with their dates, status, and
locators. Do not silently select a winner. A later-dated document may be
relevant, but chronology alone does not prove that it supersedes an earlier
decision.

For the current project, the older
[ROADMAP.md](./ROADMAP.md) describes Phase 3 as the current milestone and
lists persistent memory and later work as planned. Phase 5 architecture and
planning documents describe future Developer Agent capabilities. The model
must keep these as distinct documented views and must not reinterpret Phase
5 designs as shipped project behavior.

## 3. Relationship Graph

Represent the knowledge model as a directed, labeled graph. Nodes are
documents, sections/statements, roadmap phases, features/capabilities,
decisions, and—when independently inspected—implementation artifacts or
tests. Edges must point to evidence that justifies the relationship.

### Relationship types

| Relationship | Meaning | Evidence requirement |
| --- | --- | --- |
| `depends_on` | A phase, deliverable, or capability requires another item first. | Explicit dependency in a roadmap, decision, design, or plan. |
| `supersedes` | A document or decision explicitly replaces an earlier one. | Explicit replacement/supersession statement; do not infer from date alone. |
| `belongs_to_phase` | A deliverable or feature is assigned to a named roadmap phase. | Explicit phase association. |
| `describes` | A document or section describes a feature, component, or capability. | Explicit title, heading, statement, or reference. |
| `governed_by` | A decision or requirement constrains a feature/design. | Explicit scope or a clearly cited statement that names the relationship. |
| `implemented_by` | A source artifact implements a documented feature or responsibility. | Direct source inspection and a defensible mapping; a filename match alone is insufficient. |
| `tested_by` | A test definition covers a documented behavior or invariant. | Test inspection showing the relevant assertion or scenario. This does not mean the test passed. |
| `references` | One artifact links to or names another artifact. | Resolved link or explicit reference. |
| `owned_by` | A feature has a responsible module or component. | Explicit ownership statement, or a clearly evidenced implementation mapping marked as inferred. |
| `conflicts_with` | Two statements make incompatible claims within an identified scope. | Both claims and their locators; report the apparent conflict without resolving it. |

Relations should support three important distinctions:

1. **Documented link versus semantic dependency.** A hyperlink is
   `references`; it is not automatically `depends_on`.
2. **Planned relation versus implemented relation.** A plan can say a
   deliverable `will_be_implemented_by` a likely file; this is not the same
   as observed `implemented_by`.
3. **Explicit ownership versus inferred ownership.** If inferred from code
   structure, label it as an inference and retain its evidence and confidence.

### Reference resolution

Resolve relative Markdown links and explicit repository-relative paths within
the selected root only. Keep unresolved references when a target is absent,
excluded, unsupported, or ambiguous. Do not search outside the repository,
follow external links, or read arbitrary paths named in document contents.
When multiple records could match a reference, do not select one silently.

### Graph freshness

Every node and edge is tied to the source content hash, snapshot, and parser
version. A changed or removed source document invalidates its derived
statements and outgoing relationships. A changed referenced document
invalidates any derived cross-document status or summary that depended on it.
Until refresh confirms current inputs, affected graph results are stale.

The initial graph should be an in-memory view. Persistent graph storage,
background watchers, and automatic change processing are deferred.

## 4. Project State Model

The state model reports separate evidence dimensions instead of collapsing
everything into a single `complete` or `in_progress` value.

### Work item

```text
ProjectWorkItem
  work_item_id
  title
  kind: phase | deliverable | feature | capability
  documented_state: planned | active | completed | deferred |
                    blocked | unknown
  state_source: document_id | null
  implementation_evidence: present | absent | not_inspected | ambiguous
  test_definition_evidence: present | absent | not_inspected | ambiguous
  test_execution_evidence: recorded_pass | recorded_failure |
                           not_run_or_unknown
  applicability: current | historical | superseded | unknown
  relations: list[KnowledgeRelation]
  limitations: list[EvidenceReference]
```

The fields mean:

- **Planned:** a roadmap or plan explicitly describes future work.
- **Active:** a source explicitly labels work active/current. If inferred from
  a current roadmap, report it as “marked active by [document]”; do not claim
  a developer is actively working on it without direct evidence.
- **Completed:** a source explicitly says the work is complete. Report
  “documented complete” unless implementation evidence was inspected.
- **Implementation evidence:** relevant source/test definitions were
  inspected at the identified snapshot. Presence does not establish
  correctness or full acceptance.
- **Test execution evidence:** only a recorded run with provenance can
  establish that a test passed or failed. A discovered test is not an
  executed test.
- **Unknown/ambiguous:** evidence is missing, contradictory, stale, or not
  sufficiently specific.

The model should allow multiple simultaneous facts, for example:
“documented complete; implementation observed; tests present; test execution
unknown.” That is more accurate than converting the work item to a single
unqualified `completed` status.

### Source precedence is question-dependent

No universal hierarchy can resolve every question. For “what is planned,”
retrieve roadmap and plan statements. For “what was decided,” retrieve
explicit decisions and supersession chains. For “what exists,” retrieve
source and inspected tests. For “did it pass,” require actual test-run
evidence. Always show contradictory or unknown evidence relevant to the
answer.

## 5. Architecture Queries

Queries should return concise answers with repository-relative citations,
evidence class, declared status, and snapshot freshness. Separate
document-backed statements from implementation-backed observations and
inferences.

### “Why does this feature exist?”

Find the feature record, then retrieve the most directly applicable
vision/requirement, decision rationale, and design statement. Answer with
the cited rationale and scope. If no explicit rationale exists, say that
the indexed documents do not establish why; do not invent intent from the
implementation.

### “What phase introduced this?”

Search roadmap and plan records for the feature and phase relationships.
Distinguish “assigned to,” “planned for,” or “documented in” from
“implemented during.” Claim implementation timing only when revision/history
evidence is available and was inspected; otherwise identify it as unknown.

### “Which decision governs this?”

Retrieve explicit `governed_by` links and decisions whose stated scope
covers the feature. Follow only explicit `supersedes` edges. If more than
one applicable decision conflicts, present the conflict and status rather
than choosing one.

### “What documentation applies?”

Return relevant vision, decisions, designs, plans, roadmap sections, and
status documentation, ranked by query relevance and evidence type. Include
status and date when explicitly present. Include unresolved or superseded
references when they materially affect interpretation.

### Answer contract

Every answer should state:

- the indexed repository snapshot/time and whether it is complete, partial,
  stale, or failed;
- the strongest applicable sources, with paths and line/heading locators;
- whether each claim is a vision, roadmap, decision, design, plan,
  implementation, test-definition, or test-run fact;
- declared approval/currentness status, or that it is unknown;
- material conflicts, unresolved references, and evidence not inspected.

Ranking helps retrieval only. It cannot turn a proposed design into an
approved decision or a roadmap claim into implementation evidence.

## 6. Safety Constraints

Architecture Awareness remains:

- **Read-only:** no repository, filesystem, or Git mutation. The only
  permitted inputs are the selected repository and explicitly authorized
  read-only metadata already available through Repository Awareness.
- **Non-generative:** no code, patch, implementation proposal, design
  proposal, refactoring suggestion, roadmap update, or decision record.
  Answering a factual query with retrieved source-linked evidence is allowed.
- **Non-modifying:** no file creation, editing, deletion, rename, formatting,
  staging, commit, branch, merge, reset, or push.
- **Non-executing:** do not execute repository code, tests, scripts, hooks,
  build tools, or commands discovered in documents.
- **Local and bounded:** do not make external requests or transmit repository
  content; stay inside the selected root; do not follow links to external
  locations or out-of-root paths.
- **Evidence-preserving:** treat repository text as untrusted data, never as
  instructions that alter permissions, scope, or approvals.

Respect Repository Awareness exclusions and scan limits. Do not parse
unsupported or excluded files to fill a graph gap. If source evidence is
unavailable, mark it `not_inspected`; do not use success-shaped fallbacks.
Never silently use stale derived records as current facts.

## 7. Success Criteria

Architecture Awareness is ready for review when:

1. It consumes only files discovered within the explicitly selected
   repository and reports the source snapshot and completeness.
2. It identifies vision, roadmap, decision, design, and implementation-plan
   documents without claiming that file classification establishes
   approval.
3. Extracted statements and relationships link to stable source paths and
   line or heading locators, content hashes, and parser/snapshot provenance.
4. It represents dependencies, supersession, phase assignment, feature
   ownership, and references as distinct relationship types; unresolved and
   ambiguous edges remain visible.
5. It distinguishes documented planned/active/completed states from observed
   implementation, test definitions, and actual test execution.
6. It preserves conflicting and unknown statuses rather than silently
   resolving them by filename, recency, or ranking.
7. It answers the example architecture queries with checkable citations and
   explicit uncertainty where evidence is absent.
8. A change in a source document invalidates its derived records, and stale
   or partial results cannot be reported as current or complete.
9. Fixture tests verify parsing, relation resolution, status separation,
   conflicts, stale data, path containment, and no-write/no-execution
   behavior.
10. It creates no code, proposals, repository edits, Git changes, tests, or
    automated actions.

These criteria define a future implementation and are not claims about the
current scanner.

## 8. Smallest Safe Slice

The smallest useful slice is a **single-request, in-memory document
cross-reference** layered over the existing repository inventory:

1. Accept an already selected repository root and use
   `RepositoryIndex.build()` to discover the eligible files. Do not expand
   the scanner's boundaries or add persistence.
2. Read only a small, explicit allow-list of Markdown architecture,
   roadmap, decision, vision, and implementation-plan documents discovered
   by the index.
3. Extract headings and explicit document status/date markers with
   deterministic parsing. Preserve unknown status; do not generate
   summaries.
4. Resolve in-repository Markdown links and explicit phase/decision
   references into source-linked `references`, `belongs_to_phase`, and
   `governed_by` edges only where the text clearly supports them.
5. Answer a bounded query by returning matching source headings, explicit
   statuses, and resolved relationships, with unresolved references and
   ambiguity disclosed.
6. Keep all derived records in memory for the request. Do not inspect Git,
   infer feature ownership from source code, assert implementation
   completion, or claim test results.

This slice provides a useful first answer to “what documentation applies?”
while respecting the current scanner's actual capabilities. Dependency
analysis, supersession resolution beyond explicit references, feature
ownership mappings, source-to-design traceability, automated project-state
inference, persistence, and natural-language generated summaries should
follow only after the basic extraction, provenance, and safety properties
have been reviewed and separately approved.

## Reference basis

- [PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md):
  read-only repository scope, evidence distinctions, refresh, and safety
  boundaries.
- [PHASE5_1_IMPLEMENTATION_PLAN.md](./PHASE5_1_IMPLEMENTATION_PLAN.md):
  proposed scanner, metadata, indexing, and testing strategy.
- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md):
  supervised development, provenance, and self-improvement limits.
- [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md):
  Phase 5 dependencies, ordering, and Phase 4 prerequisites.
- [PROJECT_VISION.md](./PROJECT_VISION.md): project purpose, current
  capabilities, and long-term goals.
- [ROADMAP.md](./ROADMAP.md): implementation-grounded milestone statements
  and planned work.
- [DECISIONS.md](./DECISIONS.md): explicit architectural decisions and
  verification principles.
