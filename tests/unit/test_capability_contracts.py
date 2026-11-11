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
    assert context.scoped_context["target"]["ports"] == [80, 443]

    context.scoped_context["target"]["host"] = "changed.test"
    assert scoped["target"]["host"] == "example.test"
    assert other_context.scoped_context["target"]["host"] == "example.test"
    with pytest.raises(ValidationError):
        context.source = "web"


def test_tool_result_preserves_structured_success_data():
    data = {"hosts": [{"address": "127.0.0.1", "ports": [80, 443]}]}
    result = ToolResult(
        success=True,
        tool_id="edith.network:port-scan",
        data=data,
        message="Scan complete.",
        duration_ms=12.5,
    )

    assert result.data == data
    assert result.error is None


def test_tool_result_requires_errors_only_for_failures():
    error = CapabilityError(code=CapabilityErrorCode.EXECUTION_FAILED, message="Tool failed.")
    failed = ToolResult(
        success=False,
        tool_id="edith.network:port-scan",
        message="Scan failed.",
        duration_ms=0,
        error=error,
    )
    assert failed.error is error

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
    error = CapabilityError(code=code, message="Safe error message.")

    assert error.code is code


def test_capability_error_rejects_unknown_codes_and_empty_messages():
    with pytest.raises(ValidationError):
        CapabilityError(code="UNKNOWN", message="Failure.")
    with pytest.raises(ValidationError):
        CapabilityError(code=CapabilityErrorCode.INVALID_INPUT, message=" ")


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
