
import time
from datetime import datetime, timezone

from remote_agent.config import (
    HEARTBEAT_INTERVAL,
    AGENT_NAME,
    AGENT_ID,
    SERVER_NAME,
)

from remote_agent.system_monitor import (
    collect_system_metrics,
    check_system_health,
)

from remote_agent.api_client import (
    check_backend_connection,
    send_agent_data,
)


def run_agent():
    print("=" * 50)
    print("       SENTINELAI REMOTE WINDOWS AGENT")
    print("=" * 50)

    print(f"Agent: {AGENT_NAME}")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Server: {SERVER_NAME}")
    print(f"Heartbeat interval: {HEARTBEAT_INTERVAL} seconds")

    print("\nConnecting to SentinelAI backend...")

    if not check_backend_connection():
        print("[SentinelAI] Backend unavailable.")
        print("[SentinelAI] Agent will retry automatically.")

    print("\nRemote monitoring started.\n")

    while True:
        try:
            metrics = collect_system_metrics()

            health = check_system_health(metrics)

            payload = {
                **metrics,
                "agent_id": AGENT_ID,
                "agent_name": AGENT_NAME,
                "server_name": SERVER_NAME,
                "event_type": "SYSTEM_METRICS",
                "health_status": (
                    "HEALTHY" if health["healthy"] else "WARNING"
                ),
                "alerts": health["alerts"],
                "agent_timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            print("-" * 50)
            print(f"Server: {SERVER_NAME}")
            print(f"CPU: {metrics['cpu_usage']}%")
            print(f"RAM: {metrics['ram_usage']}%")
            print(f"Disk: {metrics['disk_usage']}%")
            print(f"Health: {payload['health_status']}")

            if health["alerts"]:
                print("Alerts:", health["alerts"])

            success = send_agent_data(payload)

            if success:
                print("[SentinelAI] Heartbeat sent successfully.")
            else:
                print("[SentinelAI] Heartbeat transmission failed.")

            time.sleep(HEARTBEAT_INTERVAL)

        except KeyboardInterrupt:
            print("\n[SentinelAI] Remote agent stopped.")
            break

        except Exception as error:
            print(f"[SentinelAI] Monitoring error: {error}")
            time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    run_agent()
