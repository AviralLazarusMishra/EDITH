from app.core.models.execution import controller
from app.core.models.memory.memory import memory


def test_check_runs_scan_and_updates_memory(monkeypatch):
    scan_data = {"target": "example.com", "open_ports": [80]}
    monkeypatch.setattr(controller, "scan_ports", lambda target: scan_data)
    monkeypatch.setitem(memory, "last_target", None)
    monkeypatch.setitem(memory, "last_scan", None)
    monkeypatch.setitem(memory, "last_analysis", None)

    result = controller.execute_command({"action": "check", "target": "example.com"})

    assert "[TARGET] example.com" in result
    assert "[RISK LEVEL] MEDIUM" in result
    assert memory["last_target"] == "example.com"
    assert memory["last_scan"] == scan_data
    assert memory["last_analysis"]["open_ports"] == [80]


def test_assess_without_analysis_returns_message(monkeypatch):
    monkeypatch.setitem(memory, "last_analysis", None)

    assert controller.execute_command({"action": "assess"}) == "No analysis available."


def test_whois_preserves_resolution_and_registry_lookup(monkeypatch):
    monkeypatch.setattr(controller.socket, "gethostbyname", lambda target: "203.0.113.10")
    monkeypatch.setattr(controller, "run_whois", lambda target: "Registry record")

    result = controller.execute_command({"action": "whois", "target": "example.com"})

    assert "[WHOIS] example.com resolves to 203.0.113.10" in result
    assert "Registry record" in result
    assert memory["last_target"] == "example.com"
