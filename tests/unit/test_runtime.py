import pytest

from app.core.models.execution import controller
from app.core.models.execution.adapter import LegacyCommandAdapter
from app.core.models.execution_result import ExecutionResult
from app.core.models.memory.memory import MemoryContext, get_default_context, memory
from app.core.models.request import RequestModel
from app.core.models.task import TaskStatus
from app.core.runtime import CoreRuntime, RequestManager
from app.core.runtime.task_manager import TaskManager


class SuccessfulExecutor:
    def execute(self, request, context):
        context.set("last_input", request.user_input)
        return {"accepted": True}


class FailingExecutor:
    def execute(self, request, context):
        raise ExecutionFailure("execution failed")


class ExecutionFailure(RuntimeError):
    code = "EXECUTION_FAILURE"


def test_context_retrieval_and_updates():
    context = MemoryContext({"last_target": "127.0.0.1"})

    assert context.get("last_target") == "127.0.0.1"
    assert context.get("missing", "fallback") == "fallback"
    context.set("last_target", "example.com")
    context.update({"last_analysis": {"risk_level": "LOW"}})
    assert context.get("last_target") == "example.com"
    assert context.get("last_analysis") == {"risk_level": "LOW"}


def test_independent_contexts_do_not_share_state():
    first = MemoryContext()
    second = MemoryContext()

    first.set("last_target", "example.com")

    assert second.get("last_target") is None


def test_explicit_context_mapping_is_used():
    values = {"last_target": "127.0.0.1"}
    context = MemoryContext(values)

    context.set("last_target", "example.com")

    assert values["last_target"] == "example.com"


def test_legacy_default_context_shares_module_memory(monkeypatch):
    monkeypatch.setitem(memory, "last_target", "legacy.example")
    context = get_default_context()

    assert context.get("last_target") == "legacy.example"
    context.set("last_target", "updated.example")
    assert memory["last_target"] == "updated.example"


def test_runtime_success_completes_task_and_returns_standard_result():
    context = MemoryContext()
    task_manager = TaskManager()
    runtime = CoreRuntime(SuccessfulExecutor(), context, task_manager)
    request = RequestManager().create_request("hello", source="test")

    result = runtime.execute(request)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.result_data == {"accepted": True}
    assert result.message == "{'accepted': True}"
    assert result.duration_seconds >= 0
    assert context.get("last_input") == "hello"
    task = task_manager.get_task(result.task_id)
    assert task.request_id == request.request_id
    assert task.status is TaskStatus.COMPLETED
    assert task.started_at is not None
    assert task.completed_at is not None


def test_runtime_failure_returns_error_and_fails_task():
    task_manager = TaskManager()
    runtime = CoreRuntime(FailingExecutor(), MemoryContext(), task_manager)

    result = runtime.execute(RequestModel(user_input="fail", source="test"))

    assert result.success is False
    assert result.error_info is not None
    assert result.error_info.code == "EXECUTION_FAILURE"
    assert result.message == "execution failed"
    task = task_manager.get_task(result.task_id)
    assert task.status is TaskStatus.FAILED
    assert task.error_info == result.error_info
    assert result.duration_seconds >= 0
    assert task.execution_metadata["duration_seconds"] == result.duration_seconds


def test_runtime_validates_request_mappings():
    runtime = CoreRuntime(SuccessfulExecutor(), MemoryContext())

    with pytest.raises(ValueError):
        runtime.execute({"user_input": " ", "source": "test"})


def test_scan_command_runs_through_runtime(monkeypatch):
    scan_data = {"target": "example.com", "open_ports": [80]}
    monkeypatch.setattr(controller, "scan_ports", lambda target: scan_data)
    context = MemoryContext()
    runtime = CoreRuntime(LegacyCommandAdapter(context), context)

    result = runtime.execute(RequestManager().create_request("scan example.com"))

    assert result.success is True
    assert "[TARGET] example.com" in result.message
    assert context.get("last_target") == "example.com"
    assert context.get("last_scan") == scan_data
    assert context.get("last_analysis")["open_ports"] == [80]


def test_whois_command_runs_through_runtime_without_network(monkeypatch):
    monkeypatch.setattr(controller.socket, "gethostbyname", lambda target: "203.0.113.8")
    monkeypatch.setattr(controller, "run_whois", lambda target: "WHOIS test record")
    context = MemoryContext()
    runtime = CoreRuntime(LegacyCommandAdapter(context), context)

    result = runtime.execute(RequestManager().create_request("whois example.com"))

    assert result.success is True
    assert "203.0.113.8" in result.message
    assert "WHOIS test record" in result.message
    assert context.get("last_target") == "example.com"


def test_whois_lookup_failure_returns_failed_result(monkeypatch):
    monkeypatch.setattr(controller.socket, "gethostbyname", lambda target: "203.0.113.8")
    monkeypatch.setattr(controller, "run_whois", lambda target: "[WHOIS ERROR] unavailable")
    context = MemoryContext()
    runtime = CoreRuntime(LegacyCommandAdapter(context), context)

    result = runtime.execute(RequestManager().create_request("whois example.com"))

    assert result.success is False
    assert result.error_info is not None
    assert result.error_info.code == "WHOIS_ERROR"
    assert "[WHOIS ERROR]" in result.message


def test_open_command_runs_through_runtime_with_browser_mocked(monkeypatch):
    opened_urls = []
    monkeypatch.setattr(controller.webbrowser, "open", opened_urls.append)
    context = MemoryContext()
    runtime = CoreRuntime(LegacyCommandAdapter(context), context)

    result = runtime.execute(RequestManager().create_request("open example.com/CasePath"))

    assert result.success is True
    assert opened_urls == ["http://example.com/CasePath"]
    assert result.message == "[OPEN] Opening http://example.com/CasePath"


def test_explain_and_suggest_commands_use_runtime_context():
    context = MemoryContext(
        {
            "last_analysis": {
                "target": "example.com",
                "open_ports": [80],
                "risk_level": "MEDIUM",
                "risks": [{"port": 80, "service": "HTTP", "risk": "Unencrypted"}],
            }
        }
    )
    runtime = CoreRuntime(LegacyCommandAdapter(context), context)

    explanation = runtime.execute(RequestManager().create_request("why is port 80 open"))
    suggestions = runtime.execute(RequestManager().create_request("what should I do"))

    assert explanation.success is True
    assert "unencrypted" in explanation.message.lower()
    assert suggestions.success is True
    assert "HTTPS" in suggestions.message


def test_cli_submits_requests_to_runtime(monkeypatch, capsys):
    from main import main

    class CliExecutor:
        def execute(self, request, context):
            assert request.source == "cli"
            return f"handled {request.user_input}"

    inputs = iter(["scan example.com", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    main(runtime=CoreRuntime(CliExecutor(), MemoryContext()))

    output = capsys.readouterr().out
    assert "EDITH ONLINE" in output
    assert "handled scan example.com" in output
    assert "EDITH OFFLINE" in output


def test_cli_default_runtime_preserves_shared_command_context(monkeypatch, capsys):
    scan_data = {"target": "example.com", "open_ports": [80]}
    monkeypatch.setattr(controller, "scan_ports", lambda target: scan_data)
    inputs = iter(["scan example.com", "what should I do", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setitem(memory, "last_target", None)
    monkeypatch.setitem(memory, "last_scan", None)
    monkeypatch.setitem(memory, "last_analysis", None)

    from main import main

    main()

    output = capsys.readouterr().out
    assert "[TARGET] example.com" in output
    assert "Enable HTTPS" in output
    assert memory["last_target"] == "example.com"
