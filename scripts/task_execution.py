from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from queue import Queue
import time
from uuid import uuid4

if __package__:
    from . import tools
else:
    import tools


validate_action = tools.validate_action


class PlanValidationError(ValueError):
    def __init__(self, step_index, message):
        self.step_index = step_index
        super().__init__(f"Invalid action at step {step_index + 1}: {message}")


class TaskState(str, Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskEventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    evidence: str


@dataclass(frozen=True)
class TaskEvent:
    event_type: TaskEventType
    task_id: str
    occurred_at: datetime = field(default_factory=lambda: _utc_now())
    step_id: str | None = None
    step_index: int | None = None
    step_count: int | None = None
    action: str | None = None
    result: object | None = None
    error: str | None = None
    task_state: TaskState | None = None
    step_state: StepState | None = None
    verification_result: VerificationResult | None = None


TASK_STATE_TRANSITIONS = {
    TaskState.RECEIVED: {TaskState.VALIDATING, TaskState.FAILED},
    TaskState.VALIDATING: {TaskState.READY, TaskState.FAILED},
    TaskState.READY: {TaskState.RUNNING, TaskState.FAILED},
    TaskState.RUNNING: {
        TaskState.SUCCEEDED,
        TaskState.PARTIAL,
        TaskState.FAILED,
    },
    TaskState.SUCCEEDED: set(),
    TaskState.PARTIAL: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}

STEP_STATE_TRANSITIONS = {
    StepState.PENDING: {StepState.RUNNING, StepState.SKIPPED},
    StepState.RUNNING: {
        StepState.SUCCEEDED,
        StepState.UNVERIFIED,
        StepState.FAILED,
    },
    StepState.SUCCEEDED: set(),
    StepState.UNVERIFIED: set(),
    StepState.FAILED: set(),
    StepState.SKIPPED: set(),
}

SCREENSHOT_PATH = Path(r"D:\AI-Agent\logs\screenshot.png")
NOTEPAD_VERIFY_TIMEOUT_SECONDS = 2.0
NOTEPAD_VERIFY_POLL_INTERVAL_SECONDS = 0.1


def _utc_now():
    return datetime.now(timezone.utc)


def _execution_value(execution_result):
    if isinstance(execution_result, dict) and isinstance(
        execution_result.get("ok"), bool
    ):
        if not execution_result["ok"]:
            return None, VerificationResult(
                VerificationStatus.FAILED,
                str(execution_result.get("error", "Action execution failed")),
            )
        return execution_result.get("result"), None
    return execution_result, None


def _verify_open_notepad(action, execution_result):
    _, execution_failure = _execution_value(execution_result)
    if execution_failure:
        return execution_failure

    deadline = time.monotonic() + NOTEPAD_VERIFY_TIMEOUT_SECONDS
    while True:
        titles = tools.get_windows()
        matching_title = next(
            (title for title in titles if "notepad" in title.casefold()),
            None,
        )
        if matching_title:
            return VerificationResult(
                VerificationStatus.VERIFIED,
                f"Visible Notepad window found: {matching_title}",
            )
        if time.monotonic() >= deadline:
            return VerificationResult(
                VerificationStatus.FAILED,
                "No visible Notepad window found before the verification timeout",
            )
        time.sleep(NOTEPAD_VERIFY_POLL_INTERVAL_SECONDS)


def _verify_screenshot(action, execution_result):
    tool_result, execution_failure = _execution_value(execution_result)
    if execution_failure:
        return execution_failure

    screenshot_path = SCREENSHOT_PATH
    if isinstance(tool_result, Path):
        screenshot_path = tool_result
    elif isinstance(tool_result, str):
        reported_path = Path(tool_result)
        if reported_path.suffix or "\\" in tool_result or "/" in tool_result:
            screenshot_path = reported_path

    try:
        size = screenshot_path.stat().st_size
    except OSError as error:
        return VerificationResult(
            VerificationStatus.FAILED,
            f"Screenshot output could not be inspected: {error}",
        )
    if size <= 0:
        return VerificationResult(
            VerificationStatus.FAILED,
            f"Screenshot output is empty: {screenshot_path}",
        )
    return VerificationResult(
        VerificationStatus.VERIFIED,
        f"Screenshot exists and is non-empty ({size} bytes): {screenshot_path}",
    )


def _verify_list_windows(action, execution_result):
    tool_result, execution_failure = _execution_value(execution_result)
    if execution_failure:
        return execution_failure
    if not isinstance(tool_result, list) or any(
        not isinstance(title, str) for title in tool_result
    ):
        return VerificationResult(
            VerificationStatus.FAILED,
            "LIST_WINDOWS did not return a list of window titles",
        )
    return VerificationResult(
        VerificationStatus.VERIFIED,
        f"Received {len(tool_result)} visible window title(s)",
    )


def _verify_move_mouse(action, execution_result):
    _, execution_failure = _execution_value(execution_result)
    if execution_failure:
        return execution_failure

    params = action.get("params", {}) if isinstance(action, dict) else {}
    expected_position = (params.get("x", 500), params.get("y", 500))
    try:
        actual_position = tuple(tools.pyautogui.position())
    except (OSError, tools.pyautogui.FailSafeException) as error:
        return VerificationResult(
            VerificationStatus.FAILED,
            f"Could not inspect mouse position: {error}",
        )

    if actual_position != expected_position:
        return VerificationResult(
            VerificationStatus.FAILED,
            f"Mouse is at {actual_position}; expected {expected_position}",
        )
    return VerificationResult(
        VerificationStatus.VERIFIED,
        f"Mouse is at expected position {expected_position}",
    )


def _verify_type_text(action, execution_result):
    _, execution_failure = _execution_value(execution_result)
    if execution_failure:
        return execution_failure
    return VerificationResult(
        VerificationStatus.UNVERIFIED,
        "Typing was dispatched, but the entered text cannot be read back reliably",
    )


VERIFIER_REGISTRY = {
    "OPEN_NOTEPAD": _verify_open_notepad,
    "TAKE_SCREENSHOT": _verify_screenshot,
    "LIST_WINDOWS": _verify_list_windows,
    "MOVE_MOUSE": _verify_move_mouse,
    "TYPE_TEXT": _verify_type_text,
}


def verify_action(action, execution_result):
    """Look up and run the verifier registered for an action."""
    if not isinstance(action, dict) or not isinstance(action.get("action"), str):
        raise ValueError("Action must be an object with a string 'action' field")
    try:
        verifier = VERIFIER_REGISTRY[action["action"]]
    except KeyError as error:
        raise ValueError(
            f"No verifier registered for action: {action['action']}"
        ) from error
    return verifier(action, execution_result)


def preflight_actions(actions):
    """Validate an entire action list without invoking any tools."""
    if not isinstance(actions, list):
        raise ValueError("Action plan must be a list")

    for index, action in enumerate(actions):
        try:
            validate_action(action)
        except ValueError as error:
            raise PlanValidationError(index, str(error)) from error


def transition_task_state(task, new_state):
    """Apply a legal task state transition or raise ValueError."""
    if not isinstance(new_state, TaskState):
        raise ValueError(f"Invalid task state: {new_state}")
    if new_state not in TASK_STATE_TRANSITIONS[task.state]:
        raise ValueError(
            f"Illegal task state transition: {task.state.value} -> {new_state.value}"
        )

    now = _utc_now()
    task.state = new_state
    if new_state is TaskState.RUNNING and task.started_at is None:
        task.started_at = now
    if new_state in {
        TaskState.SUCCEEDED,
        TaskState.PARTIAL,
        TaskState.FAILED,
        TaskState.CANCELLED,
    }:
        task.finished_at = now


def transition_step_state(step, new_state):
    """Apply a legal step state transition or raise ValueError."""
    if not isinstance(new_state, StepState):
        raise ValueError(f"Invalid step state: {new_state}")
    if new_state not in STEP_STATE_TRANSITIONS[step.state]:
        raise ValueError(
            f"Illegal step state transition: {step.state.value} -> {new_state.value}"
        )

    now = _utc_now()
    step.state = new_state
    if new_state is StepState.RUNNING and step.started_at is None:
        step.started_at = now
    if new_state in {
        StepState.SUCCEEDED,
        StepState.UNVERIFIED,
        StepState.FAILED,
        StepState.SKIPPED,
    }:
        step.finished_at = now


def run_task(task, events, action_executor=None):
    """Preflight and execute all task steps sequentially, stopping on failure."""
    if task.state is not TaskState.RECEIVED:
        raise ValueError("Task must be in RECEIVED state before it can run")
    if any(step.state is not StepState.PENDING for step in task.steps):
        raise ValueError("All task steps must be PENDING before the task can run")
    if not hasattr(events, "put"):
        raise TypeError("events must provide a put(event) method")

    if action_executor is None:
        if __package__:
            from .tools import execute_action
        else:
            from tools import execute_action
        action_executor = execute_action

    def emit(event_type, step=None, index=None, result=None, error=None):
        events.put(TaskEvent(
            event_type=event_type,
            task_id=task.task_id,
            step_id=step.step_id if step else None,
            step_index=index,
            step_count=len(task.steps),
            action=step.action if step else None,
            result=result,
            error=error,
            task_state=task.state,
            step_state=step.state if step else None,
            verification_result=step.verification_result if step else None,
        ))

    transition_task_state(task, TaskState.VALIDATING)
    emit(TaskEventType.TASK_STARTED)

    actions = [
        {"action": step.action, "params": step.params}
        for step in task.steps
    ]
    try:
        preflight_actions(actions)
    except (PlanValidationError, ValueError) as error:
        task.error = str(error)
        transition_task_state(task, TaskState.FAILED)
        emit(TaskEventType.TASK_FAILED, error=task.error)
        return task

    transition_task_state(task, TaskState.READY)
    transition_task_state(task, TaskState.RUNNING)
    task.result = []

    for index, step in enumerate(task.steps):
        task.current_step_index = index
        transition_step_state(step, StepState.RUNNING)
        step.attempt_count += 1
        emit(TaskEventType.STEP_STARTED, step=step, index=index)

        action = {"action": step.action, "params": step.params}
        try:
            outcome = action_executor(action)
            if not isinstance(outcome, dict) or not isinstance(outcome.get("ok"), bool):
                raise ValueError("Action executor must return a structured result with boolean 'ok'")
        except Exception as error:
            step.error = str(error)
            transition_step_state(step, StepState.FAILED)
            task.result.append({
                "action": step.action,
                "ok": False,
                "error": step.error,
            })
            emit(TaskEventType.STEP_FAILED, step=step, index=index, error=step.error)
            for pending_step in task.steps[index + 1:]:
                transition_step_state(pending_step, StepState.SKIPPED)
            task.error = f"Step {index + 1} ({step.action}) failed: {step.error}"
            transition_task_state(task, TaskState.FAILED)
            emit(TaskEventType.TASK_FAILED, step=step, index=index, error=task.error)
            return task

        step.tool_result = outcome
        if not outcome["ok"]:
            step.error = str(outcome.get("error", "Action execution failed"))
            step.verification_result = VerificationResult(
                VerificationStatus.FAILED,
                step.error,
            )
            task.result.append({
                "action": step.action,
                "execution": outcome,
                "verification": step.verification_result,
            })
            transition_step_state(step, StepState.FAILED)
            emit(
                TaskEventType.STEP_FAILED,
                step=step,
                index=index,
                result=task.result[-1],
                error=step.error,
            )
            for pending_step in task.steps[index + 1:]:
                transition_step_state(pending_step, StepState.SKIPPED)
            task.error = f"Step {index + 1} ({step.action}) failed: {step.error}"
            transition_task_state(task, TaskState.FAILED)
            emit(TaskEventType.TASK_FAILED, step=step, index=index, error=task.error)
            return task

        try:
            verification = verify_action(action, outcome)
            if not isinstance(verification, VerificationResult):
                raise TypeError(
                    "Action verifier must return a VerificationResult"
                )
            if not isinstance(verification.status, VerificationStatus):
                raise TypeError(
                    "VerificationResult status must be a VerificationStatus"
                )
            if not isinstance(verification.evidence, str):
                raise TypeError("VerificationResult evidence must be a string")
        except Exception as error:
            verification = VerificationResult(
                VerificationStatus.FAILED,
                f"Verifier raised {type(error).__name__}: {error}",
            )
        step.verification_result = verification
        step_outcome = {
            "action": step.action,
            "execution": outcome,
            "verification": verification,
        }
        task.result.append(step_outcome)

        if verification.status is VerificationStatus.FAILED:
            step.error = verification.evidence
            transition_step_state(step, StepState.FAILED)
            emit(
                TaskEventType.STEP_FAILED,
                step=step,
                index=index,
                result=step_outcome,
                error=step.error,
            )
            for pending_step in task.steps[index + 1:]:
                transition_step_state(pending_step, StepState.SKIPPED)
            task.error = (
                f"Step {index + 1} ({step.action}) verification failed: "
                f"{step.error}"
            )
            transition_task_state(task, TaskState.FAILED)
            emit(
                TaskEventType.TASK_FAILED,
                step=step,
                index=index,
                error=task.error,
            )
            return task

        if verification.status is VerificationStatus.VERIFIED:
            transition_step_state(step, StepState.SUCCEEDED)
        else:
            transition_step_state(step, StepState.UNVERIFIED)
        emit(
            TaskEventType.STEP_COMPLETED,
            step=step,
            index=index,
            result=step_outcome,
        )

    final_state = (
        TaskState.PARTIAL
        if any(step.state is StepState.UNVERIFIED for step in task.steps)
        else TaskState.SUCCEEDED
    )
    transition_task_state(task, final_state)
    emit(TaskEventType.TASK_COMPLETED, result=task.result)
    return task


@dataclass
class TaskStep:
    action: str
    params: dict[str, object]
    step_id: str = field(default_factory=lambda: uuid4().hex)
    state: StepState = StepState.PENDING
    attempt_count: int = 0
    tool_result: object | None = None
    verification_result: VerificationResult | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class Task:
    request: str
    steps: list[TaskStep]
    task_id: str = field(default_factory=lambda: uuid4().hex)
    state: TaskState = TaskState.RECEIVED
    current_step_index: int | None = None
    result: object | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
