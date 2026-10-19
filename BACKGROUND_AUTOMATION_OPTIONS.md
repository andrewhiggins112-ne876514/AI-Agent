# Background Automation Options

## Purpose

This proposal investigates how AI-Agent could work with a Windows application
while the user is actively using another application. It is an architecture
proposal only; no implementation is authorized by this document.

The distinction that drives the design is between:

- **Background semantic automation:** ask an application or its accessible
  controls to perform an operation without routing global keyboard and mouse
  input through the user's foreground window.
- **Foreground input automation:** send keyboard or pointer input to the
  active desktop. This requires controlling or relying on focus and can
  conflict with concurrent user input.
- **Isolated interactive automation:** run a separate desktop/session/VM for
  automation so that synthetic input is not sent into the user's interactive
  desktop.

There is no universal Windows API that makes arbitrary foreground-oriented
input safe to route to an arbitrary background application. The appropriate
mechanism depends on the application, the requested operation, and the
application's exposed automation capabilities.

## Current project context

AI-Agent currently uses a Tkinter UI, Ollama-generated action plans, a
sequential task runner, and desktop tools in `scripts/tools.py`. The tools
include `pyautogui` for typing, mouse movement, and screenshots, plus Win32
window observation. `TYPE_TEXT` sends keystrokes to the active input recipient;
it does not identify a window as the input destination.

Phase 3 Step 7B associates a task target with a successful Notepad launch,
compares it with the foreground snapshot before typing, blocks typing on a
known HIGH/MEDIUM mismatch, and reports the assessment. It does not activate
the target or make global input background-capable. `TYPE_TEXT` remains
`UNVERIFIED`.

This creates a useful architectural boundary: task planning and lifecycle
should request an operation against an identified target, while an execution
backend determines whether that operation can be performed in the background,
requires foreground interaction, or is unsupported. A capability limitation
must be visible to the runner rather than silently falling back to global
input.

## Options

### 1. Focus management

**Description:** Observe and, where explicitly allowed, change the foreground
window and keyboard focus before using the existing `pyautogui` input path.
This includes confirming the target, optionally restoring it, foregrounding
it, and checking focus immediately before dispatch.

- **Benefits**
  - Smallest conceptual change to the current architecture and typing tool.
  - Works with applications that are operable only through visible keyboard
    and pointer interaction.
  - Target checks make misdirected input less likely than blind global input.
- **Limitations**
  - It is not background automation: focus is taken from the application the
    user is using, and synthetic input can conflict with real input.
  - Foreground activation is not guaranteed. Windows restricts which process
    can call `SetForegroundWindow`; it can deny a request and notify the user
    rather than stealing focus.
  - A focus observation and later key dispatch are separate operations, so a
    race remains. Top-level foreground does not establish the focused child
    control.
- **Risks**
  - User disruption, lost keystrokes, input sent to the wrong application
    after a focus change, and misleading success if activation is denied.
  - Restoring or raising a window can change the user's window layout or
    z-order.
- **Compatibility with current architecture**
  - High. It extends the existing observer, target assessment, and
    `pyautogui` tool path.
  - Must remain an explicit foreground-required backend and must report
    activation/focus failure before dispatch.
- **Can it operate while the user uses another application?**
  - No, not concurrently on the same interactive desktop. It can switch focus
    away from the user's current application, but that interrupts the user's
    interaction.
- **Suitability for games**
  - Low and unreliable. Focus may be required, games often use custom input
    handling, and game policy or anti-cheat may prohibit automation. Do not
    bypass protections or inject into game processes.
- **Suitability for desktop applications**
  - Moderate as a compatibility fallback for visible applications, but it is
    foreground automation and not a solution to concurrent use.

### 2. Window activation and restoration

**Description:** Locate the target window by the task-associated identity,
restore it if minimized, and request that Windows activate it before using
global input. This is a particular mechanism for focus management, separated
here because restoration and activation are often conflated.

- **Benefits**
  - Can make a minimized or obscured target visible before a UI-driven step.
  - Allows an explicit activation outcome to be reported and checked.
  - Fits the current process/window identity model.
- **Limitations**
  - Restoration is not equivalent to background interaction. `ShowWindow`
    modes differ: some activate, while no-activate modes show without giving
    keyboard focus.
  - `SetForegroundWindow` is subject to Windows foreground restrictions and
    can fail even when the caller appears eligible.
  - Activation does not guarantee focus of the intended control.
- **Risks**
  - Steals focus, interrupts the user, changes window state, and may cause
    the user's next input to go to the automation target.
  - Treating a successful API return as proof of effective keyboard focus
    would overstate the result.
- **Compatibility with current architecture**
  - High as an optional, separately authorized operation in the Windows
    adapter layer.
  - It should not be hidden inside `OPEN_NOTEPAD` or applied implicitly to
    all target actions.
- **Can it operate while the user uses another application?**
  - No. It may bring the target forward, but that changes which application
    receives input and interrupts concurrent user interaction.
- **Suitability for games**
  - Low. Full-screen, exclusive, or custom window behavior can make this
    disruptive or ineffective, and game protections may prohibit it.
- **Suitability for desktop applications**
  - Moderate for user-approved, short foreground workflows. Poor for
    unattended background operation.

### 3. Win32 messaging

**Description:** Send or post window messages directly to a target window,
for example a control-specific command or a conventional window message,
instead of using global physical-input simulation.

- **Benefits**
  - Can avoid moving the user's foreground focus for applications whose
    window procedure intentionally supports the required messages.
  - Does not inherently require global mouse or keyboard routing.
  - A narrow, documented message protocol can be efficient for a known
    application.
- **Limitations**
  - Window messages are not a universal semantic automation contract.
    Applications may ignore, reinterpret, or reject synthetic messages.
  - Keyboard messages sent to a window are not reliably equivalent to normal
    user input across controls, frameworks, IMEs, and custom UI.
  - Cross-process messages are subject to UIPI; custom messages may require
    marshalling, and synchronous `SendMessage` may block.
  - A successful post means delivery to a queue, not that the requested
    application outcome occurred.
- **Risks**
  - Application hangs or deadlocks from synchronous calls, incorrect
    parameters, stale HWNDs, cross-integrity access denial, and undefined
    application behavior.
  - Broad or arbitrary message use increases fragility and security exposure.
- **Compatibility with current architecture**
  - Low to moderate. It could be one specialized backend, but each supported
    application/message contract needs an explicit implementation, timeout,
    result, and verifier.
  - It should not replace the current general action executor.
- **Can it operate while the user uses another application?**
  - Sometimes, when a target application supports the specific message
    behavior. It is not a general way to type into arbitrary background
    applications.
- **Suitability for games**
  - Very low. Games commonly do not expose documented window-message
    commands for gameplay, use custom input paths, and may prohibit such
    automation.
- **Suitability for desktop applications**
  - Low generally; potentially good for a known, documented application
    protocol or narrow legacy application.

### 4. Microsoft UI Automation (UIA)

**Description:** Use Windows UI Automation client APIs to inspect a target's
automation tree and invoke supported control patterns such as `Invoke`,
`Value`, `Selection`, or `Text`, instead of simulating global keystrokes.

- **Benefits**
  - Provides structured element identity, properties, relationships, events,
    and operations rather than relying on screen coordinates or window titles.
  - Supported patterns can invoke controls or set/read values without
    bringing the entire window to the foreground.
  - Can support deterministic evidence: the adapter may read a control value
    after setting it, where that control exposes an appropriate pattern.
  - Microsoft describes UIA as intended for assistive technology and
    automated testing clients.
- **Limitations**
  - Coverage depends on the target application's UIA provider and control
    implementation. Custom-rendered controls may expose incomplete or no
    useful elements.
  - Some patterns are read-only, dynamic, or absent for a given control.
    A successful pattern call is not automatically proof of the full task
    postcondition.
  - UIA interaction can be asynchronous and cross process; element references
    can become stale as the interface changes.
  - Access to elevated UI and protected system surfaces has integrity and
    trust constraints. `UIAccess` is a narrowly regulated assistive-
    technology facility, not a general privilege-escalation mechanism.
- **Risks**
  - Incorrect element selection, stale element references, timeouts, provider
    defects, and false confidence from invoking a control without verifying
    the resulting state.
  - UIA can access substantial application information; target scope and
    privacy must be explicit.
- **Compatibility with current architecture**
  - High as a new backend behind a typed automation adapter. The existing
    task runner, preflight, task events, and verification model can remain.
  - Requires action contracts to express target/control intent and backend
    results to distinguish unsupported, unavailable, failed, and verified
    operations. This should not be encoded as a special case inside
    `pyautogui.write`.
- **Can it operate while the user uses another application?**
  - Often for supported control patterns and well-behaved providers, without
    global focus changes. It is not a guarantee; some applications or
    controls still require foreground interaction.
- **Suitability for games**
  - Very low for typical games, which generally expose custom-rendered game
    scenes rather than conventional accessible controls. Use only documented
    game-provided APIs or accessibility features.
- **Suitability for desktop applications**
  - High for standard, accessible desktop controls; moderate overall because
    provider quality and application-specific behaviors vary.

### 5. Application-specific APIs

**Description:** Prefer an application's supported automation interface:
COM/object models, scripting APIs, command-line interfaces, local protocols,
document APIs, or a vendor-supported automation endpoint. Examples include
Office's VBA/COM model for document operations or a browser's supported
automation interface, subject to the application's security model.

- **Benefits**
  - Highest semantic precision when available: operations can target
    documents, records, tabs, or objects directly without depending on
    foreground focus or screen layout.
  - Often best for deterministic read-back, idempotency, and actionable
    errors.
  - Can continue while the user uses another application because the request
    is directed to the application's own object/service model.
- **Limitations**
  - Each application has a different API, authentication model, lifecycle,
    and versioning strategy.
  - Some APIs require a running application instance; others can operate on
    files or services without a GUI. Some APIs are unsupported, deprecated,
    or unavailable for consumer editions.
  - Does not automatically cover arbitrary interface-only actions.
- **Risks**
  - Broad permissions, accidental modification of the wrong document/account,
    API rate limits, version incompatibility, and external side effects.
  - An API's success response must still be mapped to the task's declared
    postcondition.
- **Compatibility with current architecture**
  - High as per-application adapters registered by capability and target
    type. It requires explicit contracts, not a generic fallback that
    silently chooses APIs.
  - Fits the project's long-term multi-tool vision better than trying to
    make global input serve every application.
- **Can it operate while the user uses another application?**
  - Usually yes, if the application exposes an API that accepts the requested
    operation independently of UI focus. It is application- and operation-
    specific.
- **Suitability for games**
  - Low unless the game provides a documented, permitted API, mod interface,
    or command channel for the relevant operation. No process injection,
    anti-cheat bypass, or undocumented control channel should be used.
- **Suitability for desktop applications**
  - Very high for supported business/document workflows; less useful for
    arbitrary visual navigation or applications without an automation API.

### 6. Accessibility frameworks

**Description:** Use accessibility interfaces to discover and operate
controls. On Windows, the main families include Microsoft UI Automation and
the older Microsoft Active Accessibility (MSAA/`IAccessible`). UIA is compared
separately above; this option covers a deliberate accessibility-client
strategy and compatibility/fallback across accessibility providers and
frameworks.

- **Benefits**
  - Accessibility semantics expose roles, names, states, relationships, and
    user-level operations that are more stable than coordinates.
  - A fallback layer can cover older applications that expose MSAA but have
    weak or missing UIA support; Windows provides interoperability between
    UIA and MSAA, though they are not fully equivalent.
  - The same semantic information can improve vision-free verification and
    explain why a control was selected.
- **Limitations**
  - Accessibility is not a promise that every application exposes every
    control or action.
  - MSAA is legacy and generally exposes less information than UIA; a
    cross-framework strategy adds discovery, normalization, and testing
    complexity.
  - Screen-reader accessibility semantics do not necessarily describe every
    application-specific operation the agent wants to perform.
- **Risks**
  - Misidentifying similarly named controls, inaccessible custom controls,
    provider defects, privilege boundaries, and inadvertently collecting
    sensitive accessible text.
  - Supporting multiple frameworks can create inconsistent behavior unless
    capability and provenance are retained in results.
- **Compatibility with current architecture**
  - Moderate to high if represented as one semantic automation port with
    UIA as the preferred Windows provider and a narrowly scoped MSAA fallback.
  - Keep framework discovery and COM/UIA details out of the task runner and
    GUI; report selected element identity and operation evidence through
    structured results/events.
- **Can it operate while the user uses another application?**
  - Often for provider-supported control operations; not guaranteed for
    actions that depend on global focus or an application's foreground-only
    behavior.
- **Suitability for games**
  - Very low for typical games; potentially useful only for menu/settings
    controls that the game explicitly exposes through accessibility.
- **Suitability for desktop applications**
  - High when controls expose accessibility semantics; fallback support can
    improve breadth but not provide universal coverage.

### 7. Hybrid approaches

**Description:** Select an execution backend for each target and operation,
with an explicit preference order and clear capability reporting. A practical
combination is:

1. application-specific API when it directly supports the requested
   operation;
2. UI Automation semantic controls where the application exposes them;
3. foreground activation plus visible input only when necessary and
   explicitly permitted;
4. isolated interactive desktop/VM for unattended workflows requiring
   arbitrary UI input;
5. unsupported/clarification when no safe backend can satisfy the request.

- **Benefits**
  - Gives common desktop workflows background-capable semantic paths while
    retaining a visible-input fallback for less accessible applications.
  - Avoids claiming that all Windows applications can be automated in the
    background.
  - Supports gradual adoption: start with one well-supported application
    adapter, then add UIA and visible-input capabilities.
  - Backend capabilities and evidence can be tested independently of the
    planner and GUI.
- **Limitations**
  - Requires capability discovery, a target-aware action contract, policy for
    backend selection, consistent result semantics, and more test coverage.
  - Some tasks combine methods and can cross from background operation to
    foreground input, requiring a user-visible transition or refusal.
  - Isolated desktops/VMs add resource, setup, session, and observability
    costs and do not automatically solve application licensing or security
    policy.
- **Risks**
  - Silent backend fallback could cause unexpected focus changes or different
    semantics. Backend selection must be recorded and visible.
  - Partial operations across backends can leave the application in an
    intermediate state. Preserve per-step results; do not assume rollback.
  - Concurrent user changes can invalidate target or document assumptions.
- **Compatibility with current architecture**
  - Best long-term fit. Keep the sequential task runner and verification
    registry, and introduce a target-aware automation adapter layer beneath
    them. Add explicit backend/capability and evidence to each structured
    step result/event.
  - Preserve current `pyautogui` behavior as a clearly named
    foreground-required backend, not as a hidden fallback for background
    operations.
- **Can it operate while the user uses another application?**
  - Yes for operations performed through APIs or accessible controls that
    support background execution. Foreground-input operations remain
    interruptive; arbitrary UI can be isolated in a separate desktop/VM.
- **Suitability for games**
  - Limited. Use only official game APIs or game-provided accessibility
    features. Otherwise mark the operation unsupported; do not inject input
    or circumvent anti-cheat or other protections.
- **Suitability for desktop applications**
  - Best overall. Select application APIs or UIA when supported and use
    visible-input interaction only as an explicit, user-approved fallback.

## Comparison summary

| Option | Background while user interacts elsewhere | Desktop applications | Games | Fit with current architecture |
| --- | --- | --- | --- | --- |
| Focus management | No; it changes focus and interrupts the user | Medium fallback | Low | High, but remains foreground-only |
| Activation/restoration | No; activation gives target the foreground | Medium for explicit user-approved work | Low | High as a separate optional tool |
| Win32 messaging | Sometimes, only for known message contracts | Low generally; medium for specific apps | Very low | Low to medium |
| Microsoft UI Automation | Often, when provider/control patterns support the operation | High on accessible controls | Very low | High as a semantic backend |
| Application-specific APIs | Usually, where the API supports the operation | Very high for supported workflows | Low unless officially exposed | High through per-app adapters |
| Accessibility frameworks | Often, when the provider supports the operation | High, coverage varies | Very low | Medium to high |
| Hybrid | Yes for background-capable methods; not for global input | Very high overall | Low; official interfaces only | Best long-term fit |

## Recommended future architecture

Adopt a **capability-based hybrid automation layer** between the task runner
and desktop/application operations:

```text
Planner
  ↓ target-aware, validated task steps
Task runner
  ├─ asks capability registry for supported operations
  ├─ enforces interaction policy and target preconditions
  ├─ invokes one explicit backend
  └─ records backend and evidence independently of verification
          ↓
Automation adapters
  ├─ application-specific API adapters
  ├─ Windows UI Automation adapter
  ├─ optional MSAA compatibility adapter
  ├─ explicit foreground-input adapter (existing pyautogui path)
  └─ optional isolated-desktop/VM adapter
```

The task action should express **what** is intended (target application,
operation, and required evidence), not prescribe raw keys or coordinates when
a semantic operation is available. The capability registry should describe
whether a backend:

- can operate without foreground focus;
- requires visible foreground interaction;
- can read back the requested state;
- supports the specific operation and target;
- is unavailable because of security, integrity, or application limitations.

Backend selection must be explicit and observable. Do not silently fall back
from an API/UIA operation to focus-stealing input. If only foreground input is
available while the user is active elsewhere, ask for authorization or report
that the task cannot safely continue. For unattended arbitrary UI workflows,
prefer an isolated interactive environment over competing for the user's
desktop.

Keep `VerificationResult` focused on the action postcondition. Backend
identity, focus requirement, target assessment, and operation evidence should
remain separate structured facts. A successful UIA/API invocation may enable
stronger verification only when the backend can read the relevant resulting
state. `TYPE_TEXT` should remain `UNVERIFIED` until exact text can be read back
from the intended control.

## Recommended incremental path

1. **Define operation capabilities and interaction modes.** Add no new
   automation backend yet. Classify current `pyautogui` typing and pointer
   operations as foreground-required and ensure the planner/runtime can
   distinguish them from background-capable operations.
2. **Prototype one semantic application adapter.** Choose a low-risk
   operation in an application with a documented API or reliable UIA support.
   Test background operation, target identity, timeouts, read-back, and
   failure reporting without changing the generic input path.
3. **Add Windows UIA support for a bounded control set.** Start with discovery
   and read-only state inspection, then add only patterns with deterministic
   tests. Preserve clear unsupported outcomes for custom controls.
4. **Keep foreground automation explicit.** Require an explicit policy/user
   decision before activation or global input, and report focus changes.
5. **Evaluate isolation for unattended interactive workflows.** Treat
   separate desktop/session/VM operation as its own deployment feature with
   security, resource, and manual validation requirements.

## Sources

- Microsoft, [SetForegroundWindow function](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow) — documents foreground restrictions and that applications cannot force foreground while the user works in another window.
- Microsoft, [ShowWindow function](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow) — documents activation versus no-activation show modes and restoration behavior.
- Microsoft, [SendMessage function](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessage) — documents synchronous window-procedure delivery, UIPI restrictions, and message marshalling.
- Microsoft, [PostMessageW function](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew) — documents queued message delivery and UIPI restrictions.
- Microsoft, [UI Automation Overview](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-uiautomationoverview) — describes the UIA client/provider model, UI element tree, and control patterns.
- Microsoft, [UI Automation Control Patterns Overview](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controlpatternsoverview) — describes patterns as control-specific operations and properties.
- Microsoft, [UI Automation and Active Accessibility](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-msaa) — compares UIA and legacy MSAA, including their interoperability and differences.
- Microsoft, [Microsoft Active Accessibility](https://learn.microsoft.com/en-us/windows/win32/winauto/microsoft-active-accessibility) — describes MSAA's accessibility purpose and COM-based API.
- Microsoft, [Security Considerations for Assistive Technologies](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-securityoverview) — documents UIAccess trust, manifest, installation, and integrity-level constraints.
- Microsoft, [Office VBA reference](https://learn.microsoft.com/en-us/office/vba/api/overview/) — documents Office's application-specific automation surface.
- Microsoft, [Raw Input Overview](https://learn.microsoft.com/en-us/windows/win32/inputdev/about-raw-input) — describes application-side HID input registration and processing; it is not a general automation mechanism for sending background input to other applications.
