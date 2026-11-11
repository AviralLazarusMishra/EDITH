from datetime import datetime
from enum import StrEnum
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.models.execution_result import ExecutionResult
from app.core.models.request import RequestModel
from app.core.models.task import ErrorInfo, TaskModel, TaskStatus


class OtherStatus(StrEnum):
    RUNNING = "RUNNING"


def test_request_validation_and_unique_ids():
    first = RequestModel(user_input="  scan host  ", source="cli")
    second = RequestModel(user_input="whois host", source="cli")

    assert first.request_id != second.request_id
    assert first.user_input == "  scan host  "
    assert first.timestamp.tzinfo is not None
    with pytest.raises(ValidationError):
        RequestModel(user_input="  ", source="cli")
    with pytest.raises(ValidationError):
        RequestModel(user_input="scan host", source=" ")
    with pytest.raises(ValidationError):
        RequestModel(user_input="scan host", source="cli", metadata=["not", "a", "mapping"])
    with pytest.raises(ValidationError):
        RequestModel(
            user_input="scan host",
            source="cli",
            timestamp=datetime.fromisoformat("2026-01-01T12:00:00"),
        )


def test_task_lifecycle_and_timestamps():
    task = TaskModel(request_id=uuid4(), task_type="user_request")
    other_task = TaskModel(request_id=task.request_id, task_type="user_request")

    assert task.task_id != other_task.task_id
    task.transition(TaskStatus.RUNNING)
    assert task.started_at is not None
    assert task.status is TaskStatus.RUNNING
    task.transition(TaskStatus.COMPLETED)
    assert task.completed_at is not None
    assert task.status is TaskStatus.COMPLETED


def test_task_status_cannot_be_assigned_without_transition():
    task = TaskModel(request_id=uuid4(), task_type="user_request")

    with pytest.raises(ValidationError):
        task.status = TaskStatus.COMPLETED
    task.transition(TaskStatus.RUNNING)
    with pytest.raises(ValueError, match="require error_info"):
        task.transition(TaskStatus.FAILED)


def test_task_transition_rejects_plain_string_and_invalid_enum():
    task = TaskModel(request_id=uuid4(), task_type="user_request")

    with pytest.raises(TypeError, match="TaskStatus"):
        task.transition("RUNNING")
    with pytest.raises(TypeError, match="TaskStatus"):
        task.transition(object())
    with pytest.raises(TypeError, match="TaskStatus"):
        task.transition(OtherStatus.RUNNING)

    task.transition(TaskStatus.RUNNING)
    assert task.status is TaskStatus.RUNNING


def test_task_failure_transition_preserves_enum_status_and_error():
    task = TaskModel(request_id=uuid4(), task_type="user_request")
    error_info = ErrorInfo(code="FAILED", message="execution failed")

    task.transition(TaskStatus.RUNNING)
    assert task.status is TaskStatus.RUNNING
    task.transition(TaskStatus.FAILED, error_info=error_info)

    assert task.status is TaskStatus.FAILED
    assert task.error_info == error_info


def test_task_can_be_cancelled_before_start():
    task = TaskModel(request_id=uuid4(), task_type="user_request")

    task.transition(TaskStatus.CANCELLED)

    assert task.status is TaskStatus.CANCELLED
    assert task.started_at is None
    assert task.completed_at is not None
    assert task.status is TaskStatus.CANCELLED


@pytest.mark.parametrize(
    ("initial_status", "next_status"),
    [
        (TaskStatus.PENDING, TaskStatus.COMPLETED),
        (TaskStatus.COMPLETED, TaskStatus.RUNNING),
        (TaskStatus.FAILED, TaskStatus.CANCELLED),
        (TaskStatus.CANCELLED, TaskStatus.RUNNING),
    ],
)
def test_task_rejects_invalid_transitions(initial_status, next_status):
    task = TaskModel(request_id=uuid4(), task_type="user_request", status=initial_status)

    with pytest.raises(ValueError, match="Cannot transition"):
        task.transition(next_status)


@pytest.mark.parametrize(
    ("initial_status", "next_status"),
    [
        (TaskStatus.COMPLETED, TaskStatus.FAILED),
        (TaskStatus.FAILED, TaskStatus.COMPLETED),
        (TaskStatus.CANCELLED, TaskStatus.COMPLETED),
    ],
)
def test_task_terminal_states_are_immutable(initial_status, next_status):
    task = TaskModel(request_id=uuid4(), task_type="user_request", status=initial_status)

    with pytest.raises(ValueError, match="Cannot transition"):
        task.transition(next_status)
    assert task.status is initial_status


def test_execution_result_validation():
    task_id = uuid4()
    result = ExecutionResult(
        success=True,
        task_id=task_id,
        result_data={"open_ports": [80]},
        message="Scan complete",
        duration_seconds=0.25,
    )
    assert result.task_id == task_id

    with pytest.raises(ValidationError):
        ExecutionResult(success=False, task_id=task_id, message="Failed", duration_seconds=0)
    with pytest.raises(ValidationError):
        ExecutionResult(
            success=True,
            task_id=task_id,
            message="Unexpected error",
            error_info=ErrorInfo(code="ERROR", message="failure"),
            duration_seconds=0,
        )
