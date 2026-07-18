from socket import socket
import webbrowser 
from app.core.models.reasoning.reasoning import explain_analysis
from tools.scanner import run_scan
from tools.whois import run_whois
from tools.scanner import scan_ports, analyze_ports, format_report
from app.core.models.memory.memory import memory
from app.core.models.reasoning.reasoning import suggest_actions

def execute_command(data):
    action = data.get("action")
    target = data.get("target")

    if action == "scan":
        scan_data = scan_ports(target)
        memory["last_target"] = target
        memory["last_scan"] = scan_data

        return scan_data

    elif action == "check":
        scan_data = scan_ports(target)
        analysis = analyze_ports(scan_data)
        explainations = explain_analysis(analysis)

        memory["last_target"] = target
        memory["last_scan"] = scan_data
        memory["last_analysis"] = analysis
    
    elif action == "assess":
        analysis = memory["last_analysis"]

    if not analysis:
        return "[ERROR] No analysis available."

    level = analysis["risk_level"]

    if level == "LOW":
        return "No immediate concern. System appears safe."
    elif level == "MEDIUM":
        return "Some caution advised. Review exposed services."
    elif level == "HIGH":
        return "Yes. Immediate action recommended."

    return format_report(analysis, explainations)
    
    return "[ERROR] Unknown command"

def execute_command(data):
    import socket  # keep it here or at top of file

    action = data.get("action")

    if action == "error":
        return "[ERROR] No previous target found. Please specify a target."

    elif action == "check":
        target = data["target"]

        scan_data = scan_ports(target)
        analysis = analyze_ports(scan_data)

        memory["last_target"] = target
        memory["last_scan"] = scan_data
        memory["last_analysis"] = analysis

        return format_report(analysis)

    elif action == "explain":
        analysis = memory["last_analysis"]

        if not analysis:
            return "No analysis available."

        explanations = explain_analysis(analysis)

        if not explanations:
            return "No significant risks to explain."

        return "\n".join(explanations)

    elif action == "suggest":
        analysis = memory["last_analysis"]

        if not analysis:
            return "Run a scan first before asking for fixes."

        suggestions = suggest_actions(analysis)

        if not suggestions:
            return "No immediate action required."
        return suggestions
    
    elif action == "whois":
        target = data.get("target", "").strip()

        if not target:
            return "[ERROR] No target provided."

        if target == "localhost":
            ip = "127.0.0.1"
        else:
            try:
                ip = socket.gethostbyname(target)
            except Exception as e:
                return f"[ERROR] Could not resolve domain: {e}"

        # 🔥 STORE CONTEXT
        memory["last_target"] = target

        return f"[WHOIS] {target} resolves to {ip}"   
        
    elif action == "open":

        url = data["target"]

        if not url.startswith("http"):
            url = "http://" + url

        webbrowser.open(url)

        return f"[OPEN] Opening {url}"
    
    elif action == "assess":
        analysis = memory["last_analysis"]

    if not analysis:
        return "No analysis available."

    level = analysis["risk_level"]

    if level == "LOW":
        return "System appears safe. No immediate concerns."
    
    elif level == "MEDIUM":
        return "Moderate risk detected. Some services may need attention."
    
    elif level == "HIGH":
        return "High risk detected. Immediate action recommended."
    
    elif action == "unknown":
        return "[ERROR] Unknown command"

    return "[ERROR] Invalid input"

def suggest_actions(analysis):
    suggestions = []

    for r in analysis["risks"]:
        if r["port"] == 80:
            suggestions.append("Consider enabling HTTPS (port 443).")
        if r["port"] == 445:
            suggestions.append("Disable SMB or restrict it to local network.")
        
    return "\n".join(suggestions)
