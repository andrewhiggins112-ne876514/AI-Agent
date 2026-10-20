# Phase 5.1 Repository Awareness — Implementation Plan

## Purpose and status

This plan describes how to implement the read-only Repository Awareness
capability defined in
[PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md).
It is an implementation design, not authorization to change code or run
repository commands.

The current project is a local Windows/Python assistant with a Tkinter UI,
Ollama request path, desktop tools, and task-execution work. Repository
Awareness is a separate, read-only engineering-information capability. It
must not dispatch desktop actions or use the task runner to act on a
repository. The Phase 5 documents are proposed architecture, while
[ROADMAP.md](./ROADMAP.md) and [DECISIONS.md](./DECISIONS.md) contain older
status and decision records; implementation must first inspect the actual
approved baseline and preserve their evidence status.

## 1. Scope

### What Repository Awareness does

- Operates on one explicitly selected repository root.
- Discovers allow-listed source, test, documentation, architecture, roadmap,
  and decision files.
- Reads Git identity and worktree status without changing Git state.
- Builds a bounded, local inventory with file metadata, hashes, document
  sections, and deterministic source locators.
- Provides evidence-linked retrieval and descriptive answers about what the
  selected repository contains.
- Marks incomplete scans, stale entries, ambiguity, and source status
  uncertainty explicitly.

### What Repository Awareness does not do

- Generate, edit, or suggest code.
- Generate implementation, design, refactoring, or roadmap proposals.
- Create, modify, rename, delete, or format files in the repository.
- Execute source, tests, build tools, scripts, hooks, or commands discovered
  in project metadata.
- Stage, commit, branch, merge, reset, rebase, or push.
- Trigger Jarvis desktop actions, other tools, or automated workflows.
- Upload source or index contents to a remote model or service.
- Diagnose or prioritize bugs, feature requests, architecture gaps, or
  optimization opportunities.

Questions asking what to implement or how to change the project are outside
this capability. The system may return the relevant existing evidence and
state that proposal generation is not included in Phase 5.1.

### Read-only boundary

Repository reads are confined to the selected root and authorized metadata
queries. Any persistent index is stored outside the repository in a
preconfigured local application-data directory. If that destination cannot
be validated, use a non-persistent in-memory scan or stop.

The index must not run project code to discover information. Even apparently
read-only commands such as build/test discovery may execute hooks or
repository-controlled code and are excluded from Phase 5.1.

## 2. Repository Scanner

### Scanner stages

1. **Select root:** receive an explicit user-selected root or approved
   per-session setting; canonicalize it and confirm that it is a directory.
2. **Establish snapshot:** read repository identity, HEAD revision, branch,
   and worktree status through non-mutating Git inspection. If Git metadata
   is unavailable, continue only with a clearly marked non-Git snapshot.
3. **Load scan policy:** apply supported file types, allow-listed
   categories, exclusions, size/depth/file-count limits, and ignore rules.
4. **Enumerate:** walk deterministically, without following links outside
   the root; record excluded/truncated paths and reasons.
5. **Classify:** assign file category using configured patterns and
   metadata, then preserve confidence and classification source.
6. **Extract:** compute hashes and parse only supported text formats using
   bounded, deterministic extractors.
7. **Publish result:** return a complete or partial snapshot with errors,
   limits reached, and source locators. Never label a partial scan complete.

### File categories and discovery

| Category | Discovery signals | Extracted facts |
| --- | --- | --- |
| Source files | Known source extensions and configured source directories; project manifests may inform languages but are not executed. | Relative path, language/type, size, hash, module/class/function outline where a deterministic parser is available. |
| Test files | Conventional test names/directories, test configuration, and explicitly configured patterns. | Test path, identifiers when statically parseable, fixtures/markers, framework metadata. Test pass status is never inferred. |
| Documentation | Allow-listed text/document extensions such as Markdown and plain text. | Headings, links, bounded sections, dates/status labels when explicitly stated. |
| Architecture documents | Explicit classification mapping and conservative filename/title patterns. | Components, responsibilities, contracts, invariants, dependencies, risks, and acceptance criteria as documented statements. |
| Roadmap documents | Explicit mapping, filename/title patterns, and milestone headings/status labels. | Phase/milestone title, documented status, tasks, dependencies, deliverables, and exit criteria. |
| Decision records | Explicit mapping and decision/architecture headings. | Decision title, status, date, rationale, scope, and explicit supersession references. |

Classification is metadata, not a claim of authority. If a file could fit
multiple categories, retain multiple labels or mark it ambiguous; do not
silently select a status that changes how its content is interpreted.

### File filters

Use a small configurable allow-list, initially including:

- text source files for known project languages;
- test source files and test configuration;
- Markdown and plain-text documentation;
- explicitly selected configuration manifests, read as data only;
- Git metadata queried through non-mutating operations.

Do not read arbitrary binary files. A future requirement for additional
formats must add a bounded parser and tests; file extension alone is not
permission to parse potentially sensitive content.

Limits must be explicit and surfaced, including:

- maximum traversal depth;
- maximum number of candidate files;
- maximum per-file size;
- maximum aggregate bytes;
- maximum document sections or extracted symbols per file;
- parsing time budget per file and per scan.

The exact values should be configuration defaults selected during
implementation and validated against representative repository sizes.
Exceeding a limit yields a partial scan status and a clear list/count of
omitted material, not silent omission.

### Exclusions and ignore rules

Always exclude:

- `.git` object/index internals from ordinary content indexing;
- virtual environments, dependency caches, build outputs, generated
  artifacts, bytecode, and temporary directories;
- local runtime logs, screenshots, captured screen content, and local
  databases;
- credential stores, private keys, tokens, secrets, and environment files;
- user home directories or other paths outside the selected root;
- files explicitly excluded by the user or repository scan policy.

Respect `.gitignore` for untracked and ignored paths. Do not rely on
`.gitignore` as the only protection for sensitive data: apply a separate
deny-list and path policy. Avoid interpreting repository-controlled ignore
patterns as commands. Report excluded categories and counts without exposing
sensitive filenames if names themselves are sensitive.

For symlinks, junctions, and reparse points, do not follow targets outside
the canonical root. The safest initial implementation may skip all linked
directories/files and record the reason. Prevent path traversal and
case-normalization mistakes on Windows.

### Refresh behavior

- **Initial scan:** full bounded scan on explicit user request or first
  repository-awareness query.
- **Per-query validation:** recheck repository root identity and the
  relevant files' hashes/revision provenance before using cached metadata.
- **Incremental refresh:** when a later implementation adds a persistent
  index, reprocess only changed/deleted/renamed eligible files, plus records
  whose extractor or policy version changed.
- **Full refresh:** available only as a user-requested read-only rebuild;
  replace the derived index atomically in the external index location so a
  failed scan does not masquerade as a complete new snapshot.
- **No watcher by default:** background monitoring is outside the smallest
  slice. Do not imply an index is current without revalidation.

If Git state changes during scanning, the result must identify that the
snapshot may be mixed or abort and retry only if a bounded, read-only retry
policy is later approved. Do not lock or alter the checkout to obtain a
consistent snapshot.

## 3. Metadata Store

### Design principles

- Keep schemas versioned and independent of a storage engine.
- Treat the repository as source of truth; metadata is a disposable index.
- Store repository-relative paths by default.
- Track revision, content hash, scan policy, extractor version, and
  completeness.
- Do not persist source contents or summaries in the smallest slice.
- If persistence is used later, locate it outside the repository and define
  deletion/retention behavior.

The following examples are logical schemas, not a mandate to use a specific
database or serialization format.

### Repository snapshot

```text
RepositorySnapshot
  schema_version: integer
  repository_id: string
  root_fingerprint: string
  head_commit: string | null
  branch_name: string | null
  worktree_state: clean | dirty | unavailable | unknown
  observed_at: timestamp
  scan_policy_version: string
  scanner_version: string
  status: complete | partial | failed | stale
  limits_reached: list[string]
```

`root_fingerprint` should avoid revealing absolute paths outside the local
machine; use a stable local identifier or keyed/local derivation rather than
displaying a raw home path in answers.

### File record

```text
RepositoryFile
  file_id: string
  repository_id: string
  relative_path: string
  categories: list[Source | Test | Documentation | Architecture | Roadmap |
                   Decision | Configuration | Other]
  media_type: string | null
  language: string | null
  size_bytes: integer
  content_hash: string | null
  revision_provenance: committed | modified | untracked | ignored | unknown
  classification_source: explicit_mapping | path_pattern | content_heading |
                        unknown
  parse_status: parsed | metadata_only | excluded | unreadable |
                unsupported | error
  exclusion_reason: string | null
  scanned_at: timestamp
```

### Document record

```text
DocumentSection
  section_id: string
  file_id: string
  heading_path: list[string]
  start_line: integer | null
  end_line: integer | null
  document_type: architecture | implementation_plan | roadmap | decision |
                 vision | status | other
  declared_status: approved | proposed | current | historical |
                   superseded | unknown
  declared_date: date | null
  content_hash: string
  extracted_by: string
```

The status fields record only explicit document evidence. The scanner must
not infer that a proposal became approved or that an implementation plan was
completed merely because source code appears related.

### Dependency and relationship records

Dependencies and directory relationships are distinct:

```text
RepositoryDependency
  dependency_id: string
  source_file_id: string
  target_file_id: string | null
  target_reference: string
  kind: import | document_link | test_reference | decision_reference |
        roadmap_dependency | architecture_relation
  resolution: resolved | unresolved | ambiguous
  evidence_locator: string
  extractor: string
```

```text
DirectoryNode
  directory_id: string
  repository_id: string
  relative_path: string
  parent_directory_id: string | null
  child_file_ids: list[string]
  child_directory_ids: list[string]
  scan_status: complete | partial | excluded | unreadable
```

Import relationships should be emitted only by deterministic language
parsing; text references should be labeled as textual/document links, not
runtime dependencies. Unresolved or ambiguous targets remain explicit.

### Storage choice

For the smallest safe slice, keep metadata in memory for the current
request. If a persistent index is later justified, start with a simple,
versioned local manifest in the approved application-data directory. A
database, embedding store, or graph database is not required for the first
implementation.

## 4. Architecture Knowledge Model

Repository Awareness builds a descriptive model, not a judgment engine.

### Architecture documents

Extract source-linked statements about components, responsibilities,
contracts, invariants, dependencies, risks, and acceptance criteria. Preserve
the document's explicit status and revision. An architecture document can
describe a future design; that text must not be presented as code behavior.

### Implementation plans

Record the proposed sequence, deliverables, likely files, dependencies, test
requirements, and success criteria. Mark every statement as planned or
proposed unless a separate current implementation source confirms it. A
plan's existence does not imply that its work started or completed.

### Roadmap phases

Represent each phase as a document-sourced record:

```text
RoadmapPhase
  phase_id: string
  title: string
  declared_status: complete | current | planned | future | deferred | unknown
  deliverables: list[EvidenceReference]
  dependencies: list[EvidenceReference]
  source_revision: string
```

The declared status is a roadmap statement. It is not independently verified
completion. Where source/tests have not been inspected, state that limitation.

### Completed work and active work

Completion and activity must be reported as evidence-derived states:

- **Documented complete:** a source document explicitly marks the work
  complete.
- **Implementation evidenced:** relevant source or test definitions exist
  at the observed revision.
- **Test executed/passed:** only available from a real, recorded test
  execution; Phase 5.1 does not execute tests and therefore cannot make this
  claim.
- **Active/current:** a document explicitly labels the work current, or
  repository activity is observed in version-control metadata. Distinguish
  these: “marked current by roadmap” is not the same as “currently being
  developed.”
- **Unknown/conflicting:** evidence is incomplete, stale, or inconsistent.

Do not collapse these states to a single “done” or “in progress” label.
Repository Awareness may present the differences, but it must not generate a
fix, implementation proposal, or roadmap change.

## 5. Repository Index

### Search strategy

Use a deterministic, staged search:

1. Match exact paths, filenames, symbols, headings, test identifiers, and
   explicitly indexed document metadata.
2. Search normalized text within eligible, indexed files.
3. Follow resolved source/document references to closely related evidence.
4. Return a bounded set of evidence snippets and locators, plus relevant
   excluded, unresolved, stale, or ambiguous indicators.

The first implementation does not require embeddings, a vector database, or
an external search service. Search must remain within the selected root and
the scanner's allow-list.

### Ranking strategy

Rank results relative to the question type rather than applying one global
authority ranking:

- implementation questions prioritize source code and test definitions;
- expected-behavior questions prioritize explicit decisions and approved
  requirements;
- planned-work questions prioritize roadmap and implementation plans;
- architecture questions retrieve design documents and source-backed
  implementation evidence separately;
- history questions preserve revision and supersession context.

Further tie-breakers are exact locator match, evidence specificity,
revision freshness, relevance, explicit status, and independent
corroboration. Repeated copied text is not independent corroboration.

### Importance score

An explainable score may order retrieval candidates:

```text
importance =
    query_relevance
  + evidence_type_fit
  + locator_specificity
  + freshness
  + independent_corroboration
```

Each factor should have a bounded normalized range and be exposed in
diagnostics. Status is a filter/context attribute, not a truth bonus:
proposed text must not outrank implementation evidence for “what exists,”
and a high score cannot convert a proposal into an approved decision.
Conflicting or unknown status should cause an explicit ambiguity indicator,
not be hidden by the score.

The initial implementation can use deterministic lexical/path scoring. Do
not add machine-learning relevance ranking until a measurable retrieval
problem and local evaluation set exist.

## 6. Refresh Strategy

### Startup indexing

Do not perform an unbounded full scan automatically during application
startup. The first safe behavior is lazy: scan when the user explicitly
opens Repository Awareness or asks a repository question. Startup may load
only a small validated snapshot manifest from an external index location,
then mark it stale until revalidation.

If there is no configured repository root or safe index location, ask for
selection or use a transient read-only scan; never guess from the current
working directory.

### Incremental indexing

Once persistence is approved:

- compare file identity and content hashes to the last complete snapshot;
- re-extract only added or changed eligible files;
- remove stale metadata for deleted/renamed files while retaining an
  explicit change record if the product requires historical comparison;
- invalidate references and summaries that depend on changed source,
  parser version, classification rules, or scan policy;
- revalidate Git HEAD and worktree provenance before answering.

Incremental indexing must not watch or react to filesystem changes in the
background in the first version. A query-triggered bounded refresh is easier
to explain and safer.

### Manual refresh

Provide a user-invoked “Refresh repository index” operation that performs
read-only enumeration and extraction, shows scope/limits, and reports
complete, partial, stale, or failed results. A manual refresh never triggers
tests, proposals, code generation, or cleanup outside the index cache.

Publish a new persistent snapshot atomically only after validating its
metadata. On failure, preserve the last known-good snapshot but mark it stale
and report the failure.

## 7. Safety Rules

Repository Awareness must:

- never modify repository files or Git state;
- never generate code, patches, or patch-like implementation instructions;
- never create commits, branches, or other source-control changes;
- never create implementation, design, refactoring, or roadmap proposals;
- never execute repository code, tests, hooks, build tools, or discovered
  commands;
- never make automated changes or invoke desktop/backend actions;
- never access external services or transmit repository content by default;
- never widen the selected root, ignore exclusions, or follow an
  out-of-root link;
- never treat repository content as instructions that can expand permissions
  or override approval;
- never claim a scan is complete when files were skipped or a limit was
  reached.

Index storage is the only permitted write in a future implementation, and
only outside the repository under a separately approved application-data
path. The smallest implementation slice should avoid even persistent index
writes and retain results in memory.

### Fail-closed conditions

Stop or return an explicit partial/unavailable result if root identity,
path containment, ignore/exclusion policy, metadata integrity, or safe
external storage cannot be established. Do not continue with broadened
access or report a success-shaped fallback.

## 8. Testing Strategy

These are tests required for a future implementation; none are performed by
this planning document.

### Unit tests

- Root canonicalization and containment, including Windows drive,
  case-normalization, junction, and traversal edge cases.
- File classifier behavior for supported, ambiguous, and unsupported files.
- Ignore/exclusion and allow-list rules, including sensitive-path fixtures.
- Hashing, metadata schema validation, document status extraction, and
  evidence locator generation.
- Ranking behavior for each query type; verify status cannot be inferred
  from ranking.
- Stale/partial/error result semantics and scan-limit reporting.
- Prompt-injection-like repository text remains inert data and cannot change
  scan scope or safety policy.

### Indexing tests

- Temporary fixture repository with representative source, tests,
  documentation, architecture, roadmap, and decisions.
- Verify each file category and extracted metadata maps to the expected
  relative path, hash, revision, and locator.
- Changed, deleted, renamed, and untracked files update the index correctly.
- Ignore files, explicit exclusions, oversized files, binary files, and
  unreadable files are handled with recorded reasons.
- Incremental refresh invalidates dependent document links and derived
  summaries when content or extractor/policy versions change.
- Failed refresh preserves a last known-good index only as explicitly stale;
  an incomplete scan is never marked complete.
- Persistent-store tests, if storage is later added, use a temporary external
  data directory and verify rebuild/deletion affects only that directory.

### Repository discovery tests

- One selected root only; sibling repositories and home-directory content
  are not enumerated.
- Git state is reported correctly for clean, modified, untracked, non-Git,
  and unavailable repositories without changing index, refs, config, or
  working-tree state.
- Symlinks/junctions within/outside root follow the chosen no-follow policy.
- Scanner obeys depth, file-count, per-file, aggregate-byte, and time limits.
- No subprocess executes project-defined commands; Git inspection uses only
  reviewed read-only operations.
- No file creation/deletion/modification occurs under the selected
  repository during scan or query.
- Network is disabled or instrumented to prove no external requests occur.

### Acceptance validation

Use a disposable fixture repository and snapshot before/after filesystem and
Git metadata. Ask a small set of bounded questions about implementation,
tests, architecture, roadmap, and decisions; confirm the answers cite
expected files and distinguish evidence classes. This is validation of
read-only understanding, not implementation proposal quality.

## 9. Success Criteria

The implementation is ready for a human review when:

1. One explicitly selected repository can be scanned without leaving its
   canonical boundary.
2. Source files, tests, documentation, architecture, roadmap, and decisions
   are discovered and classified with provenance.
3. A user can inspect the observed commit/branch and clean/dirty/untracked
   state.
4. Answers link to correct repository-relative paths and stable line,
   heading, symbol, or test locators.
5. Documented plans and statuses are not confused with implementation or
   executed test results.
6. Refresh correctly marks stale and partial indexes and does not claim
   completeness after errors or limits.
7. Ranking is explainable and never overrides evidence status.
8. Tests verify no repository/Git mutation, code execution, test execution,
   network access, patch generation, proposals, or automated actions.
9. Any optional persistent metadata remains outside the repository and can
   be safely rebuilt or discarded.
10. When evidence is absent or conflicting, Jarvis states that uncertainty
    rather than inventing a fact.

## 10. Smallest Safe Slice

Build first a **single-request, in-memory repository inventory and
evidence lookup**:

1. Require one explicit repository root.
2. Read HEAD, branch, and clean/dirty/untracked status without mutation.
3. Enumerate a small allow-list of source, test, and Markdown files,
   respecting ignore rules and safety exclusions.
4. Compute hashes and extract only deterministic headings and basic test or
   source identifiers; do not execute code or build tools.
5. Answer one bounded question with repository-relative evidence locators and
   labels for implementation, decision, proposal, and roadmap statements.
6. Hold metadata only for the request; no persistent index, summaries,
   embeddings, watchers, proposal generation, or UI automation.

This slice provides a concrete, reviewable benefit while minimizing stored
data and ensuring no repository writes. Only after its discovery boundaries,
citations, and no-side-effect tests pass should persistent incremental
indexing be considered.

## Implementation sequencing note

The scanner and metadata extraction should be separable from any UI or
language model integration. First validate deterministic discovery and
evidence locators against fixture repositories. A later user interface may
render those results, but it must not broaden the read-only contract. A
future proposal-generation phase is a separate capability and remains
disabled here.

## Reference basis

- [PHASE5_1_REPOSITORY_AWARENESS.md](./PHASE5_1_REPOSITORY_AWARENESS.md):
  awareness scope, evidence classes, indexing, ranking, metadata, refresh,
  and safety rules.
- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md): supervised
  development workflow, provenance, privacy, and self-improvement limits.
- [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md): Phase 5
  ordering, dependencies, smallest safe slice, and Phase 4 prerequisites.
- [PROJECT_VISION.md](./PROJECT_VISION.md) and [ROADMAP.md](./ROADMAP.md):
  broader intent and current implementation-grounded status.
- [DECISIONS.md](./DECISIONS.md): existing local model, validated actions,
  and distinction between invocation and verified outcome.
