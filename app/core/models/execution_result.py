from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.models.task import ErrorInfo


class ExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    task_id: UUID
    result_data: Any = None
    message: str
    error_info: ErrorInfo | None = None
    duration_seconds: float = Field(ge=0)
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_error_consistency(self) -> "ExecutionResult":
        if self.success and self.error_info is not None:
            raise ValueError("Successful results must not include error_info")
        if not self.success and self.error_info is None:
            raise ValueError("Failed results must include error_info")
        return self
