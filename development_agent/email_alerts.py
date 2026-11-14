
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
ADMIN_EMAIL = os.getenv("SENTINELAI_ADMIN_EMAIL")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_alert_email(owner_email, subject, body):
    """Send an alert to the website owner and SentinelAI admin."""

    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        return {"success": False, "message": "SMTP credentials are missing"}

    recipients = list(dict.fromkeys(
        email.strip()
        for email in [owner_email, ADMIN_EMAIL]
        if email and email.strip()
    ))

    if not recipients:
        return {"success": False, "message": "No recipient email configured"}

    message = EmailMessage()
    message["From"] = SMTP_EMAIL
    message["To"] = ", ".join(recipients)
    message["Subject"] = f"[SentinelAI Alert] {subject}"
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.send_message(message)

        print(f"Alert email sent to: {', '.join(recipients)}")
        return {"success": True, "recipients": recipients}

    except Exception as error:
        print(f"Email sending failed: {error}")
        return {"success": False, "message": str(error)}
