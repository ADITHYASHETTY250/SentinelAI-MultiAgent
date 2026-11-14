
import time
import win32evtlog

from development_agent.security_monitor import notify_security_alert
from development_agent.website_config import WEBSITES

SERVER = "localhost"
LOG_TYPE = "Security"
CHECK_INTERVAL = 10

SECURITY_EVENTS = {
    4625: ("Failed Windows Login", "HIGH"),
    4720: ("New User Account Created", "HIGH"),
    4722: ("User Account Enabled", "HIGH"),
    4724: ("Password Reset Attempt", "HIGH"),
    4728: ("User Added to Privileged Group", "HIGH"),
    4732: ("User Added to Local Group", "HIGH"),
    1102: ("Windows Security Audit Log Cleared", "CRITICAL"),
}


def process_event(event):
    event_id = event.EventID & 0xFFFF

    if event_id not in SECURITY_EVENTS:
        return

    event_name, severity = SECURITY_EVENTS[event_id]

    alert = {
        "alert_type": event_name,
        "severity": severity,
        "evidence": (
            f"Windows Event ID: {event_id}\n"
            f"Record Number: {event.RecordNumber}\n"
            f"Source: {event.SourceName}"
        ),
        "timestamp": str(event.TimeGenerated),
    }

    print(f"[WINDOWS ALERT] {severity} | {event_name}")

    result = notify_security_alert(
        alert,
        WEBSITES[0]["owner_email"],
    )

    return result


def monitor_windows_events():
    # Start at the latest existing record.
    handle = win32evtlog.OpenEventLog(SERVER, LOG_TYPE)

    try:
        oldest = win32evtlog.GetOldestEventLogRecord(handle)
        count = win32evtlog.GetNumberOfEventLogRecords(handle)
        last_record = oldest + count - 1

    finally:
        win32evtlog.CloseEventLog(handle)

    print("[SentinelAI] Windows Security monitoring started")
    print(f"[SentinelAI] Starting from event record: {last_record}")

    try:
        while True:
            handle = None

            try:
                handle = win32evtlog.OpenEventLog(SERVER, LOG_TYPE)

                flags = (
                    win32evtlog.EVENTLOG_BACKWARDS_READ
                    | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                )

                new_events = []

                while True:
                    events = win32evtlog.ReadEventLog(
                        handle, flags, 0
                    )

                    if not events:
                        break

                    older_records_found = False

                    for event in events:
                        if event.RecordNumber > last_record:
                            new_events.append(event)
                        else:
                            older_records_found = True

                    if older_records_found:
                        break

                # Process oldest new event first.
                new_events.sort(key=lambda event: event.RecordNumber)

                for event in new_events:
                    process_event(event)
                    last_record = max(
                        last_record,
                        event.RecordNumber,
                    )

            except Exception as error:
                print(f"[WINDOWS EVENT ERROR] {error}")

            finally:
                if handle:
                    win32evtlog.CloseEventLog(handle)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n[SentinelAI] Windows monitoring stopped.")


if __name__ == "__main__":
    monitor_windows_events()
