from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


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


def _utc_now():
    return datetime.now(timezone.utc)


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
