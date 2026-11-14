
import os
from datetime import datetime, timezone

# Configure log files to monitor
LOG_FILES = [
    r"D:\PROJECTS\SentinelAI-MultiAgent\logs\application.log",
]


def collect_file_logs(max_lines=50):
    collected_logs = []

    for file_path in LOG_FILES:

        if not os.path.isfile(file_path):
            continue

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as file:

                lines = file.readlines()[-max_lines:]

                for line in lines:
                    line = line.strip()

                    if line:
                        collected_logs.append({
                            "file": file_path,
                            "message": line,
                            "collected_at": datetime.now(
                                timezone.utc
                            ).isoformat()
                        })

        except PermissionError:
            print(f"[SentinelAI] Permission denied: {file_path}")

        except OSError as error:
            print(f"[SentinelAI] Cannot read {file_path}: {error}")

    return collected_logs


if __name__ == "__main__":
    logs = collect_file_logs()

    print("\n===== APPLICATION LOG MONITOR =====")

    for log in logs:
        print(f"File: {log['file']}")
        print(f"Message: {log['message']}")
        print("-" * 50)

    print(f"\nTotal log entries: {len(logs)}")
