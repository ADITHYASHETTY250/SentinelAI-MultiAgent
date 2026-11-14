
import time
import logging
import requests

from production_agent.config import (
    AGENT_NAME,
    HEARTBEAT_INTERVAL,
    DEVELOPMENT_AGENT_URL,
)
from production_agent.monitor import get_system_health


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def send_heartbeat():
    """Collect system health and send it to the Development Agent."""

    report = get_system_health()

    payload = {
        "agent_name": AGENT_NAME,
        "event_type": "heartbeat",
        **report,
    }

    endpoint = f"{DEVELOPMENT_AGENT_URL}/api/heartbeat"

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=5,
        )

        response.raise_for_status()

        logging.info(
            "Heartbeat sent successfully | Status: %s",
            report["health"]["status"],
        )

    except requests.RequestException as error:
        logging.warning(
            "Could not reach Development Agent: %s",
            error,
        )


def start_heartbeat():
    """Send heartbeats continuously at the configured interval."""

    logging.info("%s started", AGENT_NAME)

    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    try:
        start_heartbeat()
    except KeyboardInterrupt:
        logging.info("Heartbeat service stopped.")
