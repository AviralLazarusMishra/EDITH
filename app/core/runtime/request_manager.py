from typing import Any

from app.core.models.request import RequestModel


class RequestManager:
    def create_request(
        self,
        user_input: str,
        *,
        source: str = "cli",
        metadata: dict[str, Any] | None = None,
    ) -> RequestModel:
        return RequestModel(user_input=user_input, source=source, metadata=metadata)
