from multiprocessing import context


def explain_analysis(analysis):
    explanations = []

    for r in analysis["risks"]:
        if r["port"] == 80:
            explanations.append("HTTP is unencrypted, data can be intercepted.")
        elif r["port"] == 53:
            explanations.append("DNS can be abused for spoofing or amplification attacks.")
        elif r["port"] == 443:
            explanations.append("HTTPS is secure, but misconfiguration can still pose risks.")
        elif r["port"] == 853:
            explanations.append("DNS over TLS is secure but should be properly configured.")
        elif r["port"] == 445:
            explanations.append(
            "SMB can expose file-sharing services and is often targeted in network attacks."
    )

    return explanations

def suggest_actions(analysis):
    if not analysis or "risks" not in analysis:
        return "No suggestions available."

    open_ports = analysis.get("open_ports", [])
    suggestions = []

    # HTTP logic
    if 80 in open_ports and 443 not in open_ports:
        suggestions.append("Enable HTTPS (port 443) to secure traffic.")

    elif 80 in open_ports and 443 in open_ports:
        suggestions.append("Consider redirecting HTTP (port 80) to HTTPS.")

    # SMB logic
    if 445 in open_ports:
        suggestions.append("Restrict SMB access to local network or disable it.")

    # DNS logic
    if 53 in open_ports:
        suggestions.append("Ensure DNS service is secured and not publicly abused.")

    if not suggestions:
        return "System appears properly configured. No immediate action needed."
    if context == "local":
        suggestions.append("System is local. Exposure risk is limited.")

    return "\n".join(suggestions)

def interpret_risk(analysis):
    level = analysis.get("risk_level", "LOW")

    if level == "LOW":
        return "Risk is minimal. No immediate threats detected."
    elif level == "MEDIUM":
        return "Moderate risk. Some services may expose vulnerabilities."
    elif level == "HIGH":
        return "High risk. Immediate attention recommended."
    elif level == "CRITICAL":
        return "Critical risk. System is highly vulnerable and should be secured immediately."
    
def get_context(target):
    if target.startswith("127.") or target.startswith("192.168") or target.startswith("localhost"):
        return "local"
    return "public"