from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
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
