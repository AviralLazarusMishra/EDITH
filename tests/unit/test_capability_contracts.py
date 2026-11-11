import json
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from app.core.capabilities import (
    CapabilityError,
    CapabilityErrorCode,
    CapabilityTool,
    ToolContext,
    ToolMetadata,
    ToolResult,
)


def _metadata(**overrides) -> ToolMetadata:
    values = {
        "tool_id": "edith.network:port-scan",
        "name": "Port scan",
        "description": "Check a host for open ports.",
        "version": "1.2.3",
        "category": "network.security",
    }
    return ToolMetadata(**(values | overrides))


def test_tool_metadata_validates_fields_and_defaults_active():
    metadata = _metadata()

    assert metadata.active is True
    assert metadata.tool_id == "edith.network:port-scan"
    assert _metadata(active=False).active is False


@pytest.mark.parametrize(
    "tool_id",
    ["", "port-scan", "Edith:scan", "edith network:scan", "edith:scan:host", ":scan"],
)
def test_tool_metadata_rejects_invalid_identifiers(tool_id):
    with pytest.raises(ValidationError):
        _metadata(tool_id=tool_id)


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": " "},
        {"description": ""},
        {"version": "v1"},
        {"version": "01.2.3"},
        {"category": "Network"},
        {"active": "false"},
        {"unexpected": True},
    ],
)
def test_tool_metadata_rejects_invalid_values(overrides):
    with pytest.raises(ValidationError):
        _metadata(**overrides)


def test_tool_metadata_is_immutable():
    metadata = _metadata()

    with pytest.raises(ValidationError):
        metadata.active = False


def test_tool_metadata_serializes_to_predictable_json():
    metadata = _metadata()

    expected = {
        "tool_id": "edith.network:port-scan",
        "name": "Port scan",
        "description": "Check a host for open ports.",
        "version": "1.2.3",
        "category": "network.security",
        "active": True,
    }
    assert metadata.model_dump(mode="json") == expected
    assert json.loads(metadata.model_dump_json()) == expected


def test_tool_context_copies_scoped_context_and_is_immutable():
    scoped = {"target": {"host": "example.test", "ports": [80, 443]}}
    context = ToolContext(
        request_id=uuid4(),
        task_id=uuid4(),
        source="cli",
        scoped_context=scoped,
    )
    other_context = ToolContext(
        request_id=uuid4(),
        task_id=uuid4(),
        source="cli",
        scoped_context=scoped,
    )

    scoped["target"]["ports"].append(8080)
    assert context.scoped_context["target"]["ports"] == (80, 443)
    assert context.scoped_context["target"] is not other_context.scoped_context["target"]

    with pytest.raises(TypeError, match="immutable"):
        context.scoped_context["target"]["host"] = "changed.test"
    with pytest.raises(AttributeError):
        context.scoped_context["target"]["ports"].append(8080)
    assert scoped["target"]["host"] == "example.test"
    assert other_context.scoped_context["target"]["host"] == "example.test"
    with pytest.raises(ValidationError):
        context.source = "web"


def test_tool_context_serializes_frozen_nested_values_as_json():
    context = ToolContext(
        request_id=uuid4(),
        task_id=uuid4(),
        source="cli",
        scoped_context={"target": {"host": "example.test", "ports": [80, 443]}},
    )

    dumped = context.model_dump(mode="json")

    assert dumped["request_id"] == str(context.request_id)
    assert dumped["task_id"] == str(context.task_id)
    expected_context = {"target": {"host": "example.test", "ports": [80, 443]}}
    assert dumped["scoped_context"] == expected_context
    assert json.loads(context.model_dump_json())["scoped_context"] == expected_context


def test_tool_context_rejects_non_json_scoped_data():
    with pytest.raises(ValidationError, match="valid JSON-compatible data"):
        ToolContext(
            request_id=uuid4(),
            task_id=uuid4(),
            source="cli",
            scoped_context={"timestamp": float("inf")},
        )


def test_tool_result_preserves_structured_success_data():
    data = {"hosts": [{"address": "127.0.0.1", "ports": [80, 443]}]}
    result = ToolResult(
        success=True,
        tool_id="edith.network:port-scan",
        data=data,
        message="Scan complete.",
        duration_ms=12.5,
    )

    assert result.model_dump(mode="json")["data"] == data
    assert result.error is None
    with pytest.raises(TypeError, match="immutable"):
        result.data["hosts"][0]["address"] = "changed"
    with pytest.raises(AttributeError):
        result.data["hosts"][0]["ports"].append(8080)


def test_tool_result_serializes_frozen_data_and_accepts_json_sequences():
    result = ToolResult(
        success=True,
        tool_id="edith.network:port-scan",
        data={"items": (1, 2), "enabled": True, "empty": None},
        message="Scan complete.",
        duration_ms=12.5,
    )

    assert result.model_dump(mode="json")["data"] == {
        "items": [1, 2],
        "enabled": True,
        "empty": None,
    }
    assert json.loads(result.model_dump_json())["data"] == {
        "items": [1, 2],
        "enabled": True,
        "empty": None,
    }


@pytest.mark.parametrize("unsupported", [object(), {"invalid": {1, 2}}])
def test_tool_result_rejects_non_json_data(unsupported):
    with pytest.raises(ValidationError, match="valid JSON"):
        ToolResult(
            success=True,
            tool_id="edith.network:port-scan",
            data=unsupported,
            message="Done.",
            duration_ms=0,
        )


@pytest.mark.parametrize(
    "invalid_json",
    [float("nan"), float("inf"), {1: "non-string object key"}],
)
def test_tool_result_rejects_values_that_cannot_round_trip_as_json(invalid_json):
    with pytest.raises(ValidationError, match="valid JSON-compatible data"):
        ToolResult(
            success=True,
            tool_id="edith.network:port-scan",
            data=invalid_json,
            message="Done.",
            duration_ms=0,
        )


def test_tool_result_requires_errors_only_for_failures():
    error = CapabilityError(
        code=CapabilityErrorCode.EXECUTION_FAILED,
        user_message="Tool failed.",
    )
    failed = ToolResult(
        success=False,
        tool_id="edith.network:port-scan",
        message="Scan failed.",
        duration_ms=0,
        error=error,
    )
    assert failed.error is error
    assert json.loads(failed.model_dump_json())["error"] == {
        "code": "EXECUTION_FAILED",
        "user_message": "Tool failed.",
        "diagnostic_details": {},
    }

    with pytest.raises(ValidationError):
        ToolResult(
            success=True,
            tool_id="edith.network:port-scan",
            message="Unexpected failure.",
            duration_ms=1,
            error=error,
        )
    with pytest.raises(ValidationError):
        ToolResult(
            success=False,
            tool_id="edith.network:port-scan",
            message="Failure without structured error.",
            duration_ms=1,
        )


def test_tool_result_rejects_negative_duration():
    with pytest.raises(ValidationError):
        ToolResult(
            success=True,
            tool_id="edith.network:port-scan",
            message="Done.",
            duration_ms=-0.1,
        )


def test_tool_result_requires_boolean_success():
    with pytest.raises(ValidationError):
        ToolResult(
            success="false",
            tool_id="edith.network:port-scan",
            message="Done.",
            duration_ms=0,
        )


@pytest.mark.parametrize("code", list(CapabilityErrorCode))
def test_capability_error_validates_typed_codes(code):
    error = CapabilityError(code=code, user_message="Request could not be completed.")

    assert error.code is code


def test_capability_error_rejects_unknown_codes_and_empty_messages():
    with pytest.raises(ValidationError):
        CapabilityError(code="UNKNOWN", user_message="Operation failed.")
    with pytest.raises(ValidationError):
        CapabilityError(code=CapabilityErrorCode.INVALID_INPUT, user_message=" ")
    with pytest.raises(ValidationError):
        CapabilityError(
            code=CapabilityErrorCode.EXECUTION_FAILED,
            user_message="First line\nTraceback follows",
        )
    with pytest.raises(ValidationError):
        CapabilityError(
            code=CapabilityErrorCode.EXECUTION_FAILED,
            user_message="x" * 241,
        )


def test_capability_error_keeps_diagnostics_separate_from_user_message():
    error = CapabilityError(
        code=CapabilityErrorCode.EXECUTION_FAILED,
        user_message="The operation could not be completed.",
        diagnostic_details={"exception_type": "TimeoutError", "retryable": True},
    )

    assert error.user_message == "The operation could not be completed."
    assert error.diagnostic_details == {
        "exception_type": "TimeoutError",
        "retryable": True,
    }
    assert error.model_dump(mode="json") == {
        "code": "EXECUTION_FAILED",
        "user_message": "The operation could not be completed.",
        "diagnostic_details": {"exception_type": "TimeoutError", "retryable": True},
    }
    assert json.loads(error.model_dump_json()) == {
        "code": "EXECUTION_FAILED",
        "user_message": "The operation could not be completed.",
        "diagnostic_details": {"exception_type": "TimeoutError", "retryable": True},
    }
    with pytest.raises(TypeError, match="immutable"):
        error.diagnostic_details["retryable"] = False


def test_capability_error_rejects_non_json_diagnostics():
    with pytest.raises(ValidationError, match="valid JSON-compatible data"):
        CapabilityError(
            code=CapabilityErrorCode.EXECUTION_FAILED,
            user_message="The operation failed.",
            diagnostic_details={"exception": object()},
        )


@pytest.mark.parametrize("invalid_json", [float("nan"), {1: "non-string object key"}])
def test_capability_error_rejects_diagnostics_that_cannot_round_trip_as_json(invalid_json):
    with pytest.raises(ValidationError, match="valid JSON-compatible data"):
        CapabilityError(
            code=CapabilityErrorCode.EXECUTION_FAILED,
            user_message="The operation failed.",
            diagnostic_details={"detail": invalid_json},
        )


def test_minimal_tool_implementation_satisfies_structural_protocol():
    class ScanInput(BaseModel):
        host: str

    class MinimalTool:
        metadata = _metadata()
        input_model = ScanInput

        def execute(self, inputs: ScanInput, context: ToolContext) -> ToolResult:
            return ToolResult(
                success=True,
                tool_id=self.metadata.tool_id,
                data={"host": inputs.host, "source": context.source},
                message="Scan complete.",
                duration_ms=1,
            )

    tool: CapabilityTool[ScanInput] = MinimalTool()
    context = ToolContext(request_id=uuid4(), task_id=uuid4(), source="cli")
    result = tool.execute(ScanInput(host="example.test"), context)

    assert isinstance(tool, CapabilityTool)
    assert result.success is True
    assert result.data == {"host": "example.test", "source": "cli"}


def test_runtime_protocol_check_rejects_missing_members():
    class IncompleteTool:
        metadata = _metadata()
        input_model = BaseModel

    assert not isinstance(IncompleteTool(), CapabilityTool)
