from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from queue import Queue
from uuid import uuid4

if __package__:
    from .tools import validate_action
else:
    from tools import validate_action


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


def _utc_now():
    return datetime.now(timezone.utc)


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
        task.result.append(outcome)
        if not outcome["ok"]:
            step.error = str(outcome.get("error", "Action execution failed"))
            transition_step_state(step, StepState.FAILED)
            emit(TaskEventType.STEP_FAILED, step=step, index=index, result=outcome, error=step.error)
            for pending_step in task.steps[index + 1:]:
                transition_step_state(pending_step, StepState.SKIPPED)
            task.error = f"Step {index + 1} ({step.action}) failed: {step.error}"
            transition_task_state(task, TaskState.FAILED)
            emit(TaskEventType.TASK_FAILED, step=step, index=index, error=task.error)
            return task

        transition_step_state(step, StepState.SUCCEEDED)
        emit(TaskEventType.STEP_COMPLETED, step=step, index=index, result=outcome)

    transition_task_state(task, TaskState.SUCCEEDED)
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
