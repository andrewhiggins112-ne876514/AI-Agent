# Phase 3 Step 7 Options

## Context

Phase 3 currently has task and step models, whole-plan preflight validation,
sequential fail-stop execution, registry-based verification, and GUI progress
reporting through a worker thread and Tk-safe queue polling. Manual validation
has confirmed:

- `OPEN_NOTEPAD` and `TAKE_SCREENSHOT` can be verified.
- `TYPE_TEXT` is honestly reported as `UNVERIFIED`, making the task
  `PARTIAL`.
- Invalid input is rejected before execution.

The task runner has no retry or cancellation behavior yet. The approved design
specifies that cancellation is cooperative at step boundaries, retries should
be bounded and action-aware, and UI updates must remain on Tk's main thread.
The project vision and roadmap identify better application/window handling as
a practical expansion of the existing desktop automation foundation.

Effort estimates below are for a narrowly scoped implementation and focused
tests, excluding unplanned UI redesign.

## Option 1: Window / Focus Awareness

### Purpose

Observe which windows are visible and which window is foreground, and use that
information to make actions more context-aware. For example, the engine could
report the active window before typing, detect that the intended application
is not focused, or verify that a requested application became active.

### User value

Reduces the chance that typing is sent to the wrong application and gives the
user useful context when an action runs against unexpected desktop state. It
also creates a foundation for later application switching and more reliable
verification.

### Architectural impact

- Extend the existing Windows observation helpers in `scripts/tools.py` with
  narrowly scoped foreground-window information.
- Define how task steps express an expected target window, if needed; avoid
  adding a generic workflow or planner layer.
- Integrate the observation with the existing sequential runner and
  verification registry.
- Report observed window/focus context using the existing task events and GUI
  progress display.

### Verification impact

This is the strongest option for improving the quality and relevance of
verification. It can confirm focus or foreground-window state, and can expose
when a typing step may have targeted the wrong window. It does not by itself
prove that typed text appeared; `TYPE_TEXT` should remain `UNVERIFIED` unless
a deterministic content read-back is separately designed and implemented.

### Complexity

Medium. Windows exposes foreground-window information, but target matching,
timing, changing focus, and user interaction during a task require careful
semantics. The feature should begin as observation and explicit reporting,
not silently taking focus away from the user.

### Risks

- Window titles are not stable identifiers and may be localized or duplicated.
- Focus can change between observation and action.
- Automatically activating a window could disrupt the user's current work.
- A focus observation can improve confidence but should not be presented as
  proof that text entry succeeded.

### Dependencies

- Existing Windows window-listing helpers and action verifier registry.
- The current task event model and GUI progress display.
- A clear policy for whether the engine only observes focus or may activate a
  window. The safer initial scope is observation only.

### Testing requirements

- Unit-test foreground-window result normalization and verifier decisions
  using mocked Windows APIs.
- Test missing, unknown, and mismatched foreground windows.
- Test that focus observations do not invoke desktop-changing operations.
- Test that UI reporting displays focus evidence without claiming text
  content was verified.
- Run controlled Windows integration tests with multiple visible windows and
  user focus changes.

### Estimated implementation effort

Approximately 1–2 development days for a focused observation/reporting
increment, including tests and controlled manual validation. Automatic focus
switching or target-window-aware typing would add scope and effort.

## Option 2: Retry Policy

### Purpose

Allow a narrowly bounded retry after a known transient failure when repeating
the action is safe and the previous attempt is known not to have caused its
side effect.

### User value

Can recover from intermittent failures without requiring the user to submit
the task again. It is most useful for read-only or explicitly repeatable
actions with observable failure conditions.

### Architectural impact

- Add an explicit retry decision/policy to the task runner.
- Record attempt number and each attempt's outcome.
- Emit progress updates for retry attempts.
- Preserve fail-stop behavior when retries are unavailable, exhausted, or
  unsafe.
- Keep retry policy action-specific rather than applying blanket retries.

### Verification impact

Retries can improve completion rates when the failure is transient, but they
do not improve the underlying evidence that an action achieved its goal.
Verification failures must not automatically trigger another side effect
unless the policy can establish that repetition is safe.

### Complexity

Medium. The loop itself is simple; reliably classifying failures, actions,
and side-effect uncertainty is the difficult part. Attempt history and
progress-event semantics also need definition.

### Risks

- Repeating `TYPE_TEXT` can duplicate content.
- Repeating `OPEN_NOTEPAD` can open duplicate windows.
- Repeating screenshot capture may overwrite an existing file.
- A timeout or exception does not always prove that the action did not take
  effect.
- Incorrect retry classification can turn a recoverable failure into an
  unintended repeated action.

### Dependencies

- Existing task and step state transitions, result records, and event queue.
- A documented per-action repeat-safety policy.
- Reliable distinction between invocation failures and verification failures.
- Verification must remain separate from invocation success; retries must not
  weaken that distinction.

### Testing requirements

- Test retry caps and exact attempt counts.
- Test that only explicitly safe transient failures can retry.
- Confirm `OPEN_NOTEPAD` and `TYPE_TEXT` are not retried automatically.
- Confirm no retry on validation errors or unsafe/ambiguous outcomes.
- Verify attempt history and event ordering in both exhausted and recovered
  cases.
- Use fake tools; do not cause real repeated desktop side effects in unit
  tests.

### Estimated implementation effort

Approximately 1–2 development days for one explicitly safe retry candidate,
attempt recording, progress events, and focused tests. A broader action policy
would take longer and require more evidence about tool failure semantics.

## Option 3: Cancellation

### Purpose

Let the user request that a running task stop at a safe boundary. The active
desktop call is allowed to finish; pending steps are then skipped and the
task is marked `CANCELLED`.

### User value

Gives users control over long or no-longer-wanted multi-step tasks and
prevents later actions from running after cancellation is requested.

### Architectural impact

- Add a thread-safe cancellation signal checked by the runner between steps.
- Implement legal transitions into `CANCELLED` and mark remaining steps
  `SKIPPED`.
- Emit an explicit cancellation event or define how existing task/step events
  represent the cancellation boundary.
- Add a GUI cancel control and keep all widget changes on the Tk main thread.
- Define behavior for cancellation during preflight, verification, and an
  active tool call.

### Verification impact

Cancellation does not make a completed action more verifiable. It improves
control over what happens next. The engine must preserve verification results
for completed steps and must not imply that an in-flight action was
interrupted or rolled back.

### Complexity

Medium to high across the full UI-to-runner flow. Cooperative checking is
straightforward, but state transitions, event ordering, and honest reporting
around an in-flight blocking desktop call need careful treatment.

### Risks

- Users may expect immediate interruption, which the current desktop tools
  cannot guarantee.
- A tool call may complete after cancellation was requested.
- Incorrectly marking an active step skipped or cancelled could conceal a
  side effect that occurred.
- A cancel control can be misleading unless the UI explains that cancellation
  takes effect between actions.

### Dependencies

- The existing `CANCELLED` task state and terminal-state model.
- A thread-safe cancellation signal shared by GUI and worker.
- Defined cancellation boundaries and event semantics.
- Tk-safe queue polling and task progress UI.

### Testing requirements

- Test cancellation before execution, between steps, and while a fake tool is
  blocked.
- Confirm the active tool is not falsely reported as interrupted.
- Confirm remaining pending steps become `SKIPPED`.
- Confirm final state and events are `CANCELLED` and completed steps retain
  their results.
- Test the cancel control's enable/disable lifecycle and main-thread-only UI
  updates.
- Perform controlled Windows integration checks with a deliberately slow
  action.

### Estimated implementation effort

Approximately 2–3 development days for cooperative runner behavior, event
semantics, GUI control, and focused tests. More if existing blocking tools
need bounded waits or interruption support.

## Rankings

### Lowest risk

1. **Window / Focus Awareness** — if initially limited to read-only
   observation and reporting; it avoids repeating actions or changing task
   outcomes.
2. **Cancellation** — can be safe when strictly cooperative, but users may
   misunderstand the boundary around an active call.
3. **Retry Policy** — incorrect repeat-safety assumptions can duplicate
   side effects.

### Highest user value

1. **Window / Focus Awareness** — directly addresses whether desktop actions
   target the intended application and makes progress more informative.
2. **Cancellation** — gives users control over unwanted future steps.
3. **Retry Policy** — helps only for a limited set of safe transient failures.

### Best alignment with the current architecture

1. **Window / Focus Awareness** — extends existing Windows observations,
   registered verifiers, task events, and GUI reporting without changing the
   sequential lifecycle.
2. **Retry Policy** — fits the existing runner and event model, but requires
   new attempt semantics and action-specific policy.
3. **Cancellation** — supported conceptually by the `CANCELLED` state and
   design, but needs coordination across GUI controls, worker thread, task
   transitions, and event handling.

### Biggest improvement to verification quality

1. **Window / Focus Awareness** — adds observable evidence about desktop
   context and can identify focus mismatches before or after actions.
2. **Retry Policy** — may recover from failures but does not inherently
   establish that an outcome occurred.
3. **Cancellation** — improves user control, not outcome evidence.

## Recommendation

Implement **Window / Focus Awareness** as the next Phase 3 step, beginning
with read-only foreground-window observation and explicit progress or
verification evidence. This has the best combination of low risk, user value,
fit with the current verifier/event architecture, and improvement to
verification quality. It is especially relevant to `TYPE_TEXT`, where the
current system can report dispatch as unverified but cannot establish whether
the intended application was active.

Keep the initial change conservative: do not automatically steal focus, do not
claim that observing the foreground window verifies typed content, and retain
the existing `VERIFIED` / `UNVERIFIED` / `FAILED` semantics. After this
observation path is tested, reassess whether bounded retry policy or
cooperative cancellation should follow.
