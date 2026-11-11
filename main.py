from pydantic import ValidationError

from app.core.models.execution.adapter import LegacyCommandAdapter
from app.core.models.memory.memory import get_default_context
from app.core.runtime import CoreRuntime, RequestManager


def main(
    runtime: CoreRuntime | None = None,
    request_manager: RequestManager | None = None,
) -> None:
    if runtime is None:
        context = get_default_context()
        runtime = CoreRuntime(LegacyCommandAdapter(context), context)
    request_manager = RequestManager() if request_manager is None else request_manager
    print("EDITH ONLINE")

    while True:
        command = input("EDITH >> ")

        if command.lower() in ["exit", "quit"]:
            print("EDITH OFFLINE")
            break

        try:
            request = request_manager.create_request(command, source="cli")
        except ValidationError as error:
            print(f"[ERROR] Invalid request: {error.errors()[0]['msg']}")
            continue
        result = runtime.execute(request)
        print(result.message)


if __name__ == "__main__":
    main()
