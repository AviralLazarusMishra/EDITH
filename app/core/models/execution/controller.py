import socket
import webbrowser

from app.core.models.memory.memory import memory
from app.core.models.reasoning.reasoning import explain_analysis, suggest_actions
from tools.scanner import analyze_ports, format_report, scan_ports
from tools.whois import run_whois


def execute_command(data):
    action = data.get("action")

    if action == "error":
        return "[ERROR] No previous target found. Please specify a target."

    if action in {"scan", "check"}:
        target = data.get("target")
        if not target:
            return "[ERROR] No target provided."

        scan_data = scan_ports(target)
        analysis = analyze_ports(scan_data)
        memory["last_target"] = target
        memory["last_scan"] = scan_data
        memory["last_analysis"] = analysis

        if action == "scan":
            return scan_data
        return format_report(analysis)

    if action == "explain":
        analysis = memory["last_analysis"]
        if not analysis:
            return "No analysis available."

        explanations = explain_analysis(analysis)
        if not explanations:
            return "No significant risks to explain."
        return "\n".join(explanations)

    if action == "suggest":
        analysis = memory["last_analysis"]
        if not analysis:
            return "Run a scan first before asking for fixes."
        return suggest_actions(analysis)

    if action == "whois":
        target = str(data.get("target") or "").strip()
        if not target:
            return "[ERROR] No target provided."

        try:
            ip = "127.0.0.1" if target == "localhost" else socket.gethostbyname(target)
        except OSError as error:
            return f"[ERROR] Could not resolve domain: {error}"

        memory["last_target"] = target
        registry_data = run_whois(target)
        return f"[WHOIS] {target} resolves to {ip}\n{registry_data}"

    if action == "open":
        target = data.get("target")
        if not target:
            return "[ERROR] No target provided."

        url = target
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"

        webbrowser.open(url)
        return f"[OPEN] Opening {url}"

    if action == "assess":
        analysis = memory["last_analysis"]
        if not analysis:
            return "No analysis available."

        level = analysis["risk_level"]
        if level == "LOW":
            return "System appears safe. No immediate concerns."
        if level == "MEDIUM":
            return "Moderate risk detected. Some services may need attention."
        if level == "HIGH":
            return "High risk detected. Immediate action recommended."

    if action == "unknown":
        return "[ERROR] Unknown command"
    return "[ERROR] Invalid input"
