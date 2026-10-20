# Phase 4 Execution Backends

## Purpose and status

This document proposes a future execution architecture for Jarvis / AI-Agent.
It is an architecture definition, not an implementation change or approval
to add the listed backends. The JARVIS Home Core specification is treated as a
reference, with the current Windows project and its Phase 3 execution
semantics as the starting point.

The design preserves ordered task execution, whole-plan validation,
fail-stop behavior, target assessment, and a separate verification result.
It introduces a route-selection boundary so different operations can use the
safest supported mechanism rather than defaulting to global keyboard and
mouse automation.

## 1. Execution philosophy

Jarvis should choose the **safest reliable supported execution method for
each operation and target**. Keyboard and mouse simulation is not the
universal default.

Preferred order, subject to actual support and authorization:

1. Use a documented application API or domain protocol when it expresses
   the requested operation and provides useful state read-back.
2. Use browser automation for web content and browser-owned state.
3. Use UI Automation (UIA) or another accessibility interface for supported
   semantic controls.
4. Use scoped workspace operations for files, project content, and
   explicitly sandboxed commands.
5. Use foreground keyboard/mouse automation only when other appropriate
   backends are unavailable and visible interaction is permitted.
6. If an operation cannot be safely or reliably served, report it as
   unsupported, blocked, or requiring user action. Do not silently fall back
   to an unrelated input channel.

These backends have different contracts. A foreground snapshot is evidence
about focus, not an execution channel. A target match is a precondition, not
proof of the requested effect. A successful API call or UIA pattern call is
not automatically `VERIFIED`; verification must check the action's intended
postcondition. `TYPE_TEXT` remains `UNVERIFIED` unless exact resulting text
can be read back from the intended control.

The following properties must remain separately observable:

- requested operation and target;
- selected backend and its interaction requirements;
- target/focus assessment;
- authorization and confirmation decision;
- dispatch result and side effects;
- verification status and evidence.

The current system does not yet have this router or these backends. It has a
sequential runner, target assessment, and a foreground-oriented
`pyautogui`/Win32 tool path. The proposals below are future architecture, not
claims about current capability.

## 2. Backend definitions

### 2.1 Foreground Automation Backend

**Description:** Uses global keyboard, pointer, and visible-desktop
operations, including the existing `pyautogui` path. It acts on the current
interactive desktop and does not direct arbitrary input to a background
window.

**Typical use cases**

- Interact with an application that exposes no usable API or accessibility
  controls.
- Perform a visible, short interaction that is acceptable to the user.
- Capture the desktop or move the pointer when those actions are explicitly
  requested.

**Strengths**

- Broad compatibility with applications that accept ordinary visible user
  input.
- Reuses the current tools and has a relatively low initial integration cost.
- Useful as a last resort for non-API interfaces.

**Limitations**

- Requires the intended target to be foreground and the intended control to
  receive input.
- Does not permit uninterrupted use of another application on the same
  interactive desktop.
- Coordinates and timing are sensitive to layout, scale, latency, and UI
  changes.
- Window foreground alone does not prove child-control focus.

**Verification opportunities**

- Observe foreground identity and pointer position.
- Capture before/after screenshots where permitted.
- Read back through a separate semantic backend if available.
- Without deterministic read-back, report dispatch separately and leave
  typing `UNVERIFIED`.

**Safety considerations**

- Must be labelled foreground-required.
- Check the task target immediately before dispatch; block known mismatches.
- Any activation/focus change must be a separate explicit operation and
  policy decision.
- Warn or obtain authorization when the action will take over the user's
  input surface. Never claim that this backend can operate concurrently with
  the user's input.

### 2.2 Focus-Aware Backend

**Description:** A guarded foreground-input path that combines target
identity and fresh foreground observation with ordinary visible input. It
does not itself activate a window. It may proceed only when the configured
policy's focus precondition is satisfied; otherwise it blocks or asks the
user to focus the target.

This is a logical backend/policy combination over foreground input, not a
new Windows mechanism for sending background keystrokes.

**Typical use cases**

- Continue a Notepad task after the user has manually focused the associated
  Notepad window.
- Safely dispatch a short foreground-only action after confirming the target
  is active.

**Strengths**

- Extends the current Step 7B target model and mismatch reporting.
- Reduces accidental input into a different foreground application.
- Can distinguish known mismatch, confirmed target, and unavailable
  observation before dispatch.

**Limitations**

- Still requires foreground focus and therefore interrupts or waits on the
  user.
- Observation and input are separate, leaving a race if focus changes between
  them.
- A top-level target match cannot prove the intended child control has focus.
- Unknown identity cannot safely be promoted to a match.

**Verification opportunities**

- Record expected identity, observed foreground, confidence, and whether
  dispatch was allowed.
- Reobserve focus immediately before dispatch, if the operation contract
  requires it.
- Verify postconditions independently; focus confirmation alone never
  verifies typing or application state.

**Safety considerations**

- Do not activate, restore, or focus windows implicitly.
- A confident mismatch blocks dispatch. Unknown/unavailable observations
  follow an explicit policy and must not be reported as a match.
- Keep this distinct from a future focus-changing backend so the router does
  not disguise user disruption as "focus awareness."

### 2.3 Workspace Backend

**Description:** Performs operations against explicit files, folders, and
project roots rather than manipulating their visible applications. It may
later include shell or coding tools only within a configured workspace and
sandbox.

**Typical use cases**

- List, search, read, or create project files within approved roots.
- Apply a code or document transformation to a specified file.
- Run bounded project checks in an isolated working directory.

**Strengths**

- Independent of foreground window and monitor layout.
- Usually deterministic and easy to test with temporary workspaces.
- Can provide exact file diffs, hashes, paths, and command exit codes.

**Limitations**

- Does not automatically operate on an application's in-memory state or
  unsaved document.
- Shell commands can have effects outside the workspace unless isolated and
  constrained.
- File operations may not capture user intent if a path or workspace is
  ambiguous.

**Verification opportunities**

- Check path scope, file existence, content, hashes, diffs, and command exit
  status.
- Run narrowly scoped postcondition checks and report exact side effects.
- Distinguish a successful write/process exit from semantic correctness.

**Safety considerations**

- Require explicit allow-listed roots and canonical path checks, including
  junction/symlink handling.
- Start with read-only list/search; gate writes and destructive operations.
- Require confirmation and sandboxing for shell or commands with external
  effects. Never inherit arbitrary model-generated shell without policy.
- Record files changed, command, duration, exit status, and authorization.

### 2.4 UI Automation Backend

**Description:** Uses Windows UI Automation clients to inspect UI elements
and invoke supported semantic control patterns, such as a button invocation,
selection, or accessible value operation. A narrowly scoped MSAA
compatibility path may be considered for legacy apps, but UIA is preferred.

**Typical use cases**

- Read an accessible control value.
- Invoke a standard button or menu item without global coordinates.
- Select an item or set a control value when the provider supports the
  relevant pattern.
- Inspect a UI tree to determine whether a target has exposed controls.

**Strengths**

- Targets accessible elements and declared control semantics rather than
  screen coordinates.
- Can often operate without moving the foreground focus.
- May support deterministic read-back and stronger verification.
- Can make UI state and selected-element evidence more explainable.

**Limitations**

- Capability depends on UIA providers and controls; custom-drawn interfaces
  may expose little or nothing.
- Supported patterns vary by element and may change dynamically.
- Stale elements, asynchronous updates, provider bugs, and integrity-level
  boundaries require explicit handling.
- Not every UIA operation is truly background-capable or equivalent to user
  input.

**Verification opportunities**

- Read the same target element's value/state after an operation.
- Check selected/invoked state or wait for an expected accessible element.
- Return unsupported/unavailable when required patterns or providers are
  absent; do not infer success from a call returning.

**Safety considerations**

- Scope discovery to an identified target and only request necessary
  properties; accessible text may contain sensitive content.
- Bound searches and calls with timeouts.
- Treat element identity as transient; re-resolve before consequential
  operations.
- Respect Windows UIAccess/integrity restrictions; do not request privileged
  access as a generic workaround.

### 2.5 Application API Backend

**Description:** Calls a documented application-specific object model,
command interface, local service, or vendor-supported API to perform a
semantic operation.

**Typical use cases**

- Create or edit an Office document through its object model.
- Query or update a supported application's structured data.
- Launch a documented operation or interact with an app's supported
  automation interface.

**Strengths**

- Highest semantic precision when the operation is directly supported.
- Often independent of window focus and robust to visual layout changes.
- Can expose direct state read-back, clear errors, and idempotent operations.

**Limitations**

- Application-specific implementation and support/version matrix.
- Some APIs require a running app, session, license, or authentication.
- Does not cover arbitrary visual interaction, and API access may differ from
  a user's visible unsaved state.

**Verification opportunities**

- Query the resulting object/state and compare it to the requested
  postcondition.
- Use transaction IDs, resource identifiers, or version metadata where
  available.
- Treat API success as dispatch evidence until state read-back confirms the
  intended outcome.

**Safety considerations**

- Scope credentials and permissions to the smallest app/account/resource.
- Validate arguments and apply the same policy/confirmation gate as other
  tools.
- Explicitly report external side effects and protect credentials.
- Prefer documented APIs; do not reverse-engineer private interfaces as a
  generic route around application controls.

### 2.6 Browser Automation Backend

**Description:** Uses a browser automation interface such as Playwright
against an explicit browser, context, page, and origin. Uses DOM/accessibility
state and browser APIs rather than desktop coordinates for web tasks.

**Typical use cases**

- Navigate pages, inspect content, fill forms, and interact with web
  applications.
- Verify page navigation, element state, and form results.
- Operate a dedicated automation browser context while the user uses another
  application.

**Strengths**

- Usually independent of desktop foreground focus.
- DOM/accessibility selectors are more stable and verifiable than screen
  coordinates.
- Browser contexts can be isolated from the user's normal browsing session.
- Supports explicit waits and page-level state inspection.

**Limitations**

- Applies to browser-managed content, not arbitrary native desktop dialogs or
  all embedded browser surfaces.
- Authentication, multi-factor flows, anti-bot measures, and cross-origin
  restrictions may limit automation.
- Dedicated context state may differ from the user's logged-in session.

**Verification opportunities**

- Check URL, DOM state, accessible role/name/value, and expected response.
- Capture console/network summaries where policy permits.
- Distinguish a submitted request from server-side completion.

**Safety considerations**

- Treat navigation and web forms as potentially external side effects.
- Require confirmation for purchases, messages, account changes, or other
  consequential submissions.
- Keep cookies/tokens isolated and protected; do not copy user-session
  secrets into model prompts or logs.
- Never silently switch from a semantic page action to global desktop input.

### 2.7 Home Assistant Backend

**Description:** Uses a supported Home Assistant API or MCP integration to
discover exposed entities, inspect current state, and invoke authorized
services/scenes. Home Assistant is the state authority for integrated
devices.

**Typical use cases**

- Query an exposed light, climate, media, lock, or sensor entity.
- Run a scene or service with entity/area context.
- Later, subscribe to permitted state events and prepare user-approved
  automation proposals.

**Strengths**

- Does not depend on Windows focus or a visible desktop UI.
- Provides domain-level entity IDs, state, service, area, and event models.
- Lets Jarvis use HA's entity exposure and integration ecosystem.

**Limitations**

- Depends on Home Assistant availability, configuration, permissions, and
  integration quality.
- Device state can be stale, delayed, or eventually consistent.
- A service call may be accepted without the physical device reaching the
  intended state.

**Verification opportunities**

- Read entity state before and after a service call.
- Track service-call result and subsequent state/event transitions with
  bounded waits.
- Report unavailable, timeout, and observed-but-not-achieved separately.

**Safety considerations**

- Respect HA's exposed-entity filter and use least-privilege credentials.
- Require stronger confirmation for locks, covers, security modes, and other
  physical/security-sensitive operations.
- Make no life-safety guarantee; retain physical device safety controls.
- Log requested entity/service, confirmation, result, and observed state.

## 3. Execution router

### Inputs

The router receives a validated operation and evaluates:

- operation semantics and arguments;
- target type, identity, provenance, and confidence;
- backend-advertised support for the operation;
- backend focus requirements and whether it can operate in the current
  workspace/session;
- available verification/read-back mechanism;
- user permissions, risk tier, and confirmation policy;
- current privacy mode, configuration, and adapter availability.

The router must not infer that an application supports a backend merely
because it is visible, nor infer a unique target from a title alone. Planning
and backend selection remain separate: the planner proposes **what** to do;
the router chooses an authorized **how**.

### Decision sequence

1. Validate the entire task plan before any backend side effect.
2. Resolve the target and identify the requested operation's domain.
3. Query capabilities of enabled backends for that operation/target.
4. Filter out unsupported backends, policy-denied operations, and backends
   whose requirements cannot be met.
5. Rank eligible backends by semantic fit, target confidence, verification
   quality, reliability, latency, and user disruption. Safety and
   authorization are hard constraints, not rank bonuses.
6. Obtain required confirmation before dispatch.
7. Invoke exactly the selected backend with bounded timeout and structured
   result.
8. Verify the action postcondition with the relevant verifier; record
   backend, target, policy, side effects, and evidence separately.
9. If no backend qualifies, return an explicit blocked/unsupported outcome.
   Do not fall through to global keyboard/mouse input without a new
   authorization decision.

Suggested selection outcomes: `SUPPORTED`, `REQUIRES_FOREGROUND`,
`REQUIRES_CONFIRMATION`, `UNSUPPORTED`, and `BLOCKED`. These are routing
decisions, not new task lifecycle states.

### Examples

| Request | Preferred route | Fallback / stop behavior |
| --- | --- | --- |
| "Type hello into Notepad while I keep using Chrome." | UIA value/text operation if the target control exposes a suitable pattern, or a Notepad-specific supported API if available. | If neither supports the operation, report that only foreground input is available. Do not type into Chrome or silently activate Notepad. |
| "Make a note in this project folder." | Workspace backend writes a scoped file after path validation and applicable confirmation. | Use an application API only if the request specifically targets an open document; use foreground UI only if the user permits it. |
| "Search this website and summarize the result." | Browser backend on an explicit page/context, then inspect page state. | If the site requires unsupported auth/human interaction, pause or report unsupported rather than automating around controls. |
| "Turn off the kitchen lights." | Home Assistant backend resolves exposed kitchen light entities, checks authorization, invokes service, then reads state. | If entity mapping is ambiguous, ask which area/entity. Do not fall back to desktop control of an unrelated app. |
| "Open Notepad and type a short note." | Launch/identify target; use API/UIA if available. | If only foreground input exists, require an explicit foreground-interaction policy or user focus, then re-check target. `TYPE_TEXT` remains unverified absent read-back. |
| "Click the button in this inaccessible legacy app." | UIA/MSAA if the control is exposed. | Explicit foreground automation only if authorized, target is confirmed, and interaction is visible; otherwise report unsupported. |

## 4. Workspace automation environments

Workspace tools and execution environments are different concepts:
filesystem/API operations may not require a desktop at all; a separate
interactive environment is relevant only when a workflow genuinely needs
visible UI input.

| Environment | Realistic use | Benefits | Limitations / decision |
| --- | --- | --- | --- |
| **Windows Virtual Desktops** | Organize windows for a human or separate visible workflow. | Convenient organization; windows remain in the user's logged-in session. | Not a security or input-isolation boundary. Switching desktops changes the user's view; global input remains associated with the interactive desktop/session. Do not present as background automation. |
| **Secondary monitor** | Display an automation target while the user watches another screen. | Useful visibility and manual supervision; no separate machine required. | Shares the same interactive session, focus, keyboard, and pointer. Global typing still goes to the focused control and pointer operations can disrupt the user. A second monitor is not a background input channel. |
| **Hidden workspace/window** | Hide or minimize a window for clutter reduction, or use a backend with a non-visible semantic API. | Can keep a supported API or UIA task visually unobtrusive. | A hidden/minimized window does not make global input targetable. Some UIA providers require visible/realized elements; hidden UI can change behavior. Hidden windows make oversight harder. Do not use "hidden" to imply safe isolation. |
| **Dedicated automation session** | Run visible-input automation under a separate logged-in Windows user/session, remote desktop, VM, or supported sandbox. | Stronger separation from the user's active desktop; independent focus and workspace; suitable for unattended UI-only workloads when supported. | Requires separate session lifecycle, credentials, resources, desktop availability, and observability. Services in non-interactive/session-0 contexts cannot be assumed to drive a normal UI. UI/session isolation is not automatically a security sandbox; use OS-supported boundaries and least privilege. |

**Conclusion:** Virtual desktops and secondary monitors are presentation
arrangements, not isolation. Hidden windows are not a generic solution.
Dedicated sessions/VMs are the realistic option for unattended visible-input
work, but are materially more complex and should be a later, separately
tested deployment capability. For common desktop work, prefer semantic
application APIs or UIA that do not require the user's foreground.

## 5. Background automation selection

| Work type | Preferred method | Why not keyboard/mouse by default |
| --- | --- | --- |
| Structured application content (documents, records, settings) | Application API/object model | Expresses the intent directly, can avoid UI layout/focus, and may allow exact read-back. |
| Standard desktop controls with accessible providers | UI Automation; narrow MSAA compatibility only when justified | Targets semantic controls rather than coordinates; supports value/state inspection where available. Provider support must be tested per control. |
| Known, documented legacy window protocol | Win32 messaging only for the documented message contract | Can communicate without activating a window in specific cases, but arbitrary messages/keyboard-message simulation is not a universal input API. UIPI, marshalling, and blocking behavior apply. |
| Web pages and web applications | Browser automation (for example, Playwright) | Uses page/DOM/accessibility state and isolated browser contexts instead of global desktop focus. Native dialogs and human challenges may remain unsupported. |
| Files, source trees, and bounded project checks | Workspace APIs; sandboxed shell only where needed | Direct path and result inspection are more reliable than opening a file and navigating UI. Scope and command side effects must be enforced. |
| Smart-home devices and state | Home Assistant API/MCP | Domain-specific entities and state are more appropriate than controlling a dashboard through GUI clicks. |
| Applications with no usable semantic/API surface | Foreground input, or an isolated interactive session | Global input requires the target to receive focus; if that cannot be assured without disrupting the user, stop or ask. |

Win32 window messaging is not a general backend for sending keyboard input to
arbitrary background controls. Use it only where an application's documented
message protocol defines the action and result. Browser automation is also
distinct from desktop automation: browser page state should not be inferred
from a screenshot or a successful keypress.

## 6. Capability matrix

Qualitative ratings describe typical best-case support for an operation that
the backend actually exposes. They are not guarantees across all
applications. **High user disruption** means substantial impact on the user's
active desktop or application state.

| Backend | Reliability | Speed | Verification quality | User disruption |
| --- | --- | --- | --- | --- |
| Foreground Automation | Medium; depends on visible layout, focus, timing, and app responsiveness. | Medium; direct but often needs waits and visual settling. | Low to medium; screenshots/focus are contextual, and typed content often lacks read-back. | High when the user is active; takes or competes for foreground input. |
| Focus-Aware Backend | Medium; guards known wrong-target cases but remains subject to focus races and control focus. | Medium; observation/check adds modest work, but may wait for user. | Medium for target precondition, low for action result without separate read-back. | Medium to high; no implicit focus change, but execution requires the user to focus the target or relinquish the foreground. |
| Workspace Backend | High for scoped, deterministic file operations; command reliability depends on command and environment. | High for direct operations; command startup varies. | High for file diffs, hashes, paths, and exit codes; semantic correctness still needs tests. | Low, unless a command consumes significant resources or changes shared state. |
| UI Automation Backend | Medium to high for well-supported standard controls; low where providers/custom controls are incomplete. | Medium to high; element discovery and provider responsiveness vary. | Medium to high where control values/states can be read back. | Low to medium; often does not change foreground, but can alter application state. |
| Application API Backend | High for documented, supported operations with stable contracts. | High; generally avoids UI startup and visual waits. | High where the API exposes authoritative state; call success alone is insufficient. | Low for user focus; potentially high for consequential data/account changes. |
| Browser Automation Backend | High for deterministic page selectors and stable workflows; lower for dynamic/auth challenges. | High to medium; page/network waits dominate. | High for URL/DOM/accessibility state; external completion may require server-side confirmation. | Low to medium; can use an isolated context but still changes online accounts/data. |
| Home Assistant Backend | Medium to high for responsive, correctly mapped entities; device/network state may be delayed. | High to medium; service acceptance may precede device state change. | Medium to high when entity state/event read-back is available. | Low for PC focus; potentially high real-world impact, requiring risk-based confirmation. |

Reliability and verification are operation-specific. Router tests should
measure supported workflows rather than treating the table as a universal
ranking. Authorization, target mismatch, and safety policy override any
performance preference.

## 7. Roadmap impact

### Phase 4 — Execution foundation and governed memory

Focus on contracts and controls, not broad automation expansion:

- Complete Phase 3 acceptance checks and manual target mismatch validation.
- Define validated, versioned operation/tool call and result contracts.
- Define backend capability descriptors: supported operations, target types,
  foreground requirement, read-back support, timeout, and side-effect class.
- Introduce the router as a small injected interface without immediately
  adding many adapters.
- Wrap current pyautogui/Win32 actions as an explicitly foreground-required
  backend; retain target mismatch gating.
- Add configuration, authorization/confirmation policy, and durable local
  audit before adding file writes, shell, external account access, or physical
  devices.
- Add user-controlled episodic/preference memory, separate from audit, with
  inspect/edit/export/delete and retention behavior.

**Exit criterion:** current behavior is represented through explicit
capabilities and policy; no hidden focus activation or backend fallback;
calls and outcomes can be explained through task events and durable audit.

### Phase 5 — Workspace and semantic desktop backends

Add bounded non-foreground operations:

- Scoped, initially read-only workspace list/search/read operations; then
  writes and sandboxed project checks under explicit permission.
- UIA read-only discovery and state inspection for a small tested control
  set.
- One low-risk UIA operation with deterministic read-back, or one
  documented application API adapter; do not build both broad frameworks at
  once without demonstrated use.
- Explicit foreground-required execution only as a user-authorized fallback.
- Maintain separate backend, target, dispatch, and verification evidence.

**Exit criterion:** demonstrate one operation while the user continues using
another application, with supported target selection, result read-back, and
clear unsupported behavior when the provider/backend lacks capability.

### Phase 6 — Browser and Home Assistant integrations

Add domain-specific adapters after the policy, audit, configuration, and
backend contract have been exercised:

- Browser automation on explicit page/context, isolated authentication
  storage, and page-state verification.
- Home Assistant integration through its supported API/MCP interface:
  exposed-entity discovery and read-only state first, then low-risk service
  operations, then confirmation-gated physical/security actions.
- Add event-driven/proactive capabilities only after subscription lifecycle,
  privacy controls, alerting, and user approval behavior are tested.

**Exit criterion:** per-domain authorization, side-effect logging, state
read-back, timeouts, and negative/ambiguous target cases pass controlled
integration validation. Voice satellites, multi-agent orchestration, and
unattended autonomous routines remain separate later decisions.

## 8. Preferred long-term execution architecture

Adopt a **capability-based hybrid execution router** over small, typed
adapters:

```text
User request
    ↓
Planner → validated semantic operations + explicit targets
    ↓
Whole-plan preflight
    ↓
Policy / permission / confirmation gate
    ↓
Sequential task runner
    ├─ target and capability resolution
    ├─ explicit backend selection (no silent fallback)
    ├─ dispatch and structured side-effect result
    ├─ independent verifier/read-back
    └─ progress events + durable audit
    ↓
Foreground | Focus-aware | Workspace | UIA
           | Application API | Browser | Home Assistant
```

The backends can begin as in-process Python adapters. Do not introduce
microservices, a distributed message bus, or one process per backend until
concurrency, deployment, or availability requirements justify that
complexity. Keep UIA/window handling in the Windows integration boundary,
browser concerns in a browser adapter, filesystem/shell scope in the
workspace adapter, and home entities in the Home Assistant adapter.

The router should prefer a semantic backend when it supports the requested
operation and target with acceptable verification. It may select foreground
automation only when the target/focus precondition and user policy permit
visible interaction. If the only available backend would disrupt the user
and disruption has not been authorized, stop and explain; do not route around
that policy with hidden windows, virtual desktops, or raw messages.

Persist backend choice and evidence separately from `VerificationResult`.
Keep the current honest verification rule: a successful dispatch, confirmed
foreground, or target identity does not prove text entry or application
state. Upgrade an action to `VERIFIED` only when a deterministic postcondition
is observed from an appropriate source.

## Source basis

- *JARVIS Home Core — Specification v1.0*, user-provided PDF:
  - Sections 2–3: modular layers, message/tool interfaces, memory, perception,
    and action layer.
  - Sections 4.3–4.4: PC control, Playwright browser automation,
    Home Assistant, and mouse/keyboard as last resort for non-API apps.
  - Sections 7–10: tool/result contracts, permissions, confirmations, audit,
    and Home Assistant integration.
  - Section 14: explicit scope and autonomy boundaries.
- [BACKGROUND_AUTOMATION_OPTIONS.md](./BACKGROUND_AUTOMATION_OPTIONS.md):
  Windows focus restrictions, API/UIA/message trade-offs, and hybrid
  backend recommendation.
- [ARCHITECTURE_ALIGNMENT_REVIEW.md](./ARCHITECTURE_ALIGNMENT_REVIEW.md):
  current capability gaps and Phase 4–6 dependency recommendations.
- [PROJECT_VISION.md](./PROJECT_VISION.md), [ROADMAP.md](./ROADMAP.md), and
  [DECISIONS.md](./DECISIONS.md): current project direction and milestones.
- [PHASE3_STEP7B_TARGET_AWARENESS.md](./PHASE3_STEP7B_TARGET_AWARENESS.md):
  target identity, mismatch gating, and separation of target awareness from
  action verification.
