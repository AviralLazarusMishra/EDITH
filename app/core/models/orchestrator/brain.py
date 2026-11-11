import re

from app.core.models.memory.memory import memory


def parse_ai_response(response):
    try:
        data = response.json()

        # Ollama usually returns text in 'response'
        text = data.get("response", "").strip()
        normalized_text = text.lower()

        # Basic intent extraction (keep it simple)
        if "scan" in normalized_text:
            return {"action": "scan", "target": extract_target(text)}

        if "check" in normalized_text:
            return {"action": "check", "target": extract_target(text)}

        return {"action": "unknown"}

    except (AttributeError, KeyError, TypeError, ValueError):
        return {"action": "error"}


def extract_target(command):
    url_match = re.search(r"https?://[^\s]+", command, re.IGNORECASE)
    if url_match:
        return url_match.group(0).rstrip(".,!?")

    words = command.split()

    for word in words:
        word = word.strip()

        # Accept localhost
        if word == "localhost":
            return "127.0.0.1"

        # Match IP or domain
        match = re.match(r"(?:\d{1,3}\.){3}\d{1,3}", word) or re.match(
            r"[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", word
        )

        if match:
            return word

    return None


def interpret_command(command):
    normalized_command = command.lower()

    # --- WHOIS (STRICT MATCH) ---
    if normalized_command.startswith("whois"):
        target = extract_target(command)

        if not target:
            return {"action": "error", "message": "No target provided"}

        return {"action": "whois", "target": target}
    # --- OPEN URL ---
    if normalized_command.startswith("open"):
        target = extract_target(command)

        if not target:
            return {"action": "error"}

        return {"action": "open", "target": target}
    # --- RESCAN ---
    if "rescan" in normalized_command:
        target = extract_target(command) or memory["last_target"]

        if not target:
            return {"action": "error", "message": "No target available"}

        return {"action": "check", "target": target}

    # --- SCAN / CHECK ---
    if any(x in normalized_command for x in ["scan", "check", "analyze"]):
        target = extract_target(command) or memory["last_target"]

        if not target:
            return {"action": "error", "message": "No target available"}

        return {"action": "check", "target": target}

    # --- SAFETY / RISK ---
    if any(x in normalized_command for x in ["safe", "risk", "secure"]):
        target = memory["last_target"]

        if not target:
            return {"action": "error", "message": "No previous target available"}

        return {"action": "check", "target": target}

    # --- EXPLANATION ---
    if "why" in normalized_command:
        return {"action": "explain"}

    # --- SUGGESTION ---
    if any(x in normalized_command for x in ["what should i do", "fix", "solution"]):
        return {"action": "suggest"}

    # --- RISK ASSESSMENT ---
    if any(x in normalized_command for x in ["worry", "danger"]):
        return {"action": "assess"}
    if any(x in normalized_command for x in ["safe overall", "final verdict", "should i worry"]):
        return {"action": "assess"}

    return {"action": "unknown"}
