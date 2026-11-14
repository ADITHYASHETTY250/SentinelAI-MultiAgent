
import psutil
import shutil
from datetime import datetime, timezone

from production_agent.config import (
    CPU_THRESHOLD,
    RAM_THRESHOLD,
    DISK_THRESHOLD,
)


def collect_system_metrics():
    """Collect CPU, RAM and disk usage."""

    cpu_usage = psutil.cpu_percent(interval=1)

    memory = psutil.virtual_memory()
    ram_usage = memory.percent

    disk = shutil.disk_usage("C:\\")
    disk_usage = (disk.used / disk.total) * 100

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": cpu_usage,
        "ram_percent": ram_usage,
        "disk_percent": round(disk_usage, 2),
    }


def evaluate_health(metrics):
    """Evaluate system metrics against configured thresholds."""

    issues = []

    if metrics["cpu_percent"] > CPU_THRESHOLD:
        issues.append("High CPU usage")

    if metrics["ram_percent"] > RAM_THRESHOLD:
        issues.append("High RAM usage")

    if metrics["disk_percent"] > DISK_THRESHOLD:
        issues.append("High disk usage")

    return {
        "status": "unhealthy" if issues else "healthy",
        "issues": issues,
    }


def get_system_health():
    metrics = collect_system_metrics()
    health = evaluate_health(metrics)

    return {
        "agent": "SentinelAI-Production-Agent",
        "metrics": metrics,
        "health": health,
    }
