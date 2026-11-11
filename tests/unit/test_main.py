import pytest

from main import main


@pytest.mark.parametrize("exit_command", ["quit", "exit"])
def test_main_preserves_cli_exit_loop(monkeypatch, capsys, exit_command):
    commands = iter([exit_command])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    main()

    output = capsys.readouterr().out
    assert "EDITH ONLINE" in output
    assert "EDITH OFFLINE" in output


def test_main_reports_invalid_empty_request_and_continues(monkeypatch, capsys):
    commands = iter(["  ", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    main()

    output = capsys.readouterr().out
    assert "[ERROR] Invalid request:" in output
    assert "EDITH OFFLINE" in output
