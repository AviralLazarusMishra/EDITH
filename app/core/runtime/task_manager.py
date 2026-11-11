from uuid import UUID

from app.core.models.task import ErrorInfo, TaskModel, TaskStatus


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[UUID, TaskModel] = {}

    def create_task(self, request_id: UUID, task_type: str) -> TaskModel:
        task = TaskModel(request_id=request_id, task_type=task_type)
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: UUID) -> TaskModel:
        return self._tasks[task_id]

    def transition(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        error_info: ErrorInfo | None = None,
    ) -> TaskModel:
        task = self.get_task(task_id)
        task.transition(status, error_info=error_info)
        return task
