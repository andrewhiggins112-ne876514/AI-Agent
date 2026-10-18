# Phase 3 Design: Task Execution Engine

## Purpose and scope

Phase 3 will make the existing validated action list dependable as a task. It
will introduce task and step state, ordered execution, verification, bounded
failure handling, and progress reporting.

The language model remains responsible for proposing ordered actions. Phase 3
will execute and track that action list; it will not introduce a separate
planning model or a general workflow/DAG framework.

## 1. Current architecture review

The current GUI flow in `scripts/agent_ui.py` is:

1. A user enters a request in Tkinter.
2. The GUI constructs a prompt and sends it to Ollama's local
   `/api/generate` endpoint in JSON mode.
3. A worker thread makes the request with a timeout and places its result in a
   thread-safe queue.
4. Tkinter polls the queue on its main thread.
5. The parser in `scripts/tools.py` normalizes the model response to an action
   list.
6. The GUI currently loops through the actions and invokes `execute_action`.
7. Results are displayed in the GUI.

`scripts/tools.py` currently combines desktop tool functions, the tool
registry, parameter validation, response parsing, and action invocation.

The current flow has no task or per-step lifecycle, no complete-list preflight
before side effects, no explicit stop/skip semantics after a failure, and no
postcondition verification. Action invocation currently occurs inside the
Tkinter response-handling path, so a blocking tool call can pause UI event
processing. A tool function returning without raising is not necessarily
proof that the intended desktop outcome occurred.

## 2. Proposed architecture

```text
Tkinter UI
  ├─ accepts one request at a time
  ├─ displays task and step progress
  └─ polls task event queue using root.after
          ↓
Existing Ollama API request
          ↓
Existing parser → normalized ordered action list
          ↓
Whole-list preflight validation
          ↓
Task Execution Engine
  ├─ owns task and step lifecycle
  ├─ executes one action at a time
  ├─ verifies observable outcomes
  ├─ applies action-aware retry policy
  └─ emits immutable progress/result events
          ↓
Existing desktop tools → Windows
```

The task runner should process a single task sequentially. It should not run
steps in parallel. The runner should be dependency-injected with action
execution, verification, retry policy, and event publication dependencies so
unit tests can use fakes without manipulating the live desktop.

## 3. Task state model

### Task states

- `RECEIVED`: request and normalized plan have been associated with a task.
- `VALIDATING`: all proposed actions are being checked before any side effect.
- `READY`: all actions passed preflight and the task can execute.
- `RUNNING`: the task is executing or verifying a step.
- `SUCCEEDED`: required steps completed and met the declared completion
  policy.
- `PARTIAL`: some work occurred, but at least one required outcome remains
  unverified or incomplete.
- `FAILED`: execution could not complete because of an invalid plan, tool
  failure, or verification failure.
- `CANCELLED`: cancellation was requested and honored at a safe boundary.

`SUCCEEDED`, `PARTIAL`, `FAILED`, and `CANCELLED` are terminal states. A
terminal task cannot transition back to an active state.

### Step states

- `PENDING`: not yet started.
- `RUNNING`: tool invocation or verification is in progress.
- `SUCCEEDED`: the action completed and its required outcome was verified.
- `UNVERIFIED`: the tool call completed, but the outcome cannot be proven with
  the available observation.
- `FAILED`: invocation or required verification failed.
- `SKIPPED`: the step did not run because an earlier required step failed or
  the task was cancelled.

Each task should retain a task identifier, original request, ordered steps,
current step index, lifecycle timestamps, and final result. Each step should
retain action and parameters, state, attempt count, tool result, verification
status/evidence, timestamps, and error details.

### State invariants

- Preflight validates the entire action list before any tool runs. An invalid
  action later in the list must not allow earlier side effects.
- At most one step is `RUNNING` within a task.
- Steps begin in their original plan order.
- A later step does not start until the current step has a terminal step
  outcome.
- A task is not reported `SUCCEEDED` when a required step is failed or
  unverified.
- Remaining pending steps are marked `SKIPPED` when the task stops early.

## 4. Execution verification model

Verification should be deterministic and based on observable postconditions.
Use a verifier contract that returns:

- `VERIFIED`: evidence confirms the expected outcome.
- `UNVERIFIED`: the tool call completed, but the available mechanisms cannot
  confirm the result.
- `FAILED`: the expected outcome was checked and did not occur, or a required
  check itself failed.

The result should include concise evidence or an explanation. Tool invocation
success and outcome verification must remain distinct in both internal state
and GUI reporting.

Initial verifier candidates for the existing tools:

| Action | Initial verification |
| --- | --- |
| `OPEN_NOTEPAD` | Wait for a bounded interval for a visible Notepad window and verify its presence. |
| `TAKE_SCREENSHOT` | Verify the screenshot output exists and is non-empty; prefer the tool's returned path over duplicating a hard-coded path. |
| `MOVE_MOUSE` | Compare the observed pointer position to the requested absolute coordinates or the tool's effective default target. |
| `LIST_WINDOWS` | Verify the result is a list; the returned list is the requested output. |
| `TYPE_TEXT` | Current typing behavior has no reliable read-back. Report `UNVERIFIED` unless a deterministic read-back mechanism is available. Do not treat a successful function return as proof the text appeared. |

The initial phase should not claim that content was verified merely because
`pyautogui.write` returned. It may report that typing was dispatched, while
keeping the outcome explicitly unverified.

## 5. Failure handling

### Preflight failures

Reject the whole task before execution if any action has an unknown name,
missing or unexpected parameters, or invalid parameter types/values. Report
the invalid step and leave every tool uncalled.

### Invocation and verification failures

- Mark the active step `FAILED` with its error and attempt details.
- By default, stop the task and mark later pending steps `SKIPPED`.
- Do not continue to dependent actions after a failed prerequisite.
- Preserve completed work in the task result; do not imply that a stopped task
  was rolled back.
- Distinguish tool exceptions, verification failures, timeouts, and
  unverified outcomes in the result and GUI.

### Cancellation

Cancellation is cooperative between steps. If requested while a tool is
running, finish or wait for that call and honor cancellation at the next safe
boundary. Do not claim an in-flight desktop action can be interrupted unless
the tool explicitly supports interruption.

## 6. Retry strategy

Use a bounded, explicit, action-aware retry policy. The initial default is no
automatic retry. Permit at most one retry only when:

1. the failure is transient,
2. the action is explicitly marked safe to repeat, and
3. evidence indicates the previous attempt did not already cause the side
   effect.

Action considerations:

- `LIST_WINDOWS` is read-only and is a candidate for a safe transient retry.
- Absolute `MOVE_MOUSE` is repeatable, but retry only when the previous call
  did not complete.
- `OPEN_NOTEPAD` may create duplicate windows; do not retry automatically.
- `TYPE_TEXT` may duplicate content; do not retry automatically.
- `TAKE_SCREENSHOT` may overwrite the same output. Establish and document its
  overwrite semantics before classifying retries as safe.

Record each attempt and its outcome. Do not use blanket retries or retry
verification failures if doing so could repeat a non-idempotent action.

## 7. Progress reporting

The engine should publish immutable task/step events through a thread-safe
queue. Suggested event data includes task ID, step index/count, state, action
name, attempt number, short message, and optional result/error/verification
details.

The task runner must not access Tkinter widgets. The Tk main thread should
poll events using `root.after` and perform all UI updates itself.

The GUI should show:

- task state and current step, such as “Running step 2 of 3: TYPE_TEXT”
- completed, pending, failed, skipped, and unverified step outcomes
- retry attempt when applicable
- verification result and evidence summary
- final task state: succeeded, partial, failed, or cancelled

Keep single-task submission guarded so two tasks cannot manipulate the
desktop concurrently. A cancel control may request cooperative cancellation;
it must not claim immediate interruption of an active tool call.

## 8. Required file changes

Keep the current `scripts/` layout; do not reorganize folders.

- `scripts/task_execution.py` (new): task and step models/states, full-list
  preflight orchestration, sequential runner, verifier contract, bounded retry
  policy, cooperative cancellation boundary, and task event definitions.
- `scripts/tools.py`: expose pure action validation separately from tool
  invocation and provide narrowly scoped observations needed by deterministic
  verifiers. Preserve action names and existing public tool behavior.
- `scripts/agent_ui.py`: submit the parsed action list to the task runner,
  consume task events on Tk's thread, render step progress and final status,
  and prevent overlapping tasks.
- `tests/test_task_execution.py` (new): test the task runner using fake tool
  and verifier dependencies. Use existing test conventions if present; do not
  add a test framework dependency without need.
- `tests/test_tools.py` (optional): add only if validation is refactored and
  needs focused regression coverage.

## 9. Risks

- Verification capability differs by action. Typing cannot currently be
  confirmed reliably; the UI must report `UNVERIFIED` rather than overstate
  success.
- Retrying non-idempotent actions can duplicate windows or text. Retries must
  be opt-in per action and bounded.
- Desktop state and focus can change during a task because of user activity or
  application startup timing. Use bounded waits and explicit failures.
- Tkinter is not thread-safe. All widget updates must be marshalled through
  the main-thread polling callback.
- Existing tools contain blocking OS calls and sleeps. Cancellation is
  cooperative and cannot guarantee interruption of an active action.
- Live GUI automation can be flaky. Keep most task-engine tests independent
  of Windows side effects.

## 10. Testing strategy

### Unit tests

- Verify all task/step states, valid transitions, invalid transitions, and
  terminal-state invariants.
- Verify whole-list preflight prevents all invocations if any action is
  invalid.
- Use fake tools to assert exact sequential order and that a later step cannot
  start before the current step has a terminal outcome.
- Test `VERIFIED`, `UNVERIFIED`, and `FAILED` outcomes and their effect on task
  completion.
- Test fail-stop behavior, skipped remaining steps, and cooperative
  cancellation between steps.
- Test retry caps and action policy: safe transient cases may retry once;
  `TYPE_TEXT` and `OPEN_NOTEPAD` do not automatically retry.
- Test attempt records, event ordering, and task summaries.
- Verify UI event handling is marshalled through Tk's polling callback rather
  than worker-thread widget access.

### Windows integration tests

- Open Notepad and verify its visible window.
- Open Notepad then type text; report the typing outcome honestly as
  unverified unless a valid read-back check exists.
- Capture a screenshot and verify the output file.
- Introduce a controlled tool failure and confirm later actions are skipped.
- Confirm progress, final state, cancellation boundaries, and UI
  responsiveness during a task.

## 11. Incremental implementation plan

1. **Agree on contracts:** finalize task/step records, state transitions,
   events, verification results, and what counts as task success. In
   particular, typing without read-back is `UNVERIFIED`.
2. **Add state model and preflight:** validate the complete action list before
   any tool invocation; add unit tests for state invariants and no-side-effect
   rejection.
3. **Add sequential runner:** execute one step at a time with progress events,
   fail-stop behavior, skipped-step recording, and no automatic retry at
   first.
4. **Add verification and conservative retries:** implement deterministic
   checks, then only safe bounded retry cases with tests.
5. **Integrate the GUI:** run task execution off the Tk event thread, poll
   events on the main thread, show step progress/final status, and guard
   against concurrent tasks.
6. **Validate end-to-end:** run focused unit tests first, then controlled
   Windows integration tests for successful, failed, unverified, and
   cancelled tasks.

Phase 3 implementation must not begin until this design document has been
reviewed and approved.
