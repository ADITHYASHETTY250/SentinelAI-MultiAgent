
import psutil
import platform
import socket
from datetime import datetime, timezone

from remote_agent.config import (
    CPU_THRESHOLD,
    RAM_THRESHOLD,
    DISK_THRESHOLD,
)


def collect_system_metrics():
    cpu_usage = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()

    disk = psutil.disk_usage("C:\\")

    metrics = {
        "server_name": socket.gethostname(),
        "operating_system": platform.platform(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_usage": cpu_usage,
        "ram_usage": memory.percent,
        "disk_usage": disk.percent,
        "ram_total_gb": round(memory.total / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
    }

    return metrics


def check_system_health(metrics):
    alerts = []

    if metrics["cpu_usage"] >= CPU_THRESHOLD:
        alerts.append("HIGH CPU USAGE")

    if metrics["ram_usage"] >= RAM_THRESHOLD:
        alerts.append("HIGH RAM USAGE")

    if metrics["disk_usage"] >= DISK_THRESHOLD:
        alerts.append("HIGH DISK USAGE")

    return {
        "healthy": len(alerts) == 0,
        "alerts": alerts,
    }


if __name__ == "__main__":
    data = collect_system_metrics()

    print("\n===== SENTINELAI REMOTE AGENT =====")
    print("Server:", data["server_name"])
    print("OS:", data["operating_system"])
    print("CPU:", data["cpu_usage"], "%")
    print("RAM:", data["ram_usage"], "%")
    print("Disk:", data["disk_usage"], "%")

    health = check_system_health(data)

    print("Health:", "HEALTHY" if health["healthy"] else "WARNING")
    print("Alerts:", health["alerts"])
