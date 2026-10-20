# Phase 5.1.1 Architecture Awareness — Implementation Plan

## Purpose and status

This document plans a future implementation of
[PHASE5_1_ARCHITECTURE_AWARENESS.md](./PHASE5_1_ARCHITECTURE_AWARENESS.md).
It is a design document only. It does not authorize implementation, code
generation, proposals, repository changes, test execution, or automated
actions.

The current [scripts/repository_awareness.py](./scripts/repository_awareness.py)
provides bounded, read-only file discovery and in-memory metadata with
`RepositoryIndex.build()` and `RepositoryIndex.refresh()`. It classifies
files by path and extension but does not read document bodies (except
`.gitignore`), extract headings or status, hash document contents, inspect
Git history, or build relationships. Architecture Awareness must be built
above that actual capability; planned metadata and graph features in this
plan are not currently implemented.

## 1. Scope

### What Architecture Awareness does

Architecture Awareness interprets selected documents discovered by
Repository Awareness and builds a bounded, source-linked, in-memory model
that can:

- identify vision, roadmap, decision, architecture/design, and
  implementation-plan documents;
- extract headings and explicit statements about goals, rationale,
  decisions, phases, deliverables, status, and dependencies;
- represent explicit document and work-item relationships;
- distinguish documented project state from observed source or test
  evidence;
- answer factual architecture queries with repository-relative citations,
  status, freshness, and uncertainty.

It accepts one explicitly selected repository and respects the scanner's
scope, exclusions, limits, and incomplete-result warnings. Original
documents remain authoritative; graph records are derived navigation
metadata only.

### What Architecture Awareness does not do

- Generate or recommend designs, implementation plans, code, patches,
  roadmap updates, or decisions.
- Diagnose bugs or gaps, rank work for implementation, or decide whether a
  documented architecture is good or correct.
- Treat file classification, document presence, or roadmap status as proof
  of approval, implementation, completion, or test success.
- Execute source, tests, scripts, hooks, or discovered commands.
- Modify repository files or Git state, create persistent index data, or
  trigger automated actions in the smallest implementation slice.
- Follow external links, read outside the selected repository, or send
  repository content to external services.

### Current implementation boundary

The existing scanner's `RepositoryFileMetadata` supplies path, file type,
category, and importance only. The first Architecture Awareness increment
therefore needs a bounded document reader and deterministic parser above
that inventory. It must not assume hashes, line locators, Git provenance,
document status, or graph relationships are available until those are
explicitly added and tested.

## 2. Architecture Knowledge Graph

### Model principles

- Use typed, versioned records with repository-relative paths.
- Keep nodes and edges tied to source document hashes, snapshot identity,
  parser version, and precise line/heading locators.
- Store references or bounded excerpts rather than treating copied text as
  authoritative.
- Preserve declared document state separately from inferred relationships
  and observed implementation evidence.
- Keep the graph in memory in the initial slice. Do not introduce a graph
  database or persistent cache.
- Make unresolved, ambiguous, stale, and partial records first-class
  outcomes.

### Logical schema

```text
ArchitectureSnapshot
  schema_version
  snapshot_id
  repository_root_id
  indexed_at
  source_index_complete
  status: complete | partial | stale | failed
  parser_version
  warnings: list[SnapshotWarning]

ArchitectureDocument
  document_id
  relative_path
  document_type: vision | roadmap | decision | architecture |
                 implementation_plan | status | unknown
  declared_status: approved | proposed | current | historical |
                   superseded | unknown | ambiguous
  declared_date: date | null
  content_hash: string | null
  source_revision: commit | worktree | unknown
  parse_status: parsed | partial | unreadable | unsupported | error

ArchitectureNode
  node_id
  kind: document | section | decision | phase | deliverable |
        feature | capability | source_artifact | test_definition
  title
  source_document_id: string | null
  locator: heading_path | line_range | null
  declared_state: planned | active | implemented | completed |
                  deprecated | unknown
  state_evidence_id: string | null

ArchitectureEdge
  edge_id
  source_node_id
  relation: references | depends_on | supersedes | belongs_to_phase |
            owns | governed_by | describes | planned_for |
            implemented_by | tested_by | conflicts_with
  target_node_id: string | null
  unresolved_target: string | null
  evidence_id
  relation_status: explicit | inferred | ambiguous
  resolution: resolved | unresolved | ambiguous
  confidence: high | medium | low

ArchitectureEvidence
  evidence_id
  document_id
  locator
  evidence_class: vision | roadmap | decision | design |
                  implementation_plan | implementation |
                  test_definition | test_run
  statement_kind
  content_hash
  excerpt_reference: string | null
  extraction_method
```

`confidence` describes the extraction or resolution, not whether a claim is
true, approved, or implemented. Do not attach a confidence score to explicit
status as a substitute for recording the source.

### Document-role records

| Document type | Extracted knowledge | Required distinction |
| --- | --- | --- |
| Vision | Goals, user value, constraints, non-goals, long-term capabilities. | Intent does not establish a release commitment or implementation. |
| Roadmap | Phases, declared status, deliverables, dependencies, exit criteria. | Status is reported as a roadmap statement unless corroborated independently. |
| Decision | Decision text, rationale, scope, status/date, explicit supersession. | Approval and applicability must be explicit; date alone does not establish authority. |
| Architecture document | Components, contracts, responsibilities, risks, invariants, acceptance criteria. | Proposed design remains distinct from approved design and runtime behavior. |
| Implementation plan | Work breakdown, likely files, dependencies, tests, risks, success criteria. | Planned files and deliverables are not evidence that work occurred. |

Project-status documents, source files, test definitions, and test-run
records are separate evidence classes. For example, a discovered test file
is not a test result, and a source file with a related name does not prove
that it implements a design requirement.

## 3. Relationship Discovery

### Discovery pipeline

1. Start from `RepositoryIndex.files`; select only supported, eligible
   documents from the selected root.
2. Read each selected document under the scanner's existing per-file and
   scan bounds. Decode failures, oversized inputs, and partial scans are
   explicit errors or warnings, never silently omitted.
3. Extract headings and stable line numbers. Apply deterministic parsing to
   explicit labels, document links, phase identifiers, decision references,
   and dependency phrases.
4. Resolve only repository-relative paths and unique known document/work
   item identifiers. Do not follow links or references outside the selected
   root.
5. Emit an edge only when its source text supports the relation. Preserve
   unresolved and ambiguous references with evidence locators.
6. Mark all inferred associations as inferred; do not promote them to
   explicit relations based only on lexical similarity or document
   proximity.

### Relationship rules

| Relationship to identify | Initial evidence and rule | Limits |
| --- | --- | --- |
| Dependencies | Explicit “depends on,” prerequisite, or structured dependency references in a roadmap/design/plan. | A document link alone is `references`, not `depends_on`. |
| Superseded documents | Explicit “supersedes,” “replaces,” or equivalent status/reference. | Do not infer supersession from date, filename, or apparent similarity. |
| Roadmap ownership | Explicit roadmap section assigns a deliverable or feature to a phase. | Label it `belongs_to_phase` or `planned_for`; do not claim implementation timing. |
| Phase ownership | A plan or roadmap explicitly assigns a phase to a named deliverable or capability. | If several phases mention it without explicit assignment, return ambiguous associations. |
| Implementation ownership | An explicit document states a module/component owns a feature. | Mapping source modules to ownership is deferred until source inspection exists; filename matches alone are insufficient. |
| Decision governance | A decision explicitly states scope or a document explicitly links the decision to a feature/contract. | Similar wording is not proof that a decision governs a feature. |
| Implementation mapping | Source inspection links a symbol or module to a documented responsibility. | Deferred beyond the smallest slice; it requires direct source evidence and must remain labeled as observed or inferred. |
| Test coverage mapping | An inspected test definition asserts the relevant behavior or invariant. | Deferred beyond the smallest slice; test presence does not mean it passed. |

### Explicit versus inferred

The initial implementation should support a deliberately small relation
set: `references`, `belongs_to_phase`, and explicitly stated
`governed_by`/`depends_on` relations when a deterministic rule identifies
both endpoints and the supporting text. It should not use an LLM to invent
edge types or resolve ambiguous references. More advanced semantic
extraction requires a separate design and approval.

## 4. Project State Model

The requested state labels are:

- **planned** — a roadmap, design, or implementation plan explicitly
  describes future work.
- **active** — a source explicitly marks work current/active. If the only
  evidence is a roadmap label, report “documented as active by [source]”;
  this is not evidence that someone is currently working on it.
- **implemented** — relevant source artifacts have been inspected and
  directly mapped to the work item. Implementation evidence does not prove
  correctness, acceptance, or test success.
- **completed** — a source explicitly says the work is complete. Report as
  “documented complete” unless separately corroborated; never infer from
  files existing.
- **deprecated** — an explicit decision or status statement marks the item
  deprecated or retired. Do not infer deprecation from absence or
  supersession alone.
- **unknown** — evidence is missing, conflicting, stale, or insufficient.

Represent documentary status and implementation evidence on separate
fields, so one work item can be both “documented complete” and “implementation
not inspected.” Suggested structure:

```text
WorkItemState
  node_id
  documented_state: planned | active | completed | deprecated | unknown
  implementation_state: observed | not_inspected | absent | ambiguous
  test_definition_state: observed | not_inspected | absent | ambiguous
  test_run_state: recorded_pass | recorded_failure | not_run_or_unknown
  applicability: current | historical | superseded | unknown
  evidence_ids: list[string]
```

`implemented` is an evidence-backed implementation state, not a synonym for
“completed.” If documents conflict, keep their individual claims and set the
resolved summary to `unknown` or `ambiguous`; do not pick the newest claim
automatically. A test definition cannot establish `recorded_pass`.

## 5. Architecture Query Layer

The initial query layer should be deterministic retrieval over indexed
document titles, headings, explicit terms, and graph edges. It returns
evidence, not generated recommendations. A query result includes snapshot
freshness/completeness, source-relative path and locator, document type,
declared status, relation type, and unresolved/conflicting evidence.

### Supported questions

| User question | Retrieval path | Answer boundary |
| --- | --- | --- |
| “Why does this exist?” | Feature/capability mentions → vision goals, decision rationale, design statements. | Cite explicit rationale; say when documents do not establish why. |
| “Which phase owns this?” | Feature/deliverable → explicit roadmap or plan `belongs_to_phase` edges. | Say “assigned/planned for”; do not claim it was implemented in that phase. |
| “Which decision created this?” | Feature/contract → explicit decision references, scope, and rationale; follow explicit supersession edges. | Distinguish the decision's statement from whether it remains applicable. |
| “What documents apply?” | Retrieve direct references, related headings, explicit governance, and relevant vision/roadmap/decision/design/plan records. | Show evidence types/status and include ambiguity or conflict. |

### Query behavior

- Prefer exact document, heading, phase, decision, and feature matches.
- Use lexical matching only to find candidate evidence, not to assert a
  relationship.
- Rank by question relevance and evidence type; ranking cannot turn a
  proposal into an approved decision or a plan into implementation.
- Return a bounded number of evidence references and say when results are
  incomplete.
- Do not answer unsupported questions by guessing or generating new
  architectural interpretation.

Natural-language model synthesis, unrestricted repository search, semantic
embeddings, and proposal generation are not part of the minimum
implementation.

## 6. Refresh Strategy

### Initial build

1. Require a repository root already selected under Repository Awareness.
2. Call `RepositoryIndex.build()` and stop or mark the result partial if the
   underlying scan is incomplete.
3. Select only discovered, supported documents by explicit type mapping,
   configured path/name patterns, or conservative headings. Record the
   classification source and ambiguity.
4. Read each selected document once, subject to byte and count limits;
   compute a content hash and extract heading/line locators and explicit
   metadata.
5. Build the in-memory nodes and edges from those extracted records.
6. Return the graph snapshot and diagnostics. Do not persist it or write
   under the scanned repository.

### Incremental updates

Incremental updates require a prior snapshot and stable content hashes.
They are a later capability, not part of the first slice. Once explicitly
approved and persistence is designed:

- compare eligible document paths and hashes to the prior snapshot;
- parse added or changed documents only;
- remove or invalidate records sourced from deleted/renamed documents;
- rebuild edges that point to changed records or resolved targets;
- invalidate all affected records when parser, schema, classification, or
  scan-policy versions change;
- publish a new snapshot only after its completeness and references are
  validated; otherwise preserve the old snapshot but mark it stale.

No background filesystem watcher is included. Do not claim “live” state.

### Document refresh

A user-requested document refresh re-reads the selected document only if it
remains in the current Repository Awareness inventory and passes existing
exclusions and limits. It recomputes the document hash and derived sections
and edges. Any edge or answer depending on that document is marked stale
until recalculated. A full refresh rebuilds the in-memory graph from a new
repository index. Refresh must not invoke project code, tests, Git mutation,
or document cleanup.

### Freshness and failure

The graph snapshot is current only for the exact document hashes and parser
version it records. If a document cannot be read, a scan limit is reached,
or a link cannot be resolved, preserve that condition in snapshot warnings
and relation state. Never substitute stale records as if they were current.

## 7. Safety Constraints

Architecture Awareness remains:

- **Read-only:** no writes to the repository, Git metadata, or external
  persistent stores in the initial implementation.
- **Non-generative:** no code, patches, proposals, recommendations, roadmap
  edits, or decision records. Factual retrieval is allowed.
- **Non-modifying:** no file creation/edit/deletion/rename/format, Git
  staging or history mutation, or automated action.
- **Non-executing:** no source, tests, scripts, hooks, build commands, or
  commands discovered in documents.
- **Bounded and local:** honor root containment, allow-list, exclusions,
  scanner limits, and query result limits; make no external requests.
- **Evidence-safe:** treat document contents as untrusted data, never as
  permission or instructions; do not follow external links or arbitrary
  paths named in content.
- **Honest about evidence:** distinguish explicit, inferred, unresolved,
  ambiguous, stale, partial, and unknown records.

If path safety, document decoding, scope, or snapshot consistency cannot be
established, stop or return an explicit partial result. Do not expand the
scan to fill missing graph data.

## 8. Testing Strategy

All tests below are requirements for a future implementation; none are run
or authorized by this plan.

### Unit tests

- Document type and status extraction for each supported role, including
  missing, conflicting, and malformed status labels.
- Stable heading and line locator extraction, including duplicate headings,
  nested headings, Unicode text, and empty documents.
- Hash and parser-version metadata changes invalidate derived records.
- State-model tests keep `planned`, `active`, `implemented`, `completed`,
  `deprecated`, and `unknown` distinct.
- Ranking and query matching do not change approval/state or create
  relationships from lexical similarity alone.
- Decode, read, size-limit, and partial-snapshot failures are explicit.

### Relationship tests

- Resolve valid in-repository links and explicit phase/decision references.
- Preserve unresolved targets, excluded targets, duplicate names, and
  ambiguous references without selecting a target arbitrarily.
- Distinguish `references` from `depends_on`, `belongs_to_phase`, and
  `governed_by`.
- Require explicit evidence for `supersedes`; later dates and similar
  filenames alone do not create that edge.
- Keep planned implementation ownership separate from observed
  `implemented_by`; filenames alone never establish ownership.
- Preserve conflicting edges and their source locators.
- Verify all paths remain within the selected repository, including
  traversal strings and external URLs.

### Architecture graph tests

- Build a fixture graph containing vision, roadmap, decisions, designs,
  implementation plans, and status evidence; assert exact nodes, edges, and
  evidence provenance.
- Verify partial scans produce partial graph snapshots, never complete
  snapshots.
- Edit, delete, rename, or retarget a document and verify affected nodes,
  edges, and query results become stale or are rebuilt.
- Test each example query against fixture documents and expected
  repository-relative citations.
- Confirm `implemented` requires direct inspected source evidence,
  `completed` requires explicit completion evidence, and `deprecated`
  requires an explicit deprecation record.
- Confirm document parsing and queries create no files, modify no source or
  Git state, execute no code/tests, make no network requests, and generate
  no proposals or patches.
- Treat prompt-injection-like text inside fixture documents as inert data;
  it must not expand scope or alter safety behavior.

## 9. Success Criteria

The implementation is ready for human review when:

1. It builds an in-memory graph solely from eligible documents discovered
   inside one selected repository.
2. Vision, roadmap, decision, architecture, and implementation-plan
   documents are separately typed, with declared status and parsing
   uncertainty preserved.
3. Every node, statement, and edge cites a path, line/heading locator,
   content hash, and snapshot/parser provenance when available.
4. Dependency, supersession, roadmap/phase assignment, implementation
   ownership, and references are distinct relations with explicit or
   inferred provenance.
5. The project-state model distinguishes all requested states and separates
   documented state from inspected implementation and actual test-run
   evidence.
6. The four example queries return bounded, evidence-linked answers and
   surface unknown, ambiguous, stale, or conflicting sources.
7. Document refresh invalidates dependent records; partial or stale graphs
   are never presented as complete/current.
8. Tests demonstrate read-only, non-generative, non-modifying, and
   non-executing behavior.
9. The graph is disposable and rebuildable without affecting repository
   files or Git state.

These criteria are future acceptance criteria, not claims about the current
Repository Awareness implementation.

## 10. Smallest Safe Slice

The minimum useful implementation is a **single-request, in-memory
document cross-reference**:

1. Use the existing `RepositoryIndex.build()` for bounded file discovery.
2. Read an explicit, small allow-list of discovered Markdown documents
   representing vision, roadmap, decisions, architecture/design, and
   implementation plans.
3. Extract document headings, line numbers, explicit status/date markers,
   and content hashes using deterministic local parsing.
4. Build document/section nodes and only three initial relation kinds:
   `references`, explicit `belongs_to_phase`, and explicit
   `governed_by`/`depends_on` where both endpoints are unambiguous.
5. Answer “What documents apply?” and “Which phase owns this?” by returning
   matching sections and explicit links, with unresolved references and
   unknown status disclosed.
6. Keep all results in memory. Do not inspect source code to assign
   implementation ownership, infer a feature's creator, resolve
   supersession by date, claim implementation/completion, run tests, persist
   the graph, or generate summaries/proposals.

This slice depends on adding a bounded document reader and parser above the
current inventory; it does not require changing the scanner's core
classification behavior. It should be reviewed and approved before
implementation. Incremental persistence, semantic relationship extraction,
implementation ownership, source/test traceability, richer state
reconciliation, UI integration, and generated natural-language summaries
are later work.

## Reference basis

- [PHASE5_1_ARCHITECTURE_AWARENESS.md](./PHASE5_1_ARCHITECTURE_AWARENESS.md):
  architecture knowledge model, relationship graph, state and query
  semantics, safety limits, and minimum slice.
- [PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md):
  repository boundary, provenance, evidence classes, exclusions, and
  read-only contract.
- [PHASE5_1_IMPLEMENTATION_PLAN.md](./PHASE5_1_IMPLEMENTATION_PLAN.md):
  proposed scanner interface, metadata, refresh, and repository tests.
- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md) and
  [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md):
  supervised development boundary and phase dependencies.
- [PROJECT_VISION.md](./PROJECT_VISION.md), [ROADMAP.md](./ROADMAP.md), and
  [DECISIONS.md](./DECISIONS.md): project intent, implementation-grounded
  status, and explicit decisions.
