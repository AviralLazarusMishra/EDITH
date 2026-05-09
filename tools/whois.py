import whois

def run_whois(target):
    try:
        data = whois.whois(target)
        return str(data)
    except Exception as e:
        return f"[WHOIS ERROR] {str(e)}"