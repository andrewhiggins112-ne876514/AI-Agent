# Architecture Alignment Review

## Purpose and scope

This review compares the AI-Agent project as currently documented and
implemented with:

1. *JARVIS Home Core — Specification v1.0* (22 pages; October 2026 draft);
2. the project's background-automation research in
   [BACKGROUND_AUTOMATION_OPTIONS.md](./BACKGROUND_AUTOMATION_OPTIONS.md);
3. the existing Phase 3 task execution and target-awareness design.

The JARVIS specification is treated as a reference blueprint, not as an
approved requirement to implement every listed feature. Its voice-first,
always-on, multi-user home-system scope is substantially broader than the
current personal Windows desktop prototype. Recommendations below prioritize
small, verifiable increments and preserve the existing sequential execution
model.

## Executive summary

The project has a useful foundation for **validated, sequential desktop
actions with task states, verification results, fail-stop behavior, and
foreground-target mismatch reporting**. Its local Ollama request path and
small direct Windows tools align with the specification's local-first
direction and the Phase 3 execution model.

It is not yet a general automation platform. The current runtime has one
foreground-oriented desktop tool path, no capability-based backend selection,
no durable audit trail, no memory system, no policy/confirmation engine, and
no application, browser, workspace, or Home Assistant adapters. The mismatch
between the planned "intelligent operating-system layer" and the current
foreground keyboard tool should be resolved architecturally: semantic APIs
and accessible controls should handle background-capable operations; global
keyboard/mouse input should remain an explicit foreground-only fallback.

Recommended direction:

- Finish Phase 3 around reliable task semantics, backend-neutral action
  results, and honest verification; do not add automatic window activation
  as a shortcut to background automation.
- Make the next foundation increment establish configuration, authorization,
  a capability/adapter boundary, and durable observability.
- Build memory incrementally and user-controllably, then add one bounded
  semantic automation integration at a time.
- Defer voice satellites, proactive autonomy, multi-agent orchestration,
  graph/vector memory, and broad home-device control until safety,
  persistence, and integration contracts are in place.

## 1. Architecture gap analysis

### A. Existing capabilities already aligned

| Area | Current state | Alignment |
| --- | --- | --- |
| Local-first model use | The GUI calls the local Ollama API and uses Llama 3.2. | Aligns with the JARVIS local-first principle and keeps the current path usable without cloud providers. |
| Structured plans and validation | Model output is normalized to action lists and preflight validates the entire plan before execution. | Aligns with structured tool contracts and reliable argument validation. |
| Sequential execution | The task runner executes in order, emits lifecycle events, and stops on required failures. | A sound small-scale base for the specification's plan/execute workflow; no premature general workflow engine. |
| Verification semantics | `VERIFIED`, `UNVERIFIED`, and `FAILED` are kept distinct; `TYPE_TEXT` remains unverified without read-back. | Strong alignment with observable outcomes and honest reporting. |
| Foreground awareness | Read-only snapshots capture foreground title, handle, and process ID; Step 7B assesses known targets and blocks confident mismatch. | A useful target-safety foundation, but not background operation or a focus-control backend. |
| Progress reporting | Task and step events are polled by the Tk UI; target assessments and blocked-dispatch reasons are reported. | Partial alignment with visible execution progress. The current event queue is transient, not a searchable history or audit log. |
| Windows desktop tools | Notepad launch, screenshot, pointer movement, visible-window listing, and active-window typing exist. | Covers a narrow subset of PC-control capability. |
| Local Windows foundation | Python, Tkinter, pywin32, pyautogui, and Pillow are in use. | Supports an incremental Windows-focused implementation; cross-platform abstraction is not yet justified. |

### B. Missing capabilities worth pursuing

| Area | Gap and value | Recommended treatment |
| --- | --- | --- |
| Multiple execution backends | One tool registry currently dispatches directly to functions. The runner has no capability discovery or explicit selection between semantic, API, foreground, and isolated backends. | Add a narrow backend/adapter boundary after Phase 3 semantics stabilize. Keep the current path as a named foreground-input backend. |
| Foreground and focus policy | The active-input typing tool can only act on the desktop's current input recipient. A target mismatch blocks unsafe typing, but there is no explicit policy for whether the agent may request focus changes. | Preserve focus observation in Phase 3. Introduce any activation only as an explicit, authorized foreground-required mode, never as hidden behavior. |
| Background automation | No current mechanism reliably directs arbitrary input to another app while the user remains active elsewhere. | Prefer app APIs or supported UI Automation patterns. If only global input exists, report the foreground requirement or require an isolated environment. |
| UI Automation | No semantic UI tree discovery, element selection, control patterns, or control-value read-back. | Prototype a bounded read-only UIA inspection first, then one operation/read-back pattern for a known standard control. |
| Application APIs | No per-application semantic adapters (for example, document operations through supported app interfaces). | Add only for concrete workflows where the app has a documented, supported API and deterministic result semantics. |
| Browser automation | No browser-specific backend. Current mouse/keyboard tools would be fragile for navigation and cannot independently establish page state. | Add a separate browser adapter, preferably a supported automation interface such as Playwright, with its own target/context and verification. |
| Workspace automation | No scoped project/workspace model, safe file operations, coding-agent handoff, or isolated implementation workspace. | Add explicit workspace roots and scoped file capabilities before shell or coding-agent execution. Keep shell access confirmed and sandboxed. |
| Home Assistant integration | No HA connection, entity discovery, state reads, service calls, or event subscription. | Defer until tool authorization, audit, configuration, and external-adapter contracts exist. Then use HA as the home state source of truth through its supported MCP/API interface. |
| Memory architecture | `memory/` is a vision-level placeholder; no working, episodic, semantic, or graph memory is implemented. | Start with local SQLite episodic history and user-reviewed preferences, with view/edit/export/delete controls. Defer vector and graph stores until retrieval needs are demonstrated. |
| Observability and auditability | Progress events are in-memory and short-lived. There is no durable tool-call ledger, confirmation record, configuration-change history, or searchable task history. | High priority: introduce structured, append-only local records with correlation IDs, durations, backend, target, verification, policy/confirmation decision, and side effects. Keep model prompts out of logs by default. |
| Safety and permissions | Preflight validates schema, but the project has no risk classification, confirmation policy, per-tool permissions, privacy mode, or hard safety rules. | Add an explicit policy gate before adding filesystem, shell, messaging, or physical-device tools. New high-impact tools should default to confirmation. |
| Configuration | Paths and model/runtime choices are currently hard-coded or fixed in code. | Add validated configuration before accumulating adapters and user settings. Keep secrets out of plain configuration. |
| Vision/perception | Screenshot capture exists, but OCR, screen understanding, application-state perception, camera pipelines, and telemetry are absent. | Add narrowly scoped screen OCR/read-only inspection only after privacy permissions and data-retention behavior are defined. |
| Multi-agent orchestration | No sub-agent lifecycle, delegation, resource limits, shared policy enforcement, or supervision exists. | Defer until a single task runner, audit trail, and permission boundary can supervise all delegated tool calls. |

### C. Capabilities that should be deferred

These items appear in the JARVIS reference but are not prerequisites for
reliable desktop tasks and would multiply operational and safety complexity:

- Always-on wake-word, streaming speech recognition/synthesis, barge-in,
  multi-room satellites, and speaker identity.
- Proactive monitoring, routine learning, occupancy inference, camera/person
  recognition, and autonomous actions.
- Multi-agent "staff," autonomous long-horizon plans, and coding-agent
  handoff before sub-agent policy, isolation, resource limits, audit, and
  global stop controls exist.
- Full household knowledge graph, vector database, automated fact extraction,
  overnight memory maintenance, and automatic routine proposals.
- Mobile companions, remote access, webhooks, authenticated external APIs,
  marketplace/plugin ecosystem, and cross-platform host support.
- Direct Matter/Zigbee/Z-Wave control outside a Home Assistant-mediated
  boundary.
- Game automation. Use only documented, permitted application interfaces or
  accessibility features; do not inject into protected processes or bypass
  anti-cheat.
- Automatic focus stealing as a supposed background-automation solution.
  It is an interruptive foreground mode and remains subject to Windows policy.

### D. Architectural changes recommended

1. **Retain the Phase 3 task runner.** Keep sequential execution, whole-plan
   preflight, fail-stop behavior, current task states, and the independent
   verification registry. Avoid replacing these with a broad DAG or agent
   framework.
2. **Separate intent from execution mechanism.** Model actions as validated
   operations against a target (for example, set a document field), rather
   than assuming every operation is a sequence of key presses.
3. **Introduce backend capability selection beneath the task runner.** The
   runner asks which backend supports the operation and target; a backend
   reports its identity, focus requirements, capability limits, timing, and
   structured result.
4. **Keep evidence dimensions separate.** Target assessment, foreground
   observation, backend dispatch result, policy decision, and action
   verification should remain distinct fields. A backend's successful call
   must not be presented as proof of an application postcondition.
5. **Make policy and audit cross-cutting.** All adapters, including future
   HA, browser, and sub-agent tools, should pass through one validated
   authorization/confirmation gate and a durable event/audit sink.
6. **Use an integration boundary per domain.** Desktop/UIA, browser, workspace
   filesystem/shell, and Home Assistant have different targets, permission
   models, and evidence. Do not force them into one generic `pyautogui` tool
   surface.
7. **Build memory as a governed subsystem.** Separate transient task context,
   episodic records, user-approved semantic facts, and any later vector/graph
   indices. Give the user inspection, correction, export, retention, and
   deletion controls from the first persistent-memory release.

## 2. Recommended backend architecture

### Logical execution flow

```text
User / UI / future voice interface
                ↓
Request and plan generation
                ↓
Plan normalization + schema preflight
                ↓
Policy and confirmation gate
                ↓
Sequential task runner
  ├─ target and capability resolution
  ├─ backend selection (explicit and observable)
  ├─ dispatch + timeout/error handling
  ├─ action-specific verification
  └─ events → UI + durable audit
                ↓
Automation backend ports
  ├─ Foreground Backend
  ├─ Target-Aware Backend
  ├─ Workspace Backend
  ├─ UI Automation Backend
  ├─ Application API Backend
  ├─ Browser Backend
  └─ Home Assistant Backend
```

The names below are **logical capability families**, not a requirement to
create seven separate services or processes. The first implementation can
remain a small Python package with injected adapters.

### Backend responsibilities

| Backend | Responsibility and contract | Interaction mode | Initial status / guardrail |
| --- | --- | --- | --- |
| **Foreground Backend** | Existing global keyboard/mouse and desktop operations; returns dispatch result and observable metadata. | Requires the relevant target to be foreground; may disrupt user interaction. | Existing pyautogui/Win32 tools. Label as foreground-required. Require current target precondition; never imply that it can operate concurrently with user input. |
| **Target-Aware Backend** | Resolve and retain task-scoped target identity, compare observation with intended target, describe support and mismatch. This is primarily a policy/capability layer, not an input channel. | Does not itself change focus or deliver input. | Existing Step 7B records and gates. Extend only with tested identity provenance and clearer unsupported/unknown distinctions. |
| **Workspace Backend** | Perform scoped project/file operations and, later, isolated shell or coding workflows against an explicit workspace root. | Usually independent of desktop focus; shell/coding execution may need sandbox or confirmation. | Not implemented. Start with read-only list/search in allow-listed roots; add writes only with policy, audit, and confirmation. |
| **UI Automation Backend** | Discover accessible UI elements and use supported control patterns for semantic read/write/invoke and read-back. | Often background-capable, but provider and operation dependent. | Not implemented. Start with read-only inspection and one simple standard control. Report unsupported controls rather than falling back silently. |
| **Application API Backend** | Use a vendor-supported API/object model for application-level operations, state queries, and deterministic results. | Often background-capable and independent of foreground focus. | Not implemented. Add per-application adapters only for specific, documented workflows; scope authorization to the target application/account/document. |
| **Browser Backend** | Operate on an explicitly selected browser/page/context using a browser automation API and DOM/accessibility state. | Can usually operate without the browser being foreground; behavior depends on browser context and application. | Not implemented. Keep browser context and authentication separate from desktop input. Treat page actions as external side effects with explicit result evidence. |
| **Home Assistant Backend** | Discover exposed entities, read state, invoke services/scenes, and later consume events using the supported HA interface/MCP integration. | Independent of PC window focus; operates on physical devices and home state. | Not implemented. Respect HA exposure, use per-entity permissions, confirm security/physical actions, and make HA the state source of truth for integrated devices. |

### Backend selection and result contract

Before dispatch, selection should use:

- operation name and validated arguments;
- explicit target type and target identity/provenance;
- backend-advertised operation support;
- whether the operation requires foreground focus;
- whether it can read back the desired postcondition;
- user permissions, risk tier, and confirmation result;
- current privacy/configuration mode.

The selection result should be one of:

- **supported** — a backend can perform the operation under current policy;
- **requires foreground** — only the visible-input path is available;
- **requires confirmation** — policy requires an explicit user decision;
- **unsupported** — no compatible backend is available;
- **blocked** — a safety or target precondition failed.

Do not silently fall through from UIA/API/browser/workspace execution to
global input. If a foreground-required backend is selected while the user is
active elsewhere, stop and explain the limitation or request an explicit
foreground-interaction decision. An eventual isolated desktop or VM is a
separate deployment backend, not a workaround hidden inside the foreground
adapter.

Tool-call and result records should converge toward the specification's
correlated schema: call ID, validated arguments, status, error code/message,
duration, side effects, confirmation requirement/result, backend, target,
and verification evidence. Keep sensitive prompts and secrets out of normal
audit records; allow narrowly scoped debug capture only with explicit policy.

### Memory, observability, and policy relationships

- Task events are a runtime progress stream; the audit record is a durable
  history. They may share an event contract, but the UI queue alone is not an
  audit store.
- Memory and audit should be separate. The audit ledger records what was
  requested, authorized, invoked, and observed; memory stores user-approved
  facts and useful summaries. Do not automatically feed all audit content
  back into model context.
- Persist a minimal episodic record first (task, timestamps, tool call
  summaries, result, verification, and privacy flags). Add fact extraction,
  vector search, and knowledge graphs only when there are demonstrated
  retrieval needs and data lifecycle controls.
- The policy engine should authorize both direct backend calls and future
  delegated/sub-agent calls. A sub-agent must not gain capabilities beyond
  the supervisor's approved scope.

## 3. Recommended roadmap changes

### What should remain in Phase 3

Keep Phase 3 focused on dependable execution semantics and finish it with an
acceptance checklist:

- whole-plan validation before side effects;
- legal task/step transitions, ordered fail-stop execution, and skipped
  remaining steps;
- independent action verification outcomes;
- target association, foreground assessment, mismatch gating, and clear GUI
  reporting;
- typed, backend-neutral step/event result fields, without introducing a
  generalized backend registry prematurely;
- tests proving that mismatch blocks dispatch, unknown observations preserve
  approved behavior, and `TYPE_TEXT` remains `UNVERIFIED`;
- controlled manual validation of Notepad foreground match and mismatch.

Do not put automatic activation, background typing, new UIA/API backends,
multi-agent orchestration, or persistent memory into this phase. Explicitly
record that current `TYPE_TEXT` requires the active input target and does not
provide background automation.

### What should move into Phase 4

Broaden the existing Phase 4 "Persistent memory" into a modest **foundation
and memory** phase. The JARVIS specification requires configuration,
governance, observability, and user control that should exist before the
project adds high-impact integrations.

Recommended Phase 4 deliverables, in this order:

1. **Configuration and core contracts**
   - Validated configuration for model, runtime paths, privacy mode, enabled
     adapters, and confirmation policy.
   - A versioned structured tool call/result contract with correlation ID,
     timeout, status/error, duration, side effects, target/backend metadata,
     and confirmation fields.
   - A minimal adapter/capability interface that wraps the existing
     foreground backend without changing its semantics.
2. **Policy and audit foundation**
   - Per-tool risk/permission policy; new tools default to confirmation or
     denial until explicitly enabled.
   - Durable local append-only task/tool-call history, searchable from the UI.
   - Record authorization, confirmation, backend, target, result, and
     verification separately. Avoid storing full prompts by default.
   - Define privacy mode, retention, export, and deletion behavior before
     adding screen/camera or cloud data.
3. **User-controlled basic memory**
   - SQLite episodic task/conversation summaries and explicitly approved
     preferences.
   - Memory viewer/editor plus export and delete controls.
   - Keep working context separate from durable facts. No automatic
     high-sensitivity fact capture.
4. **First bounded semantic backend pilot**
   - Add either one documented application API adapter or a small UIA
     read-only/standard-control adapter, chosen from an actual target workflow.
   - Demonstrate background operation only for the operations the adapter
     explicitly supports, and include read-back and failure tests.
   - Preserve the foreground backend as a separate user-visible mode.

This is a deliberate adjustment to the current roadmap: configuration is
currently Phase 5 and UIA/application expansion is in Phase 7; foundational
configuration, policy/audit, and one bounded semantic pilot should precede
broader memory or tool expansion. Do not attempt a complete JARVIS stack in
one phase.

### Proposed subsequent phases

| Proposed phase | Focus |
| --- | --- |
| **Phase 5 — Practical domain adapters** | Expand UIA/application APIs for selected desktop workflows; add scoped workspace/file operations; then browser automation as its own target/context backend. Revisit screenshot/OCR only with privacy policy and deterministic evaluation. |
| **Phase 6 — Home Assistant integration** | Integrate through HA's supported MCP/API interface; read exposed entity state first, then low-risk service operations, then confirmation-gated scenes/physical actions. Add event subscriptions and proactive suggestions later, not autonomous control by default. |
| **Phase 7 — Memory depth and perception** | Add semantic retrieval/vector or graph stores only when the basic memory system demonstrates need; add screen OCR/vision/telemetry under explicit permissions, retention, and verification rules. |
| **Phase 8 — Hybrid models and optional interfaces** | Add cloud model adapters only as opt-in providers with redaction and outbound-data policy; add voice/UI/mobile interfaces as separate clients over stable APIs. |
| **Phase 9 — Supervised orchestration and proactive functions** | Consider sub-agents, scheduled routines, anomaly detection, and home monitoring after policy, audit, resource limits, isolation, user visibility, and global stop controls are proven. |
| **Ongoing hardening** | Security review, backups/recovery, reliability/latency measurement, accessibility, configuration migrations, and regression/manual acceptance checks across all phases. |

The numbering is a proposal, not a required renumbering. The important change
is dependency order: policy, audit, configuration, and adapter contracts
precede integrations that can modify files, accounts, or physical devices.

### What should be deferred

Defer the JARVIS specification's always-on voice pipeline, multi-room
satellites, mobile/remote presence, proactive home monitoring, multi-agent
staff, full graph/vector memory, broad plugin/MCP hosting, multi-user
biometrics, direct device protocols, and physical presence. These depend on
stable interfaces, security review, durable audit, privacy controls, and
operational deployment foundations that do not yet exist.

## 4. Proposed document updates

These are recommendations only; no existing document was changed for this
review.

### PROJECT_VISION.md

- Reframe the vision as a **local-first, user-controlled assistant with
  capability-specific execution**, rather than a single universal Windows
  controller.
- Add the distinction between semantic/background APIs and
  foreground-required global input. State that the latter may disrupt user
  interaction and should be explicit.
- Add architecture principles: validated tool contracts, policy/confirmation,
  observable execution, privacy-controlled memory, and honest verification.
- Define near-term boundaries: Windows desktop first; one supported backend
  at a time; no claim of arbitrary background control or full autonomy.
- Add Home Assistant and browser integration as future adapters, not current
  capabilities. Identify multi-agent and voice-first scope as long-term.
- Replace or supplement the current flow diagram with the proposed
  planner → policy → task runner → capability/backend → verification/audit
  flow.

### ROADMAP.md

- Mark Phase 3's delivered task execution and target-awareness scope
  accurately; distinguish manual validation that is still outstanding.
- Move core configuration and structured adapter/result contracts forward
  from the current Phase 5, because they are prerequisites to safe growth.
- Expand Phase 4 from a directory/simple memory store into a foundation
  milestone: configuration, basic policy/confirmation, local audit, and
  user-controlled episodic/preferences memory.
- Add an incremental backend pilot before broad Phase 7 tool expansion:
  read-only UIA discovery or one app API, then an operation with read-back.
- Separate workspace operations, browser automation, and Home Assistant
  integration into bounded milestones with independent target, policy, and
  verification contracts.
- Make explicit acceptance criteria for no silent foreground fallback,
  target mismatch, permission enforcement, audit completeness, and
  `TYPE_TEXT` remaining unverified absent deterministic read-back.
- Defer voice satellites, mobile, proactive autonomy, and multi-agent work
  until stable interfaces, policy, and audit have been demonstrated.

### DECISIONS.md

Add dated, status-labelled decisions (approved versus proposed) for:

1. **Execution backend boundary:** actions express semantic intent and target;
   adapters expose explicit capabilities and interaction requirements.
2. **Foreground automation policy:** current pyautogui operations are
   foreground-required; activation is a distinct, explicit operation; no
   hidden focus stealing or silent backend fallback.
3. **Verification separation:** target match and backend dispatch are not
   action verification; `TYPE_TEXT` stays `UNVERIFIED` without exact
   deterministic read-back.
4. **Tool contracts and audit:** correlated structured calls/results; durable
   audit separated from user memory; minimum necessary data retained.
5. **Memory lifecycle:** user-visible review, edit, export, retention, and
   deletion; sensitive facts are not silently auto-committed.
6. **Integration order:** UIA/application APIs and browser/HA adapters are
   independently scoped; Home Assistant is the preferred home-device hub if
   that integration is approved.
7. **Multi-agent deferral:** sub-agents inherit supervisor policy, have
   resource bounds, visible status, audit records, and cancellation before
   orchestration is enabled.

Avoid recording speculative choices of database, message broker, UI
framework, or agent library as settled decisions. Evaluate those choices
against a small implementation need rather than copying the entire JARVIS
reference stack.

## Suggested success criteria for alignment

Before adding broad integrations, demonstrate that:

- an invalid or unauthorized action produces no side effect;
- the selected backend and its focus/capability requirements are visible;
- a foreground-only action never silently steals focus or runs against a
  different foreground target;
- task events and durable audit records can explain the request, policy,
  backend, target, dispatch, side effects, and verification outcome;
- the user can inspect, correct, export, and delete persisted memory;
- a background-capable API/UIA operation works without foreground focus and
  has deterministic state read-back, or reports unsupported/unverified
  clearly;
- Home Assistant operations are restricted to exposed entities and apply
  confirmation rules appropriate to physical risk;
- all future sub-agent tool calls pass through the same authorization,
  logging, and resource-control boundaries as primary-agent calls.

## Reference basis

- *JARVIS Home Core — Specification v1.0*, user-provided PDF:
  - Sections 1–2: goals, principles, modular layers, and communication.
  - Sections 3–4: cognition, memory, perception, action, feature priorities,
    PC control, browser, and Home Assistant.
  - Sections 6–9: memory data/lifecycle, tool/result schemas, configuration,
    safety, privacy, and audit.
  - Sections 10–13: Home Assistant, multi-agent supervision, interfaces, and
    roadmap.
  - Sections 14–15: explicit boundaries and acceptance metrics.
- [PROJECT_VISION.md](./PROJECT_VISION.md), [ROADMAP.md](./ROADMAP.md), and
  [DECISIONS.md](./DECISIONS.md): current scope, planned milestones, and
  implemented architectural choices.
- [PHASE3_STEP7B_TARGET_AWARENESS.md](./PHASE3_STEP7B_TARGET_AWARENESS.md):
  target identity, focus mismatch, verification separation, and incremental
  implementation plan.
- [BACKGROUND_AUTOMATION_OPTIONS.md](./BACKGROUND_AUTOMATION_OPTIONS.md):
  backend comparison and Windows-specific constraints for activation,
  Win32 messaging, UI Automation, application APIs, and hybrid execution.
