
import json
from production_agent.monitor import get_system_health


def main():
    print("\n===== SENTINELAI PRODUCTION MONITOR =====")

    report = get_system_health()

    print(json.dumps(report, indent=4))

    print("\n===== MONITORING TEST COMPLETED =====")


if __name__ == "__main__":
    main()
