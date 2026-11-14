
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

from development_agent.email_alerts import send_alert_email
from development_agent.website_config import WEBSITES
from shared.database import save_security_alert


# ==========================================
# SECURITY DETECTION RULES
# ==========================================

SECURITY_RULES = [
    {
        "name": "Possible SQL Injection",
        "pattern": r"(?i)(union\s+select|or\s+1=1|drop\s+table|sleep\s*\()",
        "severity": "HIGH",
    },
    {
        "name": "Possible Directory Traversal",
        "pattern": r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)",
        "severity": "HIGH",
    },
    {
        "name": "Possible Command Injection",
        "pattern": r"(?i)(;\s*(whoami|ipconfig|powershell)|\|\s*(cmd|bash))",
        "severity": "CRITICAL",
    },
    {
        "name": "Failed Login Attempt",
        "pattern": r"(?i)(failed login|login failed|authentication failure|invalid password)",
        "severity": "MEDIUM",
    },
    {
        "name": "Suspicious Access",
        "pattern": r"(?i)(/\.env|/wp-admin|/phpmyadmin|/etc/passwd)",
        "severity": "HIGH",
    },
]


# ==========================================
# CONFIGURATION
# ==========================================

STATE_FILE = Path("logs/security_alert_state.json")
ALERT_COOLDOWN = timedelta(minutes=15)

alert_state = {}


# ==========================================
# LOAD DUPLICATE ALERT STATE
# ==========================================

def load_alert_state():
    global alert_state

    if STATE_FILE.exists():
        try:
            alert_state = json.loads(
                STATE_FILE.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            alert_state = {}


# ==========================================
# SAVE DUPLICATE ALERT STATE
# ==========================================

def save_alert_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    STATE_FILE.write_text(
        json.dumps(alert_state, indent=2),
        encoding="utf-8",
    )


# ==========================================
# ANALYZE INDIVIDUAL LOG LINE
# ==========================================

def analyze_log_line(line):
    alerts = []

    for rule in SECURITY_RULES:
        if re.search(rule["pattern"], line):
            alerts.append({
                "alert_type": rule["name"],
                "severity": rule["severity"],
                "evidence": line.strip()[:500],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    return alerts


# ==========================================
# SECURITY ALERT + EMAIL + DATABASE
# ==========================================

def notify_security_alert(alert, owner_email):

    # Save every detected alert in SQLite.
    # Email status is updated based on actual delivery.

    if alert["severity"] not in ("HIGH", "CRITICAL"):

        save_security_alert(
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            evidence=alert["evidence"],
            source="Windows/Sample Logs",
            email_sent=False,
            timestamp=alert["timestamp"],
        )

        print(
            f"[RECORDED] {alert['severity']} - "
            f"{alert['alert_type']}"
        )

        return

    # Generate unique event fingerprint.
    event_text = (
        alert["alert_type"] + "|" +
        alert["severity"] + "|" +
        alert["evidence"]
    )

    event_id = hashlib.sha256(
        event_text.encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc)
    previous = alert_state.get(event_id)

    # Check duplicate email cooldown.
    if previous:
        last_sent = datetime.fromisoformat(
            previous["last_sent"]
        )

        if now - last_sent < ALERT_COOLDOWN:

            save_security_alert(
                alert_type=alert["alert_type"],
                severity=alert["severity"],
                evidence=alert["evidence"],
                source="Windows/Sample Logs",
                email_sent=False,
                timestamp=alert["timestamp"],
            )

            print(
                f"[DUPLICATE SUPPRESSED] "
                f"{alert['alert_type']}"
            )

            return

    # Prepare email.
    subject = (
        f"{alert['severity']} Security Alert: "
        f"{alert['alert_type']}"
    )

    body = (
        "SentinelAI Security Notification\n\n"
        f"Alert: {alert['alert_type']}\n"
        f"Severity: {alert['severity']}\n"
        f"Detected: {alert['timestamp']}\n"
        f"Evidence: {alert['evidence']}\n\n"
        "This is a suspicious activity indicator, not "
        "confirmation of a successful attack. "
        "Please investigate the original logs."
    )

    # Send email to website owner and admin.
    result = send_alert_email(
        owner_email,
        subject,
        body,
    )

    email_sent = result.get("success", False)

    # Save security event and actual email delivery status.
    save_security_alert(
        alert_type=alert["alert_type"],
        severity=alert["severity"],
        evidence=alert["evidence"],
        source="Windows/Sample Logs",
        email_sent=email_sent,
        timestamp=alert["timestamp"],
    )

    if email_sent:

        alert_state[event_id] = {
            "last_sent": now.isoformat(),
            "alert_type": alert["alert_type"],
            "severity": alert["severity"],
        }

        save_alert_state()

        print(
            f"[EMAIL ALERT] {alert['severity']} - "
            f"{alert['alert_type']}"
        )

    else:
        print(
            f"[EMAIL FAILED] {result.get('message', 'Unknown error')}"
        )


# ==========================================
# ANALYZE COMPLETE LOG FILE
# ==========================================

def analyze_log_file(file_path, owner_email=None):

    detected_alerts = []

    if owner_email is None:
        owner_email = WEBSITES[0]["owner_email"]

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as log_file:

            for line in log_file:

                alerts = analyze_log_line(line)

                for alert in alerts:
                    detected_alerts.append(alert)

                    notify_security_alert(
                        alert,
                        owner_email,
                    )

    except FileNotFoundError:
        print(f"Log file not found: {file_path}")

    except PermissionError:
        print(f"Permission denied: {file_path}")

    return detected_alerts


# ==========================================
# INITIALIZE
# ==========================================

load_alert_state()
