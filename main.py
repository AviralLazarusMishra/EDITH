from app.core.models.execution.controller import execute_command
from app.core.models.orchestrator.brain import interpret_command


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
