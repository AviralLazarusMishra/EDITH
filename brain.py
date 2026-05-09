import requests
import json
import memory
from memory import memory
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

def interpret_command(user_input):

    prompt = f"""
You are EDITH, an AI command interpreter.

Your job:
Convert ANY user input into STRICT JSON.

Rules:
- ALWAYS output valid JSON
- NO explanations
- NO text outside JSON

Supported actions:
- scan → scanning IPs/domains
- whois → domain lookup

Format:
{{"action": "", "target": ""}}

Examples:

Input: scan 192.168.1.1
Output: {{"action": "scan", "target": "192.168.1.1"}}

Input: can you scan google.com
Output: {{"action": "scan", "target": "google.com"}}

Input: scan this ip 192.168.1.1
Output: {{"action": "scan", "target": "192.168.1.1"}}

Input: whois google.com
Output: {{"action": "whois", "target": "google.com"}}

Input: tell me about google.com domain
Output: {{"action": "whois", "target": "google.com"}}

Input: {user_input}
Output:
"""

    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })

    try:
        result = response.json()["response"]
        return json.loads(result)
    except:
        return {"action": "unknown", "target": ""}
    
def parse_ai_response(response):
    try:
        data = response.json()

        # Ollama usually returns text in 'response'
        text = data.get("response", "").strip().lower()

        # Basic intent extraction (keep it simple)
        if "scan" in text:
            return {"action": "scan", "target": extract_target(text)}

        if "check" in text:
            return {"action": "check", "target": extract_target(text)}

        return {"action": "unknown"}

    except Exception:
        return {"action": "error"}
    

def extract_target(command):
    words = command.split()

    for word in words:
        word = word.strip()

        # Accept localhost
        if word == "localhost":
            return "127.0.0.1"

        # Match IP or domain
        match = re.match(r"(?:\d{1,3}\.){3}\d{1,3}", word) or \
                re.match(r"[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", word)

        if match:
            return word

    return None

def interpret_command(command):
    command = command.lower()

    # --- WHOIS (STRICT MATCH) ---
    if command.startswith("whois"):
        target = extract_target(command)

        if not target:
            return {"action": "error", "message": "No target provided"}

        return {
            "action": "whois",
            "target": target
        }
    # --- OPEN URL ---
    if command.startswith("open"):
        target = extract_target(command)

        if not target:
            return {"action": "error"}

        return {
            "action": "open",
            "target": target
        }
    # --- RESCAN ---
    if "rescan" in command:
        target = extract_target(command) or memory["last_target"]
        
        if not target:
            return {"action": "error", "message": "No target available"}
        
        return {
                "action": "check",
                "target": target
            }    

    # --- SCAN / CHECK ---
    if any(x in command for x in ["scan", "check", "analyze"]):
        target = extract_target(command) or memory["last_target"]

        if not target:
            return {"action": "error", "message": "No target available"}

        return {
            "action": "check",
            "target": target
        }

    # --- SAFETY / RISK ---
    if any(x in command for x in ["safe", "risk", "secure"]):
        target = memory["last_target"]

        if not target:
            return {"action": "error", "message": "No previous target available"}

        return {
            "action": "check",
            "target": target
        }

    # --- EXPLANATION ---
    if "why" in command:
        return {"action": "explain"}

    # --- SUGGESTION ---
    if any(x in command for x in ["what should i do", "fix", "solution"]):
        return {"action": "suggest"}

    # --- RISK ASSESSMENT ---
    if any(x in command for x in ["worry", "danger"]):
        return {"action": "assess"}
    if any(x in command for x in ["safe overall", "final verdict", "should i worry"]):
        return {"action": "assess"}

    return {"action": "unknown"}