from copy import deepcopy
from enum import StrEnum
from typing import Annotated, Any, Protocol, Self, TypeVar, runtime_checkable
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

ToolIdentifier = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*:[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"
    ),
]
InputModel = TypeVar("InputModel", bound=BaseModel)


class ToolMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    tool_id: ToolIdentifier
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    category: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
    active: bool = Field(default=True, strict=True)


class ToolContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    request_id: UUID
    task_id: UUID
    source: str = Field(min_length=1)
    scoped_context: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Per-invocation JSON data, copied on construction.",
    )

    @field_validator("scoped_context", mode="before")
    @classmethod
    def isolate_scoped_context(cls, value: object) -> object:
        return deepcopy(value)


class CapabilityErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class CapabilityError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    code: CapabilityErrorCode
    message: str = Field(
        min_length=1,
        description="Safe user-facing text; do not include stack traces or sensitive information.",
    )


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    success: bool = Field(strict=True)
    tool_id: ToolIdentifier
    data: Any = None
    message: str = Field(min_length=1)
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    error: CapabilityError | None = None

    @model_validator(mode="after")
    def validate_error_consistency(self) -> Self:
        if self.success and self.error is not None:
            raise ValueError("Successful tool results must not include an error")
        if not self.success and self.error is None:
            raise ValueError("Failed tool results must include an error")
        return self


@runtime_checkable
class CapabilityTool(Protocol[InputModel]):
    metadata: ToolMetadata
    input_model: type[InputModel]

    def execute(self, inputs: InputModel, context: ToolContext) -> ToolResult: ...
