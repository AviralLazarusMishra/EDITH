import socket
from concurrent.futures import ThreadPoolExecutor# ---------------- TOOL LAYER ---------------- #

def scan_port(target, port, timeout):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex((target, port)) == 0:
                return port
    except:
        return None


def scan_ports(target, ports=None, timeout=0.2):
    if ports is None:
        ports = range(1, 1025)

    open_ports = []

    with ThreadPoolExecutor(max_workers=100) as executor:
        results = executor.map(lambda p: scan_port(target, p, timeout), ports)

    for result in results:
        if result:
            open_ports.append(result)

    return {
        "target": target,
        "open_ports": open_ports
    }

# ---------------- LOGIC LAYER ---------------- #

def analyze_ports(scan_data):
    open_ports = scan_data["open_ports"]
    target = scan_data["target"]

    risks = []

    # Example risk detection
    port_map = {
        80: ("HTTP", "Unencrypted web traffic"),
        443: ("HTTPS", "Secure web service (generally safe)"),        
        445: ("SMB", "File sharing vulnerability"),
        53: ("DNS", "DNS service exposed"),
        853: ("DNS-over-TLS", "Encrypted DNS service")
    }

    for port in open_ports:
        if port in port_map:
            service, risk_desc = port_map[port]
            risks.append({
                "port": port,
                "service": service,
                "risk": risk_desc
            })
        # 🔥 Risk level logic
        risk_level = "LOW"

    if any(p in open_ports for p in [80, 445]):
        risk_level = "MEDIUM"

    # 🔥 CONTEXT AWARE OVERRIDE (PUT IT HERE)
    is_local = target.startswith("127.") or target.startswith("192.168")

    if is_local:
        if any(p in open_ports for p in [445, 3389]):
            risk_level = "MEDIUM"   # local but sensitive services
        else:
            risk_level = "LOW"
    else:
        if any(p in open_ports for p in [445, 3389]):
            risk_level = "HIGH"
        elif any(p in open_ports for p in [80]):
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

    return {
        "target": target,
        "open_ports": open_ports,
        "risks": risks,
        "risk_level": risk_level
    }


def get_risk_level(risks):
    if not risks:
        return "LOW"

    high_risk_ports = [22, 3306]

    for r in risks:
        if r["port"] in high_risk_ports:
            return "HIGH"

    return "MEDIUM"


# ---------------- OUTPUT LAYER ---------------- #

def format_report(analysis):
    if "error" in analysis:
        return f"[ERROR] {analysis['error']}"

    output = []
    output.append(f"[TARGET] {analysis['target']}")
    output.append(f"[OPEN PORTS] {analysis['open_ports']}")
    output.append(f"[RISK LEVEL] {analysis['risk_level']}")
    output.append("")

    if not analysis["risks"]:
        output.append("No significant risks detected.")
    else:
        output.append("[DETAILS]")
        for r in analysis["risks"]:
            service = r.get("service", "Unknown")
            risk = r.get("risk", "Unknown")

            output.append(
                f"Port {r['port']} ({service}) -> {risk}"
    )

    return "\n".join(output)


# ---------------- CONTROLLER ---------------- #

def run_scan(target):
    scan_data = scan_ports(target)
    analysis = analyze_ports(scan_data)
    return format_report(analysis)

print("RUN_SCAN EXECUTED")