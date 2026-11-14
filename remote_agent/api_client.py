
import requests

from remote_agent.config import BACKEND_URL


def check_backend_connection():
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/health",
            timeout=5
        )
        response.raise_for_status()
        return True

    except requests.RequestException as error:
        print("[SentinelAI] Connection failed:", error)
        return False


def send_agent_data(data):
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/remote-agent/data",
            json=data,
            timeout=10
        )

        response.raise_for_status()

        print("[SentinelAI] Data successfully transmitted!")
        print("Response:", response.json())

        return True

    except requests.RequestException as error:
        print("[SentinelAI] Data transmission failed:", error)
        return False


if __name__ == "__main__":
    from remote_agent.system_monitor import collect_system_metrics

    metrics = collect_system_metrics()

    metrics["event_type"] = "SYSTEM_METRICS"

    send_agent_data(metrics)