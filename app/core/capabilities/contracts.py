from collections.abc import Mapping
from enum import StrEnum
from math import isfinite
from typing import Annotated, Any, Protocol, Self, TypeVar, runtime_checkable
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_serializer,
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


class _FrozenDict(dict):
    def _immutable(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("This mapping is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def _freeze_json(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return _FrozenDict({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json(item) for item in value]
    return value


def _copy_json(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Value must be valid JSON-compatible data")
        return {key: _copy_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy_json(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and isfinite(value):
        return value
    raise ValueError("Value must be valid JSON-compatible data")


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
        return _copy_json(value)

    @field_validator("scoped_context")
    @classmethod
    def freeze_scoped_context(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return _freeze_json(value)

    @field_serializer("scoped_context")
    def serialize_scoped_context(self, value: dict[str, JsonValue]) -> JsonValue:
        return _thaw_json(value)


class CapabilityErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class CapabilityError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    code: CapabilityErrorCode
    user_message: str = Field(
        min_length=1,
        max_length=240,
        pattern=r"^[^\r\n]+$",
        description=(
            "Concise, caller-supplied user-facing text. Never populate this from raw exception "
            "strings; this contract does not detect secrets."
        ),
    )
    diagnostic_details: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Structured internal diagnostics; do not expose as user-facing content.",
    )

    @field_validator("diagnostic_details", mode="before")
    @classmethod
    def copy_diagnostic_details(cls, value: object) -> object:
        return _copy_json(value)

    @field_validator("diagnostic_details")
    @classmethod
    def freeze_diagnostic_details(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return _freeze_json(value)

    @field_serializer("diagnostic_details")
    def serialize_diagnostic_details(self, value: dict[str, JsonValue]) -> JsonValue:
        return _thaw_json(value)


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    success: bool = Field(strict=True)
    tool_id: ToolIdentifier
    data: JsonValue = None
    message: str = Field(min_length=1)
    duration_ms: float = Field(ge=0, allow_inf_nan=False)
    error: CapabilityError | None = None

    @field_validator("data", mode="before")
    @classmethod
    def copy_data(cls, value: object) -> object:
        return _copy_json(value)

    @field_validator("data")
    @classmethod
    def freeze_data(cls, value: JsonValue) -> JsonValue:
        return _freeze_json(value)

    @field_serializer("data")
    def serialize_data(self, value: JsonValue) -> JsonValue:
        return _thaw_json(value)

    @model_validator(mode="after")
    def validate_error_consistency(self) -> Self:
        if self.success and self.error is not None:
            raise ValueError("Successful tool results must not include an error")
        if not self.success and self.error is None:
            raise ValueError("Failed tool results must include an error")
        return self


@runtime_checkable
class CapabilityTool(Protocol[InputModel]):
    """Structural tool contract; runtime checks test member presence only.

    The future ToolExecutor is responsible for validating input and output types.
    """

    metadata: ToolMetadata
    input_model: type[InputModel]

    def execute(self, inputs: InputModel, context: ToolContext) -> ToolResult: ...
