import main


def test_main_preserves_cli_request_loop(monkeypatch, capsys):
    commands = iter(["scan example.com", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))
    monkeypatch.setattr(main, "interpret_command", lambda command: {"command": command})
    monkeypatch.setattr(main, "execute_command", lambda request: f"handled {request['command']}")

    main.main()

    output = capsys.readouterr().out
    assert "EDITH ONLINE" in output
    assert "handled scan example.com" in output
    assert "EDITH OFFLINE" in output
