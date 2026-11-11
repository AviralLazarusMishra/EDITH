from collections.abc import Mapping
from time import perf_counter
from typing import Any, Protocol

from app.core.models.execution_result import ExecutionResult
from app.core.models.memory.context import ContextStore
from app.core.models.request import RequestModel
from app.core.models.task import ErrorInfo, TaskStatus
from app.core.runtime.task_manager import TaskManager


class ExecutionEngine(Protocol):
    def execute(self, request: RequestModel, context: ContextStore) -> Any: ...


class CoreRuntime:
    def __init__(
        self,
        execution_engine: ExecutionEngine,
        context: ContextStore,
        task_manager: TaskManager | None = None,
    ) -> None:
        self.context = context
        self.task_manager = TaskManager() if task_manager is None else task_manager
        self.execution_engine = execution_engine

    def execute(self, request: RequestModel | Mapping[str, Any]) -> ExecutionResult:
        validated_request = (
            request if isinstance(request, RequestModel) else RequestModel.model_validate(request)
        )
        task = self.task_manager.create_task(validated_request.request_id, "user_request")
        self.task_manager.transition(task.task_id, TaskStatus.RUNNING)

        started = perf_counter()
        try:
            data = self.execution_engine.execute(validated_request, self.context)
        except Exception as error:  # noqa: BLE001
            duration = perf_counter() - started
            error_info = ErrorInfo(
                code=getattr(error, "code", type(error).__name__),
                message=str(error) or type(error).__name__,
            )
            task.execution_metadata["duration_seconds"] = duration
            self.task_manager.transition(
                task.task_id,
                TaskStatus.FAILED,
                error_info=error_info,
            )
            return ExecutionResult(
                success=False,
                task_id=task.task_id,
                message=error_info.message,
                error_info=error_info,
                duration_seconds=duration,
            )

        duration = perf_counter() - started
        task.execution_metadata["duration_seconds"] = duration
        self.task_manager.transition(task.task_id, TaskStatus.COMPLETED)
        return ExecutionResult(
            success=True,
            task_id=task.task_id,
            result_data=data,
            message=data if isinstance(data, str) else str(data),
            duration_seconds=duration,
        )
