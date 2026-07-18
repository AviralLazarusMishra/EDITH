from app.core.models.orchestrator.brain import interpret_command
from app.core.models.execution.controller import execute_command
import requests
from app.core.models.orchestrator.brain import parse_ai_response


def main():
    print("EDITH ONLINE")

    while True:
        command = input("EDITH >> ")

        if command.lower() in ["exit", "quit"]:
            print("EDITH OFFLINE")
            break

        interpreted = interpret_command(command)
        result = execute_command(interpreted)

        print(result)


if __name__ == "__main__":
    main()

def interpret_command(command):
    try:
        response = requests.post(...)
        return parse_ai_response(response)
    except:
        # fallback
        parts = command.split()

        if parts[0] == "scan":
            return {"action": "scan", "target": parts[1]}

        if parts[0] == "check":
            return {"action": "check", "target": parts[1]}

        return {"action": "unknown"}