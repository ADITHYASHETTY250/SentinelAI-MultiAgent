
import asyncio
import httpx

from datetime import datetime, timezone

from development_agent.website_config import WEBSITES
from development_agent.email_alerts import send_alert_email
from shared.database import save_website_check


# ==========================================
# CONFIGURATION
# ==========================================

CHECK_INTERVAL = 10
REQUEST_TIMEOUT = 8

# Tracks the previous website status.
website_status = {}


# ==========================================
# CHECK WEBSITE STATUS
# ==========================================

async def check_website(client, website):

    url = website["url"]

    checked_at = datetime.now(timezone.utc).isoformat()

    try:

        response = await client.get(url)

        result = {
            "name": website["name"],
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": round(
                response.elapsed.total_seconds() * 1000,
                2
            ),
            "checked_at": checked_at,
            "error": None,
        }

        if response.status_code >= 400:

            result["error"] = (
                f"HTTP {response.status_code}"
            )

        return result

    except httpx.TimeoutException:

        return {
            "name": website["name"],
            "url": url,
            "checked_at": checked_at,
            "status_code": None,
            "response_time_ms": None,
            "error": "Request timed out",
        }

    except httpx.RequestError as error:

        return {
            "name": website["name"],
            "url": url,
            "checked_at": checked_at,
            "status_code": None,
            "response_time_ms": None,
            "error": str(error),
        }

    except Exception as error:

        return {
            "name": website["name"],
            "url": url,
            "checked_at": checked_at,
            "status_code": None,
            "response_time_ms": None,
            "error": str(error),
        }


# ==========================================
# SEND WEBSITE DOWN EMAIL
# ==========================================

def send_down_alert(result, website):

    name = result["name"]

    subject = (
        f"CRITICAL: {name} - Website is DOWN"
    )

    body = (
        "SENTINELAI WEBSITE FAILURE ALERT\n\n"

        f"Website: {name}\n"
        f"URL: {result['url']}\n"
        "Status: DOWN\n"
        f"Error: {result['error']}\n"
        f"Time: {result['checked_at']}\n\n"

        "SentinelAI detected that the website "
        "is not responding successfully.\n\n"

        "Please investigate this issue and "
        "restore website availability."
    )

    email_result = send_alert_email(
        website.get("owner_email"),
        subject,
        body,
    )

    print(f"[DOWN EMAIL] {email_result}")

    return email_result.get("success", False)


# ==========================================
# SEND WEBSITE RECOVERY EMAIL
# ==========================================

def send_recovery_alert(result, website):

    name = result["name"]

    subject = (
        f"RECOVERED: {name} - Website is ONLINE"
    )

    body = (
        "SENTINELAI WEBSITE RECOVERY NOTIFICATION\n\n"

        f"Website: {name}\n"
        f"URL: {result['url']}\n"
        "Status: ONLINE\n"
        f"HTTP Status: {result['status_code']}\n"
        f"Response Time: {result['response_time_ms']} ms\n"
        f"Recovery Time: {result['checked_at']}\n\n"

        "The website is responding successfully again.\n"
        "Website monitoring has resumed."
    )

    email_result = send_alert_email(
        website.get("owner_email"),
        subject,
        body,
    )

    print(f"[RECOVERY EMAIL] {email_result}")

    return email_result.get("success", False)


# ==========================================
# PROCESS RESULT AND SEND EMAIL
# ==========================================

def process_result(result, website):

    name = result["name"]

    error = result["error"]

    previous_status = website_status.get(name)

    # ======================================
    # WEBSITE DOWN
    # SEND EMAIL EVERY 10 SECONDS
    # ======================================

    if error:

        website_status[name] = "DOWN"

        print(
            f"[ALERT] {name}: {error}"
        )

        try:

            email_sent = send_down_alert(
                result,
                website
            )

            if email_sent:

                print(
                    f"[EMAIL SENT] "
                    f"{name} DOWN notification sent"
                )

            else:

                print(
                    f"[EMAIL FAILED] "
                    f"{name} DOWN notification failed"
                )

        except Exception as email_error:

            print(
                f"[EMAIL ERROR] {name}: {email_error}"
            )

        return

    # ======================================
    # WEBSITE RECOVERED
    # ======================================

    if previous_status == "DOWN":

        try:

            email_sent = send_recovery_alert(
                result,
                website
            )

            if email_sent:

                website_status[name] = "UP"

                print(
                    f"[RECOVERED] {name}: "
                    "Recovery email sent"
                )

            else:

                print(
                    f"[EMAIL RETRY] "
                    f"{name}: Recovery email failed"
                )

        except Exception as email_error:

            print(
                f"[EMAIL ERROR] "
                f"{name}: {email_error}"
            )

        return

    # ======================================
    # FIRST HEALTHY CHECK
    # ======================================

    if previous_status is None:

        website_status[name] = "UP"

    # ======================================
    # NORMAL HEALTHY STATUS
    # ======================================

    print(
        f"[HEALTHY] {name} | "
        f"HTTP {result['status_code']} | "
        f"{result['response_time_ms']} ms"
    )


# ==========================================
# MAIN WEBSITE MONITOR
# ==========================================

async def monitor_websites():

    enabled_websites = [
        website
        for website in WEBSITES
        if website.get("enabled", True)
    ]

    if not enabled_websites:

        print(
            "[SentinelAI] No websites configured."
        )

        return

    print(
        "[SentinelAI] Website monitoring started."
    )

    print(
        f"[SentinelAI] Checking every "
        f"{CHECK_INTERVAL} seconds."
    )

    print(
        "[SentinelAI] Repeated DOWN email alerts enabled."
    )

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:

        while True:

            results = await asyncio.gather(
                *[
                    check_website(client, website)
                    for website in enabled_websites
                ]
            )

            for website, result in zip(
                enabled_websites,
                results
            ):

                # Save every check to SQLite.

                try:

                    save_website_check(result)

                except Exception as database_error:

                    print(
                        f"[DATABASE ERROR] "
                        f"{website['name']}: {database_error}"
                    )

                # Process website status and emails.

                process_result(
                    result,
                    website
                )

            await asyncio.sleep(
                CHECK_INTERVAL
            )


# ==========================================
# START MONITOR
# ==========================================

if __name__ == "__main__":

    try:

        asyncio.run(
            monitor_websites()
        )

    except KeyboardInterrupt:

        print(
            "\n[SentinelAI] Website monitoring stopped."
        )
