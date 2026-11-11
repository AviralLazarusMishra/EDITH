from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ErrorInfo(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: dict[str, Any] | None = None


class TaskModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    task_type: str = Field(min_length=1)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_metadata: dict[str, Any] = Field(default_factory=dict)
    error_info: ErrorInfo | None = None

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("task_type must not be empty")
        return value

    def transition(
        self,
        new_status: TaskStatus,
        *,
        error_info: ErrorInfo | None = None,
    ) -> None:
        if not isinstance(new_status, TaskStatus):
            raise TypeError("new_status must be a TaskStatus")

        allowed_transitions = {
            TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.COMPLETED: set(),
            TaskStatus.FAILED: set(),
            TaskStatus.CANCELLED: set(),
        }
        if new_status not in allowed_transitions[self.status]:
            raise ValueError(f"Cannot transition task from {self.status} to {new_status}")
        if new_status == TaskStatus.FAILED and error_info is None:
            raise ValueError("Failed tasks require error_info")

        now = datetime.now(UTC)
        object.__setattr__(self, "status", new_status)
        if new_status == TaskStatus.RUNNING:
            object.__setattr__(self, "started_at", now)
        if new_status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            object.__setattr__(self, "completed_at", now)
        object.__setattr__(self, "error_info", error_info)
