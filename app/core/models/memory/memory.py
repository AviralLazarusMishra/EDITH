from collections.abc import MutableMapping
from typing import Any

from app.core.models.memory.context import ContextStore

memory = {
    "last_target": None,
    "last_scan": None,
    "last_analysis": None,
    "last_question": None,
    "last_action": None,
    "last_command": None,
}


class MemoryContext:
    def __init__(self, values: MutableMapping[str, Any] | None = None) -> None:
        self._values = {} if values is None else values

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def update(self, values: dict[str, Any]) -> None:
        self._values.update(values)


def get_default_context() -> ContextStore:
    return MemoryContext(memory)
