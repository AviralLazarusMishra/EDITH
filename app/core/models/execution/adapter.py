from typing import Any

from app.core.models.execution.controller import execute_command
from app.core.models.memory.context import ContextStore
from app.core.models.memory.memory import get_default_context
from app.core.models.orchestrator.brain import interpret_command
from app.core.models.request import RequestModel


class CommandExecutionError(RuntimeError):
    def __init__(self, message: str, *, code: str = "COMMAND_ERROR") -> None:
        super().__init__(message)
        self.code = code


class LegacyCommandAdapter:
    def __init__(
        self,
        context: ContextStore | None = None,
    ) -> None:
        self._default_context = get_default_context() if context is None else context

    def execute(
        self,
        request: RequestModel,
        context: ContextStore | None = None,
    ) -> Any:
        context = self._default_context if context is None else context
        command = interpret_command(request.user_input, context)
        output = execute_command(command, context)
        if isinstance(output, str):
            if output.startswith("[ERROR]"):
                raise CommandExecutionError(output)
            if "[WHOIS ERROR]" in output:
                raise CommandExecutionError(output, code="WHOIS_ERROR")
        return output
