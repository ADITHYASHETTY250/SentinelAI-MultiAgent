
import asyncio
from pathlib import Path

from development_agent.security_monitor import (
    analyze_log_line,
    notify_security_alert,
)
from development_agent.website_config import WEBSITES

LOG_FILES = [
    Path("sample_logs/test_security.log"),
]

CHECK_INTERVAL = 10

file_positions = {}


async def watch_log_file(file_path):
    if not file_path.exists():
        print(f"[WAITING] Log file not found: {file_path}")
        return

    previous_position = file_positions.get(str(file_path), 0)
    current_size = file_path.stat().st_size

    # Detect file truncation or replacement.
    if current_size < previous_position:
        previous_position = 0

    with file_path.open("r", encoding="utf-8", errors="ignore") as log_file:
        log_file.seek(previous_position)

        for line in log_file:
            alerts = analyze_log_line(line)

            for alert in alerts:
                print(
                    f"[SECURITY DETECTED] "
                    f"{alert['severity']} | {alert['alert_type']}"
                )

                notify_security_alert(
                    alert,
                    WEBSITES[0]["owner_email"],
                )

        file_positions[str(file_path)] = log_file.tell()


async def monitor_logs():
    print("[SentinelAI] Continuous security log monitoring started")

    while True:
        for file_path in LOG_FILES:
            try:
                await watch_log_file(file_path)
            except OSError as error:
                print(f"[LOG ERROR] {file_path}: {error}")

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor_logs())
