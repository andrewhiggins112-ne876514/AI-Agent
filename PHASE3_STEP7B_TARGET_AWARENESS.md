# Phase 3 Step 7B: Target Window Awareness Design

## Scope

This document proposes how the Task Execution Engine could identify an
action's intended window, compare it with the observed foreground window, and
report or safely handle a mismatch. It is design only: no implementation,
automatic focus change, or modification of the current verification policy is
authorized here.

The design builds on Step 7A, which captures a read-only foreground snapshot
immediately before each dispatch and attaches it to `STEP_STARTED`. It
preserves sequential execution, full-plan preflight, the existing task and
step states, and the `VERIFIED` / `UNVERIFIED` / `FAILED` distinction.

## 1. Current limitation analysis

### Foreground window versus intended target

The foreground window is the top-level window Windows currently considers
active for user interaction. The intended target is the window or desktop
surface that a particular action is meant to affect. These are related but
not equivalent:

- `TYPE_TEXT` sends keyboard input to the current input recipient; it does
  not specify a target window in its action parameters.
- `OPEN_NOTEPAD` starts Notepad, but the current action result does not
  provide a durable identity linking that process to a later typing step.
- `TAKE_SCREENSHOT`, `LIST_WINDOWS`, and `MOVE_MOUSE` operate on desktop-wide
  state and do not necessarily have one application window as their target.
- A foreground snapshot records observed context, not the user's intended
  target and not child-control focus.

Step 7A improves evidence because it records which top-level window was
foreground immediately before dispatch, including its title, handle, and
process ID when available. It does not compare that observation with a
reliably identified intended target, stop a potentially misdirected action,
or prove the action's result. It therefore improves visibility and diagnosis,
not the verification status.

### Why `TYPE_TEXT` remains `UNVERIFIED`

The typing tool dispatches keystrokes but does not read the target control's
contents back. Foreground identity can show that a likely application was
active, but cannot prove that the correct child control had focus, that the
requested text appeared exactly, or that the application accepted it.
Focus may also change between observation and input dispatch.

Thus a foreground match can support a target/focus precondition, but cannot by
itself turn `TYPE_TEXT` into `VERIFIED`. Text verification needs a
deterministic read-back mechanism for the specific target and control.

## 2. Target window model

### Target window

The target window is the intended top-level window for an action when the
action has a meaningful single-window destination. A target should be
represented by an identity record rather than a title string alone. Candidate
identity fields include:

- process ID for a running process;
- native window handle for the current window instance;
- process executable or registered application identity, where safely
  available;
- title as descriptive metadata, not a unique key;
- source and confidence of the identification.

Window handles and process IDs are transient runtime values. They are useful
for comparison within one task but must not be treated as durable identity
across application restarts.

### Foreground window

The foreground window is the most recent observed top-level window receiving
desktop foreground status. It is an observation, represented by the Step 7A
snapshot. It is not automatically the intended target.

### Target confidence

Target confidence describes the strength of the identity match, not the
likelihood that an action's requested effect occurred. Use explicit
categories:

- **HIGH** — exact current window handle matches a task-associated target,
  with process identity consistent.
- **MEDIUM** — process identity matches the task-associated target, but the
  current window handle differs or is unavailable; this may occur when an
  application replaces or recreates its window.
- **LOW** — only a title or application-name heuristic matches.
- **UNKNOWN** — no target is defined, observations are unavailable, or
  identity is ambiguous.

Confidence must not be silently promoted. In particular, matching title
text alone is never HIGH confidence.

### Target mismatch

A target mismatch exists when a target has been resolved with sufficient
confidence for policy and the observed foreground identity does not match
that target. Distinguish mismatch from:

- **unknown target**: the action has no single-window target;
- **ambiguous target**: multiple candidates satisfy the current matching
  rules;
- **observation unavailable/error**: the foreground cannot be established;
- **matched target**: observed identity matches the expected target at a
  stated confidence.

Unknown or unavailable is not itself evidence of mismatch.

## 3. Target identification strategy

Target resolution should be action-aware. Do not force every action to have a
window target.

| Action | Intended target | Identification strategy |
| --- | --- | --- |
| `OPEN_NOTEPAD` | The Notepad instance started by this step. | Prefer a process identity returned by the launch operation and associate a visible top-level window with that process. If launch identity is unavailable, a Notepad title/process heuristic is at most LOW confidence and must be reported as such. Multiple candidates remain ambiguous; do not pick arbitrarily. |
| `TYPE_TEXT` | The target established by an explicit task association or a preceding target-producing step, such as `OPEN_NOTEPAD`. | Carry the associated target identity forward in task context. If there is no explicit or unambiguous target, report UNKNOWN and do not claim that the current foreground window is the intended one. A future user-selected target can provide an explicit association. |
| `TAKE_SCREENSHOT` | The desktop as a whole, not one application window. | No single target window is required. Record the foreground snapshot as contextual metadata only; screenshot output verification remains authoritative. |
| `LIST_WINDOWS` | The current desktop/session's enumerable visible windows. | No single target window is required. The action's result is the window listing; foreground metadata is contextual only. |
| `MOVE_MOUSE` | The desktop pointer and requested screen coordinates. | No single target window is required. Preserve coordinate verification; a foreground window is context only and does not determine whether the pointer reached the requested location. |

For the initial target-aware implementation, do not infer a target solely from
free-form natural-language text. A user-selected target or a target
established by a successful task action is stronger than a model-generated
title guess. Any future action-schema target field must be explicitly
validated and must not weaken existing parameter validation.

## 4. Focus mismatch detection

The engine compares the expected target association for a window-directed
action with the Step 7A foreground snapshot taken immediately before
dispatch. The comparison is observational and does not activate or focus a
window.

### Example: Notepad opens, user clicks Chrome, then `TYPE_TEXT` executes

1. `OPEN_NOTEPAD` starts a Notepad instance. The task associates the resulting
   Notepad window/process as the target, provided identity is available with
   sufficient confidence.
2. The user switches to Chrome before the next step.
3. Immediately before `TYPE_TEXT`, the observer reports Chrome as foreground.
4. The resolved task target is Notepad, so the engine records a target
   mismatch.
5. The safest default is **do not dispatch `TYPE_TEXT`** when a HIGH- or
   MEDIUM-confidence target is known to differ from the foreground. Mark the
   step failed as a target precondition failure, mark remaining steps
   skipped, and fail-stop the task. Preserve the already completed
   `OPEN_NOTEPAD` result.
6. Report clearly that the text was not sent because the foreground target
   differed. Do not claim the in-flight text action was interrupted; it was
   never invoked.

If the target is LOW confidence, ambiguous, or UNKNOWN, do not automatically
block or redirect the action based on a guessed identity. Report the
uncertainty and apply a separately approved policy. For this design, the
conservative behavior is to avoid claiming a target match; whether to require
user confirmation before typing should be decided before implementation.

The action plan and task event ordering should make the precondition outcome
visible before any action dispatch. A target mismatch is not a verifier result
for the text content: the action was not executed, so no postcondition
verification was attempted.

## 5. Verification opportunities

### What becomes verifiable

- Whether a task-associated window is the foreground top-level window at the
  pre-dispatch check.
- Whether the foreground process/window matches a known target at a defined
  confidence.
- Whether an action was safely withheld because its target precondition did
  not hold.
- Whether a Notepad window associated with a launched process remains
  available for a subsequent task step, subject to window/process observation
  reliability.

These are target/focus and control-flow facts. They do not establish content
or the full semantic success of an action.

### What remains unverifiable

- Whether the intended child control has keyboard focus.
- Whether keystrokes were accepted or transformed by the target application.
- Whether the exact requested text is present after typing.
- Whether an application has completed its own asynchronous work merely
  because its top-level window exists or is foreground.
- Targets for desktop-wide operations such as screenshots, window listing,
  and pointer movement, beyond their existing action-specific verification.

### Moving `TYPE_TEXT` closer to `VERIFIED`

Target awareness can improve the precondition but cannot verify text content.
To move typing toward `VERIFIED`, a later capability would need deterministic
read-back from the intended target control, for example through a supported
Windows UI Automation text/value pattern or an application-specific,
validated control interface.

Such a verifier must:

- read from the same task-associated target and intended control;
- compare the observed value with the exact expected text or a precisely
  defined insertion result;
- distinguish unsupported/unavailable read-back (`UNVERIFIED`) from a
  confirmed mismatch (`FAILED`);
- account for prior control contents, selection, newline behavior, and
  asynchronous updates;
- avoid interpreting clipboard contents, successful key dispatch, or
  foreground identity as proof that text appeared.

Until such a mechanism is independently designed and tested,
`TYPE_TEXT` stays `UNVERIFIED`, and successful tasks containing it remain
`PARTIAL`.

## 6. Event model impact

No new task or step lifecycle state is needed. Existing `RUNNING`, `FAILED`,
`SKIPPED`, and terminal task states can represent target-precondition failure
and fail-stop behavior. Do not add a new global target-mismatch task state.

The event/result payload should make target assessment explicit and separate
from `VerificationResult`. A small immutable `TargetAssessment` value can
contain:

- expected target identity, if resolved;
- observed foreground snapshot;
- confidence category;
- match/mismatch/unknown/ambiguous status;
- concise reason or error;
- whether dispatch was withheld by policy.

Possible event usage:

- `STEP_STARTED`: include the Step 7A foreground snapshot and resolved target
  assessment immediately before the action.
- For a mismatch that prevents dispatch: emit `STEP_FAILED` with the
  precondition reason and target assessment; do not create a verification
  result for an action that did not run.
- `STEP_COMPLETED` / `STEP_FAILED` after an invoked action: preserve the
  target assessment alongside the existing execution and verification
  result.

The GUI should display expected target, observed foreground, confidence,
and mismatch disposition concisely. Existing queue polling remains the only
path for worker progress to update Tk widgets. Avoid a separate
`TARGET_MISMATCH` event type unless later consumers demonstrate that the
existing step-failure event cannot express the transition clearly.

## 7. Risks

- **Multiple matching windows:** applications may have several documents or
  windows. The engine must report ambiguity rather than pick the first
  title/process match.
- **Changed window titles:** titles can include filenames, localization, or
  unsaved markers and are not stable identity.
- **Focus race:** the foreground window can change after observation and
  before the keyboard action. A pre-dispatch check narrows but cannot remove
  this interval.
- **User interference:** the user can change focus during a multi-step task.
  A safe mismatch stop may interrupt the remaining plan but should preserve
  completed work.
- **Incorrect target identification:** a wrong process/window association can
  withhold a valid action or direct input to an unintended application.
- **Process/window lifecycle:** process IDs and handles are transient; apps
  can create replacement windows or exit between steps.
- **Privacy:** titles may reveal document names. Display only necessary
  information; do not send target metadata to Ollama or persist it by default.
- **Overstated verification:** matching a foreground window does not prove
  child-control focus or text insertion.
- **Policy ambiguity:** behavior for LOW-confidence, UNKNOWN, or ambiguous
  targets must be decided explicitly; do not silently fall back to whatever
  window happens to be foreground.
- **Event/result compatibility:** optional fields must preserve current event
  consumers and keep target evidence separate from action verification.

## 8. Testing strategy

### Unit tests

- Resolve a target from an explicit task association and verify HIGH or
  MEDIUM confidence according to exact window/process matches.
- Verify title-only matches are LOW and never treated as an exact identity.
- Verify multiple candidates result in AMBIGUOUS, not arbitrary selection.
- Verify actions with desktop-wide targets (`TAKE_SCREENSHOT`, `LIST_WINDOWS`,
  `MOVE_MOUSE`) do not require a single application target.
- Verify `TYPE_TEXT` inherits only an explicit or task-established target and
  otherwise remains UNKNOWN.
- Verify a target mismatch prevents dispatch under the approved policy,
  marks the active step failed, skips later steps, and preserves prior
  results.
- Verify observer errors and no-window observations are distinct from
  mismatch and do not fabricate target identity.
- Verify matching foreground identity does not change `TYPE_TEXT` from
  `UNVERIFIED` or task `PARTIAL`.
- Verify target assessment and verification remain separate event fields.
- Verify preflight still validates the entire plan before any desktop action
  and that no window-activation API is called.

### Integration tests

- Launch Notepad and establish the association between the launched process
  and its visible window without relying solely on title text.
- With Notepad foreground, run a target-associated typing step and confirm
  the precondition passes while the typing outcome remains `UNVERIFIED`.
- Change foreground to Chrome before a Notepad-targeted typing step and
  confirm dispatch is withheld, later steps are skipped, and prior step
  results are retained.
- Exercise missing, replaced, or inaccessible target windows and confirm
  explicit unknown/ambiguous/error reporting without a focus change.
- Confirm task progress remains responsive and target metadata is displayed
  through Tk-safe polling.

### Manual validation tests

- Open Notepad, leave it foreground, and type a short test string; confirm
  target match reporting and final `PARTIAL` state.
- Open Notepad, switch to Chrome before the typing step, and confirm the
  agent reports the mismatch and does not type into Chrome.
- Open multiple Notepad windows and confirm ambiguity is reported or the
  task-established identity is used, rather than selecting by title order.
- Change a document title (for example by editing or renaming its content)
  and confirm identity does not depend on title alone.
- Confirm screenshots, window listing, and mouse movement continue to operate
  with desktop-wide targets and unchanged verifiers.

## 9. Incremental implementation plan

### Step 7B.1 — Target and assessment contracts

Define immutable target identity and assessment records, confidence/status
values, and per-action target semantics. Add pure unit tests for exact
identity, process-only match, title-only low confidence, unknown, ambiguous,
and desktop-wide/no-single-target actions. Do not gate or change dispatch in
this step.

**Independent completion criterion:** target assessments are deterministic
from supplied candidate windows and target records, with tests proving that
title-only matches cannot be treated as exact.

### Step 7B.2 — Task target association and mismatch precondition

Associate a target with a task after a target-producing action such as
`OPEN_NOTEPAD`, using process/window identity rather than title alone where
available. Before a target-directed action such as `TYPE_TEXT`, compare the
expected target to the current foreground snapshot. Under the approved
HIGH-/MEDIUM-confidence mismatch policy, withhold dispatch, fail the active
step as a precondition failure, skip later steps, and retain prior results.
Do not activate or focus windows.

**Independent completion criterion:** fake-observer and fake-executor tests
prove that a matching target dispatches normally, a known mismatch prevents
dispatch, and ambiguous/unknown identity is reported according to an
explicitly chosen safe policy.

### Step 7B.3 — Event and GUI reporting with integration validation

Add optional target assessment data to existing step events/results, render
expected target, observed foreground, confidence, and dispatch disposition in
the GUI using existing queue polling, then perform controlled Windows and
manual mismatch tests. Keep `VerificationResult` unchanged and confirm
`TYPE_TEXT` remains `UNVERIFIED`.

**Independent completion criterion:** progress output accurately explains
target match/mismatch decisions and existing task/verification behavior
passes regression and manual tests.

## 10. Recommendation

The smallest useful implementation slice is **Step 7B.1: pure target
assessment contracts and resolver tests**, using synthetic candidate windows
and the existing Step 7A snapshot shape. It adds measurable value by defining
exactly when identity is HIGH, MEDIUM, LOW, UNKNOWN, or ambiguous, prevents
unsafe title-only assumptions, and requires no changes to task execution,
verification, GUI behavior, or action schemas.

After the assessment rules are reviewed, implement Step 7B.2 as a separate
approved increment to bind launched applications to task targets and withhold
typing on a known mismatch. Then add event/GUI reporting and Windows
integration validation in Step 7B.3. This sequence minimizes risk while
preserving the existing architecture and avoids implying that target
awareness verifies typed content.
