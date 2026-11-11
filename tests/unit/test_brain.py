from app.core.models.memory.memory import memory
from app.core.models.orchestrator.brain import (
    extract_target,
    interpret_command,
    parse_ai_response,
)


def test_interpret_command_preserves_cli_actions():
    assert interpret_command("scan 192.168.1.1") == {
        "action": "check",
        "target": "192.168.1.1",
    }
    assert interpret_command("whois example.com") == {
        "action": "whois",
        "target": "example.com",
    }
    assert interpret_command("open https://example.com") == {
        "action": "open",
        "target": "https://example.com",
    }


def test_interpret_command_preserves_url_path_and_query_case():
    url = "https://example.com/CaseSensitive/Path?AccessToken=AbCd123&mode=FAST"

    assert interpret_command(f"OPEN {url}") == {"action": "open", "target": url}


def test_interpret_command_uses_previous_target(monkeypatch):
    monkeypatch.setitem(memory, "last_target", "192.168.1.10")

    assert interpret_command("rescan") == {
        "action": "check",
        "target": "192.168.1.10",
    }


def test_extract_target_handles_localhost():
    assert extract_target("check localhost") == "127.0.0.1"


def test_parse_ai_response_preserves_response_handling():
    response_text = "SCAN https://example.com/CaseSensitive?Key=AbCd"
    response = type("Response", (), {"json": lambda self: {"response": response_text}})()

    assert parse_ai_response(response) == {
        "action": "scan",
        "target": "https://example.com/CaseSensitive?Key=AbCd",
    }
