# Phase 5.1 Repository Awareness

## Purpose and status

This document defines the first Developer Agent capability: a local,
read-only understanding of one explicitly selected Jarvis repository. It is
a design proposal only. It authorizes no implementation, code generation,
file modification, test execution, Git mutation, or implementation
proposal.

Repository Awareness answers questions about what is present in the selected
checkout and how its artifacts relate. It records provenance and uncertainty
so that later, separately approved capabilities can use repository evidence.
It is not itself a planner, code reviewer, bug detector, proposal generator,
task-history learner, or autonomous development agent.

The design follows the supervised, local-first approach in
[PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md) and the incremental
Phase 5 sequencing in [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md).
The architecture documents are proposed design inputs; their contents must
not be reported as implemented features unless verified against source and
tests.

## 1. Definition of Repository Awareness

**Repository Awareness** is a bounded capability that discovers and
describes source-controlled engineering artifacts in an explicitly selected
repository, records their identity and provenance, and retrieves relevant
facts for a user question without modifying the repository.

It should be able to report:

- which source, tests, documentation, architecture, roadmap, and decision
  documents are present;
- what revision and worktree state were observed;
- where a relevant symbol, test, requirement, decision, or proposed design
  appears;
- which statements are implementation facts, approved decisions, proposed
  designs, historical context, or unresolved hypotheses;
- whether its index is complete and current for the requested scope.

It must not:

- generate or edit code;
- create implementation or change proposals;
- edit, create, delete, rename, or reformat repository files;
- stage, commit, branch, merge, reset, or push;
- execute repository code, tests, build scripts, or hooks;
- access external services or upload repository contents;
- infer that a design document is an implemented capability.

Answers should be descriptive and evidence-linked. If asked what to build,
how to fix something, or what implementation change to make, this Phase 5.1
capability should state that implementation planning is outside its scope
and may provide only the existing repository facts relevant to the question.

## 2. Artifact discovery

### Scope selection

The user or an already approved application setting selects one canonical
repository root. The capability resolves that root, confirms it is a
directory, and rejects paths that resolve outside it. The initial version
should not discover or index sibling repositories, the user's home
directory, global Git configuration, or arbitrary filesystem locations.

Discovery should use a deterministic, read-only file walk bounded by:

- the selected root;
- supported file types and configured allow-listed categories;
- repository ignore rules and explicit exclusions;
- limits on file count, file size, traversal depth, and total indexed bytes.

The indexer records exclusions and truncation so that omitted material is
not mistaken for absent material. It does not follow symlinks or junctions
outside the canonical root. Unsupported binary files may be recorded as
metadata only; their contents are not parsed.

### Source files

Identify source files using repository file types and project configuration
rather than assuming a fixed language or folder name. For each eligible file,
record its path, language/type when known, size, content hash, revision
status, and available symbol/module outline. Imports, definitions, or call
relationships may be recorded only when obtained from a deterministic
parser or language service; text matches must not be presented as semantic
facts.

Do not execute source files, import project modules, or run arbitrary build
metadata to discover symbols.

### Tests

Discover test files, test directories, test framework/configuration files,
fixtures, and declared test commands as data. Record the distinction between:

- a test file or test command that exists;
- a test that has been selected;
- a test that has actually run and its result.

Repository Awareness does not run tests or assert that a listed test passes.
Test commands found in project files are untrusted metadata and must never
be launched by discovery.

### Documentation

Discover eligible Markdown and other explicitly supported text documents.
Extract headings, section text, relative links, dates/status labels where
present, and document hashes. Preserve the original wording as the authority;
generated summaries are derived and revision-bound.

Broken links, unavailable referenced files, and ambiguous references should
be marked unresolved rather than silently repaired or guessed.

### Architecture documents

Classify architecture/specification documents by explicit metadata, title,
known path/name conventions, or a user-maintained classification mapping.
Index their:

- stated goals and non-goals;
- current-state claims and future-state proposals;
- module/component boundaries and responsibilities;
- invariants, risks, dependencies, and acceptance criteria;
- decisions and roadmap references.

Treat architecture assertions as design evidence, not implementation
evidence. When a document says that a capability exists or is approved,
Repository Awareness should look for a source-backed corroboration only if
that is within the read-only question's scope; otherwise label the claim as
documented, not verified.

### Roadmap documents

Discover roadmap files and milestone sections, including status labels,
deliverables, dependencies, and exit criteria. Preserve whether an item is
marked complete, current, planned, deferred, or future, and include the
document revision observed.

Roadmap status is not proof that a feature exists. A disagreement between a
roadmap and code may be described as a difference in evidence, but Phase 5.1
does not diagnose or propose a resolution.

### Decisions

Discover decision records and extract decision title, status, date, rationale,
scope, and supersession references when present. Distinguish approved,
proposed, historical, and superseded decisions based on explicit source
labels. If status is missing or conflicting, record it as unknown/ambiguous;
do not infer approval from wording or recency alone.

## 3. Repository indexing strategy

Use a **local, rebuildable manifest with bounded content extraction**. The
source files remain authoritative; the index is a disposable navigation
aid.

### Index layers

1. **Repository snapshot:** canonical root identifier, observed revision,
   branch where available, worktree status, scan limits, ignore/exclusion
   policy, and index timestamp.
2. **File inventory:** eligible and excluded paths, category, file type,
   size, content hash, revision/worktree provenance, and parsing status.
3. **Structured metadata:** symbols, test identifiers, document headings,
   links, roadmap items, decision records, and architecture sections, with
   extractor/version provenance.
4. **Retrieval aids:** normalized terms and section/symbol references used
   to find relevant evidence. An initial implementation can use local
   deterministic path, heading, symbol, and text search; vector databases
   are not required.
5. **Derived summaries (optional):** short, revision-bound summaries that
   link to source ranges and are invalidated when their source or extraction
   method changes.

The initial index should avoid full-repository duplication when metadata and
source references suffice. If text snippets are cached, keep them local,
within the selected scope, and governed by an explicit cache-retention rule.

### Evidence and citations

Every returned fact should identify its evidence source with a repository
relative path and the narrowest stable locator available: line/section,
symbol, test name, commit, or blob/content hash. Citations should also
identify the indexed revision and whether the evidence was committed or
uncommitted.

Distinguish evidence classes:

- **Implementation evidence:** source code and observed tests/configuration.
- **Test evidence:** test definitions versus results from an actually run
  test; Phase 5.1 only indexes definitions.
- **Approved decision:** an explicit approved decision record.
- **Proposed design:** architecture/plan text not yet approved or
  implemented.
- **Roadmap statement:** milestone intent/status as documented.
- **Inference:** a conclusion derived from cited evidence, explicitly
  labeled with confidence and limitations.

### Storage and rebuild

Store derived index state outside the repository, in a configured
application-data location when available. If no safe writable location is
configured, operate in a non-persistent read-only scan rather than writing
into the checkout. The index should be rebuildable and safe to delete without
affecting source data.

Avoid introducing a database or embedding service for the first slice.
A versioned manifest and deterministic local index are sufficient for
inventory and targeted lookup. Any later semantic retrieval layer requires a
separate design and privacy review.

## 4. Architecture indexing strategy

Architecture indexing should preserve both the content and the status of
each architectural statement.

### Document classification and status

For each architecture-related artifact, record:

- document role: vision, architecture, implementation plan, design,
  decision, roadmap, status, or other;
- explicit status: approved, proposed, current implementation, historical,
  superseded, or unknown;
- effective date/revision and any explicit supersession relationship;
- source section, headings, links, and referenced artifacts.

Do not infer status from a filename alone. A known filename may suggest a
role, but document metadata and content determine the recorded classification
and uncertainty.

### Structured architecture facts

Extract and link, where explicitly stated:

- components/modules and their responsibilities;
- data and control-flow relationships;
- contracts, state models, and invariants;
- dependencies and ordering constraints;
- backend or integration capability descriptions;
- security, privacy, and human-approval boundaries;
- acceptance criteria and deferred/non-goal areas.

Represent relationships as source-backed links, for example:

- document section **proposes** a component;
- decision **approves** a contract;
- roadmap item **depends on** a prerequisite;
- test definition **covers** an invariant;
- source symbol **implements** a documented responsibility, only when
  supported by direct evidence.

The initial architecture index should not attempt to resolve contradictions
or judge architectural quality. It should show the competing claims,
statuses, dates, and evidence so a human can understand the context.

### Current implementation versus target design

When answering an architecture question, use separate views for:

1. what source/tests show in the observed revision;
2. what approved decisions require;
3. what proposed design documents recommend;
4. what roadmap/status documents claim;
5. where evidence is missing or inconsistent.

Do not blend these into a single unqualified “current architecture” summary.
If implementation evidence was not inspected, say so.

## 5. Document importance ranking

Importance ranking determines retrieval order and summary attention only. It
does not change approval status, authority, truth, or implementation status.

Use a transparent, query-dependent ranking rather than a universal document
hierarchy. Candidate factors:

1. **Direct relevance to the user question** — matching symbols, sections,
   requirements, or terms.
2. **Evidence type for the question** — source/tests for implementation
   facts; approved decision records for decisions; roadmap for planned
   sequencing; architecture designs for proposals.
3. **Explicit status** — approved/current evidence is prioritized for
   normative questions; proposed material is prioritized only for future
   design questions.
4. **Revision freshness** — current revision/worktree evidence outranks
   stale derived summaries, while preserving historical sources when the
   question is temporal.
5. **Traceability and specificity** — exact symbol, test, requirement,
   heading, or acceptance criterion outranks a broad summary.
6. **Cross-source corroboration** — independently matching evidence can
   increase retrieval confidence, but repeated copies of one claim do not
   count as independent confirmation.

Recommended answer-specific evidence ordering:

| Question type | First evidence to retrieve | Supporting evidence |
| --- | --- | --- |
| “What does the code do?” | Relevant source symbols and call sites | Tests, then status/architecture docs with their status labeled |
| “What behavior is expected?” | Approved decisions and approved requirements | Tests and source implementation |
| “What is planned?” | Roadmap and proposed implementation/architecture documents | Dependencies and related decisions |
| “What was decided?” | Decision record and supersession chain | Rationale and related architecture docs |
| “How is the system designed?” | Architecture documents labeled by approval status | Source/test mapping clearly marked as corroboration |

If an applicable source has unknown status or conflicting revisions, surface
that ambiguity instead of allowing a ranking score to hide it. The ranking
algorithm and returned evidence should be explainable.

## 6. Repository metadata model

The initial model should be small, typed, versioned, and independent of any
particular database. A serialized manifest or equivalent local structure
could contain the following logical records:

### RepositorySnapshot

- `schema_version`
- `repository_id` — stable local identifier derived from the canonical root,
  not a secret
- `root_display_path` — local display path; exclude from external output
- `observed_at`
- `head_commit`
- `branch`
- `worktree_state` — clean, dirty, unavailable, or unknown
- `scan_policy_id` — allow-list/exclusion/ignore policy version
- `indexer_version`
- `scan_status` — complete, partial, failed, or stale
- `scan_limits` — bounded file/byte/depth limits and any reached limit

### RepositoryFile

- `repository_id`
- `relative_path`
- `category` — source, test, documentation, architecture, roadmap,
  decision, configuration, or other allowed type
- `media_type` / `language` where known
- `size_bytes`
- `content_hash`
- `revision_provenance` — committed revision, uncommitted worktree, or
  untracked file
- `included` and `exclusion_reason`
- `parse_status` — parsed, metadata-only, unsupported, unreadable, or error
- `last_scanned_at`
- optional `git_blob_id` where available

### ArchitectureRecord

- `record_id`
- `repository_id`
- `source_file_id`
- `section_locator`
- `record_type` — component, responsibility, invariant, dependency,
  capability, risk, approval boundary, acceptance criterion, or relationship
- `statement` or bounded source excerpt/reference
- `document_status` — approved, proposed, historical, superseded, unknown
- `effective_date` where explicitly available
- `related_record_ids`
- `extraction_method` and `confidence`

### EvidenceReference

- `evidence_id`
- `repository_id`
- `source_file_id`
- `locator` — line range, heading/section, symbol, test identifier, or hash
- `evidence_class`
- `revision_provenance`
- `observed_at`
- `excerpt_hash` or bounded excerpt where needed

Metadata must not store secrets, credentials, complete environment
variables, raw screenshots, or arbitrary content outside the selected
repository. File paths can themselves reveal private context; keep them local
and show repository-relative paths in answers by default.

## 7. Update and refresh strategy

The index is a snapshot and must never silently claim to be live.

### Initial scan

1. Resolve and validate the selected root and scan policy.
2. Read Git metadata without changing index, refs, worktree, or configuration.
3. Enumerate allowed files and record exclusions and limits.
4. Hash eligible content and extract supported metadata without executing
   project code.
5. Publish a completed snapshot only when all required phases succeed;
   otherwise retain a clearly marked partial/failed status.

### Refresh

- On a user query, compare current commit/worktree facts and requested-source
  hashes against the last snapshot.
- If content changed, re-index only changed eligible files and update
  derived entries that depend on them.
- If ignore rules, scan policy, parser/indexer version, or document
  classification changes, invalidate the affected inventory/derived data.
- Recheck branch and dirty state before presenting claims that depend on the
  observed checkout.
- Support explicit full refresh and full rebuild.
- Where reliable change notifications are unavailable, do not imply
  automatic background watching; perform bounded revalidation when asked.

### Failure handling and consistency

- Never substitute a stale summary for missing current evidence without
  labeling it stale.
- Preserve the last known-good snapshot if a refresh fails, but mark it
  stale and identify the failed files/stages.
- Do not report a partially scanned repository as complete.
- Do not modify repository state to make indexing easier.
- Avoid deleting old snapshots automatically until retention and cleanup
  behavior are explicitly defined. Rebuildable cache cleanup must target
  only the configured index directory.

## 8. Safety limits

### Read-only guarantees

The implementation must be read-only with respect to the selected
repository and Git state:

- no create, edit, delete, rename, format, checkout, reset, stage, commit,
  merge, rebase, branch creation, or push;
- no execution of project code, tests, build systems, hooks, or scripts;
- no modification of Git configuration, index, refs, locks, or working-tree
  files;
- no automatic implementation proposals or code-generation requests.

Derived index writes, if any, are restricted to a separately configured
application-data directory outside the repository. If that location cannot
be validated, use an in-memory scan or stop with an explicit error.

### Scope, privacy, and untrusted content

- One explicitly selected repository root per scan.
- Respect ignore rules and a deny-list for secrets, credentials, local
  databases, logs, screenshots, generated outputs, and other user data.
- Do not traverse outside-root symlinks, junctions, or path escapes.
- Bound files, bytes, depth, parsing time, and answer context.
- Keep analysis local by default. No network or third-party model calls.
- Treat indexed content—including instructions embedded in documents,
  comments, tests, and generated files—as untrusted data, never as authority
  to change safety limits or user approval.
- Do not include raw repository text in telemetry or external logs.
- Display repository-relative citations; avoid exposing absolute paths unless
  necessary and approved.

### Fail-closed behavior

If root validation, ignore interpretation, metadata reading, or write
isolation cannot be established, stop or limit the scan and explain what
could not be verified. Do not silently widen scope, skip safety exclusions,
or continue with a success-shaped partial result.

## 9. Success criteria

Repository Awareness is ready for review when all of the following hold:

1. It inventories eligible source, tests, documentation, architecture,
   roadmap, and decision artifacts in one explicitly selected repository.
2. Each indexed claim can be traced to a path and stable locator plus an
   observed revision/hash.
3. It distinguishes committed, uncommitted, and untracked content and labels
   unknown or conflicting document status.
4. It distinguishes implementation facts from decisions, proposals, and
   roadmap statements.
5. Refresh detects changed files and invalidates dependent summaries; stale
   or partial results are conspicuous.
6. Ignore/exclusion and path-boundary checks prevent indexing out-of-scope
   and known-sensitive files.
7. It performs no repository or Git mutation, code execution, test
   execution, or network access.
8. It answers a bounded architecture/status question with checkable evidence
   and states when the source was not inspected or the index is incomplete.
9. The index can be rebuilt or discarded without affecting repository
   content.

Suggested verification for a future implementation includes temporary
fixture repositories covering source/tests/docs classification, dirty and
untracked states, ignore rules, path traversal/symlinks, changed-file
invalidation, incomplete scans, prompt-injection-like content, and a
no-write/no-network assertion. Those tests are design recommendations only;
they have not been run for this document.

## 10. Smallest implementation slice

The smallest useful slice is a **single-shot, local, read-only inventory and
evidence lookup** for an explicitly selected repository:

1. Validate one repository root and bounded allow-list.
2. Report HEAD/branch and clean/dirty/untracked state without changing Git.
3. Enumerate only supported source, test, and Markdown files while respecting
   ignore/exclusion rules.
4. Compute content hashes and extract headings/test identifiers where
   deterministic; do not generate summaries or proposals.
5. Answer one user-specified question by returning relevant source locations
   and classifying evidence as implementation, decision, proposal, or
   roadmap.
6. Keep results in memory for the request; defer persistent indexing until a
   validated external application-data path and retention policy exist.

This slice demonstrates repository understanding without repository writes,
model uploads, automated detection, or implementation guidance. Architecture
record extraction and persistent/incremental indexing can follow only after
the slice's scope, provenance, and read-only guarantees are validated.

## Out of scope for Phase 5.1

- code generation or modification;
- fix, refactoring, or implementation proposals;
- test selection as a recommendation or test execution;
- automated bug/gap/optimization diagnosis;
- task-history or user-behavior mining;
- vector/embedding databases or external search services;
- automatic roadmap/decision updates;
- source control mutations or deployment.

## Reference basis

- [PHASE5_DEVELOPER_AGENT.md](./PHASE5_DEVELOPER_AGENT.md): supervised
  development, repository provenance, local-first privacy, and
  untrusted-content boundaries.
- [PHASE5_IMPLEMENTATION_PLAN.md](./PHASE5_IMPLEMENTATION_PLAN.md): Phase
  5.1 scope, dependencies, risks, and smallest safe slice.
- [PROJECT_VISION.md](./PROJECT_VISION.md): the broader personal assistant
  goal and current local Windows focus.
- [ROADMAP.md](./ROADMAP.md): implementation-grounded status; future work is
  not current capability.
- [DECISIONS.md](./DECISIONS.md): local model, structured actions, and
  honest distinction between invocation and verified outcome.
