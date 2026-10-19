# Phase 3 Step 7: Window and Focus Awareness Design

## Scope

This document proposes a read-only window and focus awareness capability for
the existing sequential Task Execution Engine. It is a design only: it does
not authorize source changes, automatic window activation, or a claim that
typed text has been verified.

The initial objective is to capture useful desktop context around actions,
report that context through the existing task events and GUI, and establish a
safe foundation for future target-aware execution. The existing
`VERIFIED`/`UNVERIFIED`/`FAILED` meanings and fail-stop policy remain
unchanged.

## 1. Current limitation analysis

`TYPE_TEXT` remains `UNVERIFIED` because the current tool dispatches text to
the keyboard input API but has no deterministic way to read the resulting
contents back from the target application. A successful function return
establishes that typing was dispatched; it does not establish that:

- the intended application had focus at dispatch time;
- the intended control accepted the input;
- the exact requested text appeared; or
- the text was not changed, rejected, or redirected.

Window and focus observations can narrow this uncertainty, but cannot prove
text content. Even observing the expected foreground window immediately
before or after a typing action leaves a race in which focus can change
between observation and input. Accordingly, the first implementation should
report observations as contextual evidence and must not upgrade
`TYPE_TEXT` to `VERIFIED`.

The current verifier framework returns a status and evidence for an action.
The `TYPE_TEXT` verifier deliberately returns `UNVERIFIED`; it does not have
an application-specific read-back channel. The task runner records the result
on the step, emits it in progress events, and concludes `PARTIAL` if any
successful step is unverified.

## 2. Window awareness architecture

Add a small read-only observation layer alongside the existing Windows
automation helpers:

```text
Task runner
  ├─ captures optional window context at defined step boundaries
  ├─ executes the existing action
  ├─ invokes the existing verifier without changing its contract
  └─ emits task events containing the action and observation context
           ↓
Windows observation helper
  ├─ enumerates visible top-level windows (existing capability)
  └─ reads foreground window identity and metadata
           ↓
Tk main-thread queue poller
  └─ renders concise context and existing task/step/verification states
```

The observation helper should return a typed, immutable snapshot rather than
exposing raw Windows handles to the UI or model. Suggested fields:

- observation timestamp;
- whether a foreground window was available;
- process ID, if it can be read;
- process executable/name, if it can be read safely;
- window title, possibly empty;
- visibility/minimized state where available.

Keep the first version read-only. Do not activate, restore, move, or resize
windows. Keep platform API details in the existing tools/Windows integration
area, and keep formatting and display in the GUI. The task runner should
receive observation through a narrow injectable function so unit tests can
provide deterministic snapshots without accessing a live desktop.

The observer should distinguish a legitimate “no foreground window” result
from an observation error. It should not hide unexpected Windows API failures
as an empty or successful snapshot. The task runner must keep observation
errors separate from action execution outcomes.

## 3. Focus awareness architecture

Focus awareness means observing which top-level window is foreground, not
proving that a particular child control has keyboard focus. Windows foreground
ownership is useful context, but controls inside the same application may
have different focus, and applications can change foreground state at any
time.

For the initial scope:

1. Capture the foreground snapshot immediately before each action.
2. Capture a second snapshot after action execution and verification have
   completed.
3. Associate both snapshots with the step's progress/results.
4. Report changes as observations, not as action success or failure.

The before/after pair can show that focus changed during an action window; it
cannot prove exactly when the change occurred or which control accepted input.
Polling continuously for foreground changes is not required for the first
increment and could add noise, event volume, and timing complexity.

Observation should be fast and bounded. It must not block the Tk thread.
Exceptions or unavailable metadata should be represented explicitly in the
observation result and must not silently default to a fabricated active
window.

## 4. Active-window tracking

Track active-window snapshots per step rather than maintaining a global
“active application” assumption. Desktop state can be changed by the user or
by another process between steps, so a previous step's active window is not
reliable evidence for a later step.

Each step may retain:

- `active_window_before`: snapshot immediately before dispatch;
- `active_window_after`: snapshot after execution and verification;
- an observation status/error when either snapshot could not be collected.

The task event should carry the snapshot relevant to that event, or a pair of
before/after snapshots on a step-completion/failure event. The task result
should preserve the same observations for completed steps so the final
summary does not depend on transient UI text.

Tracking should use process ID and native window handle internally where
available to compare identity during the task. Window handles are
process-local, transient values and should not be persisted as durable
identifiers. Avoid treating title text alone as a unique identity.

## 5. Target-window identification

Do not infer a target window solely from natural-language text or a title
substring in the initial implementation. The current action schema has no
declared target-window field, and implicit matching can select the wrong
window when titles are duplicated, localized, or changed by document state.

Use a staged design:

### Initial observation-only stage

- Record the active window before and after each action.
- Do not require a target and do not change focus.
- If the model or user supplied a likely target in the request, display it
  only as request context; do not treat it as a validated target identity.

### Future explicit-target stage

If target-aware actions are later approved, add an explicit, validated target
representation to the plan or a separate user-confirmed selection. Prefer a
stable process identity and a user-selected window identity over an
unconstrained title string. Define matching rules for multiple windows,
missing windows, application restarts, and ambiguous matches before dispatch.

Activating or focusing a target window is a separate side effect and requires
its own approval, safety behavior, verification, and tests. It is not part of
this design's initial implementation.

## 6. Verification opportunities

Window awareness can add contextual checks without changing current
verification semantics:

- `OPEN_NOTEPAD`: retain its existing visible-window verification. A
  foreground snapshot may additionally show whether Notepad became active,
  but foreground status should not become a required condition until its
  semantics and timing are explicitly approved.
- `TYPE_TEXT`: record the before/after foreground process/window as context.
  Keep the action `UNVERIFIED`; foreground identity does not prove text
  content or child-control focus.
- `TAKE_SCREENSHOT`: record the active window as context if useful, but keep
  screenshot file verification authoritative.
- `MOVE_MOUSE` and `LIST_WINDOWS`: preserve their current verification;
  window context is supplemental and must not replace the action's existing
  result.

If the observer is unavailable, an action whose current verifier can still
run should retain its current verification status. A separate mandatory
focus precondition could later cause a clear validation or execution failure,
but must not be smuggled into a verifier as an ambiguous downgrade. Any
future policy that makes a focus mismatch fail a task must define whether
that is a plan validation error, a precondition failure, or a verification
failure.

## 7. New task states or event changes required

No new task or step state is required for read-only observations:

- the existing task states continue to describe lifecycle;
- the existing step states continue to describe execution and verification;
- the observer does not itself start, fail, or complete a task.

The immutable event payload needs an optional window-context field (or
equivalent typed before/after fields) that can contain a snapshot or an
explicit observation error. Existing fields for task state, step state,
verification result, action, and error remain authoritative.

The simplest initial event policy is to attach the pre-action snapshot to
`STEP_STARTED` and both snapshots to the terminal step event
(`STEP_COMPLETED` or `STEP_FAILED`). A separate `WINDOW_CONTEXT_CHANGED`
event is unnecessary unless later continuous monitoring is introduced.
Existing GUI queue polling remains responsible for all widget updates.

If a required observation itself is later made a task prerequisite, define
how its outcome is represented and whether it can fail independently of the
action. Do not add a new task state just to represent an observation result;
use a typed observation status/evidence field unless a distinct lifecycle
transition is demonstrably needed.

## 8. Interaction with the current verification framework

Keep the verifier registry and `VerificationResult` contract focused on the
action's postcondition. Window snapshots are context; they should not be
embedded in a way that makes them appear to be proof of unrelated effects.

Recommended separation:

- `VerificationResult`: status and evidence for the action outcome, unchanged.
- `WindowSnapshot` (or equivalent): read-only observation of foreground
  window state.
- Step/task result: stores both action verification and window observations.
- `TaskEvent`: transports both values to the UI without Tk access in the
  worker thread.

Inject the observation function into the runner, similarly to action
execution, to test call timing, unavailable observations, and errors. Preserve
preflight-before-side-effects: validation must still finish before desktop
actions run. If observation occurs during validation in a later design, it
must remain read-only and must not change the existing guarantee that invalid
plans cause no action execution.

The first implementation must not alter `TYPE_TEXT`'s `UNVERIFIED` result,
the task's `PARTIAL` completion policy, verifier lookup behavior, fail-stop
semantics, retries, or cancellation.

## 9. Risks

- **Race conditions:** foreground focus can change between a snapshot and
  input dispatch.
- **Overstated confidence:** observing the expected top-level window does not
  prove child-control focus or text entry.
- **Unstable identity:** titles change, processes restart, and handles are
  transient.
- **Privacy:** titles can contain document names or other user-sensitive
  context. Display only what is useful; do not send snapshots to the model or
  persist more than required.
- **Platform errors:** window enumeration and metadata reads can fail or
  return partial data. Preserve explicit error status rather than silently
  substituting defaults.
- **User disruption:** activating a window could steal focus or interrupt
  work; the initial design is observation-only.
- **Event compatibility:** adding event fields must preserve existing event
  consumers and tests.
- **Timing and responsiveness:** observation must remain bounded and run on
  the task worker, while UI rendering stays on Tk's main thread.
- **Scope expansion:** focus tracking does not justify adding screenshots,
  OCR, application-specific text extraction, or model-based visual reasoning
  in this step.

## 10. Testing strategy

### Unit tests

- Normalize valid foreground-window data, absent foreground windows, partial
  metadata, and explicit observation errors.
- Verify snapshots are captured at the defined before/after boundaries and
  attached to the correct task step and events.
- Use injected fake observers; do not call live Windows APIs in unit tests.
- Confirm observation errors do not silently become an empty successful
  result and do not change existing action verification outcomes.
- Confirm a `TYPE_TEXT` step remains `UNVERIFIED` even when the expected
  foreground window is observed before and after.
- Confirm each existing action's verifier behavior and task-state outcome
  remain unchanged.
- Confirm the runner and observer do not access Tk widgets, and GUI updates
  remain in `root.after` polling.
- Confirm invalid plans still cause no action execution.
- Confirm no activation, restore, move, or resize API is called.

### Controlled Windows integration tests

- Observe foreground identity with one known window and with multiple visible
  windows.
- Change focus manually during a controlled task and confirm the before/after
  observations are reported accurately without claiming exact timing.
- Run `OPEN_NOTEPAD`, `TAKE_SCREENSHOT`, and `TYPE_TEXT` and confirm existing
  verification results remain the same.
- Confirm absent or inaccessible foreground metadata is reported without
  hanging or falsely failing unrelated actions.
- Confirm the UI remains responsive and displays only the approved,
  privacy-conscious context.

## 11. Incremental implementation plan

1. **Finalize observation contract:** choose typed snapshot fields, explicit
   unavailable/error representation, privacy limits, and identity semantics.
2. **Add read-only foreground observer:** implement a narrow Windows helper
   and unit tests for normalized results and failures; do not alter focus.
3. **Inject and capture context:** add the observer dependency to the task
   runner and capture before/after snapshots per step. Keep action execution
   and verifier logic unchanged.
4. **Extend event/result data:** add optional snapshot fields to step results
   and immutable task events, preserving existing fields and consumers.
5. **Display context in the GUI:** render concise foreground-window evidence
   using the existing Tk-safe queue polling path; avoid sending it to Ollama.
6. **Run regression and integration checks:** run all task/verifier unit tests,
   verify that `TYPE_TEXT` remains unverified, then conduct controlled
   Windows tests for foreground changes and unavailable metadata.
7. **Review before target-aware behavior:** treat explicit target selection,
   focus enforcement, window activation, and text read-back as separate
   follow-up decisions rather than silently expanding this step.

## Completion criteria

The feature is ready when the GUI reports trustworthy before/after foreground
context for each relevant step, observation failures remain explicit, all
existing task and verification semantics are preserved, `TYPE_TEXT` remains
`UNVERIFIED`, no window is activated automatically, and unit plus controlled
Windows tests pass.
