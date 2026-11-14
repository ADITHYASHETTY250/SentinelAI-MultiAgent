
import win32evtlog
from datetime import datetime, timezone


def collect_windows_events(log_type="System", max_events=20):
    server = "localhost"
    handle = None
    events = []

    try:
        handle = win32evtlog.OpenEventLog(server, log_type)

        flags = (
            win32evtlog.EVENTLOG_BACKWARDS_READ
            | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        )

        records = win32evtlog.ReadEventLog(
            handle, flags, 0
        )

        for event in (records or [])[:max_events]:
            events.append({
                "log_type": log_type,
                "event_id": event.EventID & 0xFFFF,
                "source": event.SourceName,
                "event_type": event.EventType,
                "record_number": event.RecordNumber,
                "timestamp": datetime.fromtimestamp(
                    event.TimeGenerated.timestamp(),
                    tz=timezone.utc
                ).isoformat(),
                "message": str(event.StringInserts or []),
            })

    except Exception as error:
        print(f"[SentinelAI] Event collection error: {error}")

    finally:
        if handle:
            win32evtlog.CloseEventLog(handle)

    return events


if __name__ == "__main__":
    results = collect_windows_events()

    print("\n===== WINDOWS EVENT LOGS =====")

    for event in results:
        print(
            f"ID: {event['event_id']} | "
            f"Source: {event['source']} | "
            f"Record: {event['record_number']}"
        )

    print(f"\nTotal events collected: {len(results)}")
