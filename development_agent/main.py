import json
import asyncio

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.database import (
    initialize_database,
    save_heartbeat,
    get_connection,
    create_incident,
    has_open_incident,
    resolve_incident,
    save_ai_investigation,
    get_ai_investigations,
    get_security_alerts,
    get_website_checks,
    get_latest_website_checks,
)

from development_agent.investigation import investigate_incident
from development_agent.email_alerts import send_alert_email


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

initialize_database()


# ==========================================
# CONFIGURATION
# ==========================================

HEARTBEAT_TIMEOUT = 15

REMOTE_AGENT_TIMEOUT = 30
REMOTE_MONITOR_INTERVAL = 5

OFFLINE_INCIDENT_TYPE = "AGENT_OFFLINE"
OFFLINE_INCIDENT_SEVERITY = "CRITICAL"

INCIDENT_MAPPING = {
    "High CPU usage": ("CPU_HIGH", "HIGH"),
    "High RAM usage": ("RAM_HIGH", "HIGH"),
    "High disk usage": ("DISK_HIGH", "HIGH"),
}

# Tracks previous remote server status.
# Prevents duplicate remote status-change emails.
remote_agent_status_cache = {}

# Stores the latest production heartbeat.
latest_heartbeat = None


# ==========================================
# ENSURE REMOTE DATABASE TABLE
# ==========================================

def ensure_remote_agent_table():

    conn = get_connection()

    try:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS remote_agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT,
                event_type TEXT,
                payload TEXT,
                received_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    finally:

        conn.close()


ensure_remote_agent_table()


# ==========================================
# HEARTBEAT MESSAGE MODEL
# ==========================================

class HeartbeatMessage(BaseModel):

    agent_name: str
    event_type: str
    agent: str
    metrics: dict[str, Any]
    health: dict[str, Any]


# ==========================================
# AI INCIDENT INVESTIGATION AND DATABASE SAVE
# ==========================================

def investigate_and_save(
    incident_id,
    incident_type,
    severity,
    description,
    metrics,
):

    try:

        incident = {
            "incident_type": incident_type,
            "severity": severity,
            "description": description,
        }

        # OpenRouter DeepSeek is the primary provider.
        # Gemini is used automatically if OpenRouter fails.
        investigation = investigate_incident(
            incident,
            metrics,
        )

        # Validate the investigation response.
        if not isinstance(investigation, dict):

            raise ValueError(
                "AI investigation returned an invalid response."
            )

        # Do not save failed investigations.
        if investigation.get("status") != "completed":

            error_message = investigation.get(
                "ai_analysis",
                "AI investigation was unsuccessful."
            )

            print(
                f"[AI INVESTIGATION FAILED] "
                f"{incident_type}: {error_message}"
            )

            return {
                "success": False,
                "status": "failed",
                "error": error_message,
            }

        # Validate the generated report.
        ai_analysis = investigation.get("ai_analysis")

        if not isinstance(ai_analysis, str) or not ai_analysis.strip():

            print(
                f"[AI INVESTIGATION FAILED] "
                f"Empty report for {incident_type}"
            )

            return {
                "success": False,
                "status": "failed",
                "error": "AI returned an empty investigation report.",
            }

        # Save the completed report to SQLite.
        report_id = save_ai_investigation(
            incident_id,
            incident_type,
            severity,
            ai_analysis,
        )

        if report_id is None:

            raise RuntimeError(
                "Database did not return an investigation report ID."
            )

        print(
            f"[AI INVESTIGATION SUCCESS] "
            f"{incident_type} | Report ID: {report_id}"
        )

        return {
            "success": True,
            "status": "completed",
            "report_id": report_id,
            "incident_type": incident_type,
        }

    except Exception as error:

        print(
            f"[AI INVESTIGATION ERROR] "
            f"{incident_type}: {error}"
        )

        return {
            "success": False,
            "status": "failed",
            "error": str(error),
        }


# ==========================================
# PRODUCTION HEARTBEAT TIMEOUT DETECTION
# ==========================================

def check_heartbeat_timeout():

    global latest_heartbeat

    if latest_heartbeat is None:
        return False

    try:

        last_timestamp = datetime.fromisoformat(
            latest_heartbeat["metrics"]["timestamp"]
        )

        if last_timestamp.tzinfo is None:

            last_timestamp = last_timestamp.replace(
                tzinfo=timezone.utc
            )

        current_time = datetime.now(timezone.utc)

        time_difference = (
            current_time - last_timestamp
        ).total_seconds()

        if time_difference > HEARTBEAT_TIMEOUT:

            if not has_open_incident(OFFLINE_INCIDENT_TYPE):

                incident_id = create_incident(
                    OFFLINE_INCIDENT_TYPE,
                    OFFLINE_INCIDENT_SEVERITY,
                    "Production Agent stopped sending heartbeats",
                )

                investigate_and_save(
                    incident_id,
                    OFFLINE_INCIDENT_TYPE,
                    OFFLINE_INCIDENT_SEVERITY,
                    "Production Agent stopped sending heartbeats",
                    latest_heartbeat.get("metrics", {}),
                )

                print(
                    "[CRITICAL INCIDENT] "
                    "Production Agent is offline"
                )

            return True

        return False

    except Exception as error:

        print(
            f"[HEARTBEAT MONITOR ERROR] {error}"
        )

        return False


# ==========================================
# REMOTE SERVER EMAIL MONITOR
# ==========================================

def check_remote_server_email_alerts():

    conn = get_connection()

    try:

        rows = conn.execute("""
            SELECT
                e.server_name,
                e.payload,
                e.received_at

            FROM remote_agent_events e

            INNER JOIN (
                SELECT
                    server_name,
                    MAX(id) AS latest_id

                FROM remote_agent_events

                WHERE event_type = 'SYSTEM_METRICS'

                GROUP BY server_name

            ) latest

            ON e.id = latest.latest_id

            ORDER BY e.server_name

        """).fetchall()

    finally:

        conn.close()

    current_time = datetime.now(timezone.utc)

    for row in rows:

        server_name = row["server_name"]

        try:

            received_at = datetime.fromisoformat(
                row["received_at"].replace("Z", "+00:00")
            )

            if received_at.tzinfo is None:

                received_at = received_at.replace(
                    tzinfo=timezone.utc
                )

            age_seconds = (
                current_time - received_at
            ).total_seconds()

        except Exception as error:

            print(
                f"[REMOTE MONITOR ERROR] "
                f"{server_name}: {error}"
            )

            continue

        # Determine current remote server status.
        current_status = (
            "OFFLINE"
            if age_seconds > REMOTE_AGENT_TIMEOUT
            else "ONLINE"
        )

        previous_status = remote_agent_status_cache.get(
            server_name
        )

        # Initialize status on first observation.
        # Do not send a false alert for an old record
        # when the backend initially starts.
        if previous_status is None:

            remote_agent_status_cache[server_name] = (
                current_status
            )

            print(
                f"[REMOTE STATUS INITIALIZED] "
                f"{server_name}: {current_status}"
            )

            continue

        # No status change: do not send another email.
        if previous_status == current_status:
            continue

        # ======================================
        # REMOTE SERVER OFFLINE
        # ======================================

        if current_status == "OFFLINE":

            subject = (
                f"CRITICAL: Remote Server OFFLINE - "
                f"{server_name}"
            )

            body = (
                "SENTINELAI REMOTE SERVER ALERT\n\n"
                f"Server Name: {server_name}\n"
                "Status: OFFLINE\n"
                f"Last Heartbeat: {row['received_at']}\n"
                f"Seconds Since Heartbeat: "
                f"{age_seconds:.1f}\n\n"
                "SentinelAI detected that the remote "
                "agent stopped sending heartbeats.\n\n"
                "Possible reasons:\n"
                "- Remote machine is powered off.\n"
                "- Remote agent process stopped.\n"
                "- Network connection failed.\n\n"
                "Recommended Action:\n"
                "Check the remote machine, agent process "
                "and network connectivity."
            )

            result = send_alert_email(
                None,
                subject,
                body,
            )

            print(
                f"[REMOTE EMAIL] {result}"
            )

            if result.get("success"):

                remote_agent_status_cache[server_name] = (
                    "OFFLINE"
                )

                print(
                    f"[REMOTE OFFLINE] {server_name}"
                )

            else:

                print(
                    f"[REMOTE EMAIL FAILED] "
                    f"{server_name}"
                )

        # ======================================
        # REMOTE SERVER RECOVERED
        # ======================================

        elif current_status == "ONLINE":

            subject = (
                f"RECOVERED: Remote Server ONLINE - "
                f"{server_name}"
            )

            body = (
                "SENTINELAI REMOTE SERVER RECOVERY\n\n"
                f"Server Name: {server_name}\n"
                "Status: ONLINE\n"
                f"Latest Heartbeat: {row['received_at']}\n\n"
                "The remote agent has started sending "
                "heartbeats again.\n\n"
                "Remote server monitoring has resumed "
                "successfully."
            )

            result = send_alert_email(
                None,
                subject,
                body,
            )

            print(
                f"[REMOTE EMAIL] {result}"
            )

            if result.get("success"):

                remote_agent_status_cache[server_name] = (
                    "ONLINE"
                )

                print(
                    f"[REMOTE RECOVERED] {server_name}"
                )

            else:

                print(
                    f"[REMOTE RECOVERY EMAIL FAILED] "
                    f"{server_name}"
                )


# ==========================================
# AUTOMATIC BACKGROUND MONITOR
# ==========================================

async def heartbeat_monitor():

    print(
        "SentinelAI background heartbeat monitor started"
    )

    print(
        "Remote server email monitoring enabled"
    )

    while True:

        try:

            # Production agent monitoring.
            check_heartbeat_timeout()

            # Remote server email monitoring.
            check_remote_server_email_alerts()

        except Exception as error:

            print(
                f"Background monitor error: {error}"
            )

        await asyncio.sleep(
            REMOTE_MONITOR_INTERVAL
        )


# ==========================================
# FASTAPI LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    monitor_task = asyncio.create_task(
        heartbeat_monitor()
    )

    try:

        yield

    finally:

        monitor_task.cancel()

        try:

            await monitor_task

        except asyncio.CancelledError:

            print(
                "SentinelAI background monitor stopped"
            )


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="SentinelAI Development Agent",
    description=(
        "Multi-Agent Production Monitoring "
        "and Recovery System"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# HOME ENDPOINT
# ==========================================

@app.get("/")
def home():

    return {
        "project": "SentinelAI",
        "agent": "Development Agent",
        "message": "SentinelAI Development Agent is running",
        "status": "online",
    }


# ==========================================
# DEVELOPMENT AGENT HEALTH
# ==========================================

@app.get("/api/health")
def health_check():

    return {
        "agent": "SentinelAI Development Agent",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
# ==========================================
# INCIDENT DETECTION
# ==========================================

def detect_incidents(heartbeat_data):

    issues = heartbeat_data["health"].get(
        "issues", []
    )

    created_incidents = []
    resolved_incidents = []
    investigation_results = []

    for issue in issues:

        incident_type, severity = INCIDENT_MAPPING.get(
            issue,
            ("SYSTEM_WARNING", "MEDIUM"),
        )

        if not has_open_incident(incident_type):

            incident_id = create_incident(
                incident_type,
                severity,
                issue,
            )

            created_incidents.append(
                incident_type
            )

            result = investigate_and_save(
                incident_id,
                incident_type,
                severity,
                issue,
                heartbeat_data.get("metrics", {}),
            )

            investigation_results.append({
                "incident_type": incident_type,
                **result,
            })

    active_incident_types = {
        INCIDENT_MAPPING[issue][0]
        for issue in issues
        if issue in INCIDENT_MAPPING
    }

    for incident_type, severity in INCIDENT_MAPPING.values():

        if incident_type not in active_incident_types:

            if has_open_incident(incident_type):

                resolve_incident(incident_type)

                resolved_incidents.append(
                    incident_type
                )

    return {
        "created": created_incidents,
        "resolved": resolved_incidents,
        "investigations": investigation_results,
    }


# ==========================================
# RECEIVE PRODUCTION HEARTBEAT
# ==========================================

@app.post("/api/heartbeat")
def receive_heartbeat(message: HeartbeatMessage):

    global latest_heartbeat

    heartbeat_data = message.model_dump()

    latest_heartbeat = heartbeat_data

    if has_open_incident(OFFLINE_INCIDENT_TYPE):

        resolve_incident(
            OFFLINE_INCIDENT_TYPE
        )

        print(
            "RECOVERY: Production Agent is back online"
        )

    save_heartbeat(heartbeat_data)

    incident_updates = detect_incidents(
        heartbeat_data
    )

    print(
        "\n========== HEARTBEAT RECEIVED =========="
    )

    print(f"Agent: {message.agent_name}")
    print(f"Health: {message.health['status']}")
    print(f"Metrics: {message.metrics}")
    print(f"Incident Updates: {incident_updates}")

    print(
        "========================================\n"
    )

    return {
        "success": True,
        "message": (
            "Heartbeat received and stored successfully"
        ),
        "health_status": message.health["status"],
        "incident_updates": incident_updates,
    }


# ==========================================
# GET LATEST HEARTBEAT
# ==========================================

@app.get("/api/heartbeat/latest")
def get_latest_heartbeat():

    if latest_heartbeat is None:

        return {
            "message": "No heartbeat received yet"
        }

    return latest_heartbeat


# ==========================================
# GET PRODUCTION AGENT STATUS
# ==========================================

@app.get("/api/heartbeat/status")
def heartbeat_status():

    if latest_heartbeat is None:

        return {
            "status": "unknown",
            "message": "No heartbeat received yet",
        }

    is_offline = check_heartbeat_timeout()

    last_timestamp = datetime.fromisoformat(
        latest_heartbeat["metrics"]["timestamp"]
    )

    if last_timestamp.tzinfo is None:

        last_timestamp = last_timestamp.replace(
            tzinfo=timezone.utc
        )

    current_time = datetime.now(timezone.utc)

    time_difference = (
        current_time - last_timestamp
    ).total_seconds()

    if is_offline:

        return {
            "status": "offline",
            "message": (
                "Production Agent heartbeat missing"
            ),
            "last_seen_seconds_ago": round(
                time_difference, 2
            ),
        }

    return {
        "status": "online",
        "message": (
            "Production Agent is responding"
        ),
        "last_seen_seconds_ago": round(
            time_difference, 2
        ),
    }


# ==========================================
# GET HEARTBEAT HISTORY
# ==========================================

@app.get("/api/heartbeat/history")
def get_heartbeat_history():

    connection = get_connection()

    try:

        rows = connection.execute("""
            SELECT *
            FROM heartbeats
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

        return {
            "total_records": len(rows),
            "heartbeats": [
                dict(row) for row in rows
            ],
        }

    finally:

        connection.close()


# ==========================================
# GET INCIDENT HISTORY
# ==========================================

@app.get("/api/incidents")
def get_incidents():

    connection = get_connection()

    try:

        rows = connection.execute("""
            SELECT *
            FROM incidents
            ORDER BY id DESC
        """).fetchall()

        return {
            "total_incidents": len(rows),
            "incidents": [
                dict(row) for row in rows
            ],
        }

    finally:

        connection.close()


# ==========================================
# GET OPEN INCIDENTS
# ==========================================

@app.get("/api/incidents/open")
def get_open_incidents():

    connection = get_connection()

    try:

        rows = connection.execute("""
            SELECT *
            FROM incidents
            WHERE status = 'OPEN'
            ORDER BY id DESC
        """).fetchall()

        return {
            "total_open_incidents": len(rows),
            "incidents": [
                dict(row) for row in rows
            ],
        }

    finally:

        connection.close()


# ==========================================
# GET AI INVESTIGATION REPORTS
# ==========================================

@app.get("/api/investigations")
def get_investigations():

    reports = get_ai_investigations()

    return {
        "total_reports": len(reports),
        "investigations": reports,
    }


# ==========================================
# GET SECURITY ALERT HISTORY
# ==========================================

@app.get("/api/security/alerts")
def get_security_alert_history():

    alerts = get_security_alerts()

    return {
        "total_alerts": len(alerts),
        "alerts": alerts,
    }


# ==========================================
# GET SECURITY ALERT SUMMARY
# ==========================================

@app.get("/api/security/alerts/summary")
def get_security_alert_summary():

    connection = get_connection()

    try:

        summary = connection.execute("""
            SELECT
                COUNT(*) AS total_alerts,

                SUM(
                    CASE WHEN severity = 'CRITICAL'
                    THEN 1 ELSE 0 END
                ) AS critical_alerts,

                SUM(
                    CASE WHEN severity = 'HIGH'
                    THEN 1 ELSE 0 END
                ) AS high_alerts,

                SUM(
                    CASE WHEN severity = 'MEDIUM'
                    THEN 1 ELSE 0 END
                ) AS medium_alerts,

                SUM(
                    CASE WHEN severity = 'LOW'
                    THEN 1 ELSE 0 END
                ) AS low_alerts,

                SUM(
                    CASE WHEN status = 'NEW'
                    THEN 1 ELSE 0 END
                ) AS new_alerts,

                SUM(
                    CASE WHEN email_sent = 1
                    THEN 1 ELSE 0 END
                ) AS emails_sent

            FROM security_alerts
        """).fetchone()

        return {
            "total_alerts": summary["total_alerts"] or 0,
            "critical_alerts": summary["critical_alerts"] or 0,
            "high_alerts": summary["high_alerts"] or 0,
            "medium_alerts": summary["medium_alerts"] or 0,
            "low_alerts": summary["low_alerts"] or 0,
            "new_alerts": summary["new_alerts"] or 0,
            "emails_sent": summary["emails_sent"] or 0,
        }

    finally:

        connection.close()
        # ==========================================
# WEBSITE MONITORING - LATEST STATUS
# ==========================================

@app.get("/api/websites")
def get_websites():

    websites = get_latest_website_checks()

    total = len(websites)

    up = sum(
        1 for website in websites
        if website["status"] == "UP"
    )

    down = sum(
        1 for website in websites
        if website["status"] == "DOWN"
    )

    return {
        "total_websites": total,
        "up": up,
        "down": down,
        "websites": websites,
    }


# ==========================================
# WEBSITE MONITORING - COMPLETE HISTORY
# ==========================================

@app.get("/api/websites/history")
def get_website_history():

    history = get_website_checks()

    return {
        "total_checks": len(history),
        "history": history,
    }


# ==========================================
# RECEIVE REMOTE AGENT DATA
# ==========================================

@app.post("/api/remote-agent/data")
def receive_remote_agent_data(data: dict):

    conn = get_connection()

    try:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS remote_agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT,
                event_type TEXT,
                payload TEXT,
                received_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            INSERT INTO remote_agent_events
            (server_name, event_type, payload)
            VALUES (?, ?, ?)
        """, (
            data.get("server_name", "Unknown"),
            data.get("event_type", "UNKNOWN"),
            json.dumps(data),
        ))

        conn.commit()

        return {
            "success": True,
            "message": "Remote agent data received",
            "server_name": data.get("server_name"),
        }

    finally:

        conn.close()


# ==========================================
# GET REMOTE AGENT EVENTS
# ==========================================

@app.get("/api/remote-agent/events")
def get_remote_agent_events():

    conn = get_connection()

    try:

        cursor = conn.execute("""
            SELECT
                id,
                server_name,
                event_type,
                payload,
                received_at

            FROM remote_agent_events

            ORDER BY id DESC
            LIMIT 50
        """)

        rows = cursor.fetchall()

        return {
            "total": len(rows),

            "events": [
                {
                    "id": row[0],
                    "server_name": row[1],
                    "event_type": row[2],
                    "payload": json.loads(row[3]),
                    "received_at": row[4],
                }

                for row in rows
            ],
        }

    finally:

        conn.close()


# ==========================================
# GET REMOTE SERVER STATUS
# ==========================================

@app.get("/api/remote-agent/servers")
def get_remote_servers():

    conn = get_connection()

    try:

        cursor = conn.execute("""
            SELECT
                e.id,
                e.server_name,
                e.event_type,
                e.payload,
                e.received_at

            FROM remote_agent_events e

            INNER JOIN (
                SELECT
                    server_name,
                    MAX(id) AS latest_id

                FROM remote_agent_events

                WHERE event_type = 'SYSTEM_METRICS'

                GROUP BY server_name

            ) latest

            ON e.id = latest.latest_id

            ORDER BY e.server_name
        """)

        rows = cursor.fetchall()

        servers = []

        current_time = datetime.now(timezone.utc)

        for row in rows:

            payload = json.loads(row[3])

            received_at = datetime.fromisoformat(
                row[4].replace("Z", "+00:00")
            )

            if received_at.tzinfo is None:

                received_at = received_at.replace(
                    tzinfo=timezone.utc
                )

            age_seconds = (
                current_time - received_at
            ).total_seconds()

            status = (
                "OFFLINE"
                if age_seconds > REMOTE_AGENT_TIMEOUT
                else "ONLINE"
            )

            servers.append({
                "id": row[0],
                "server_name": row[1],
                "event_type": row[2],
                "payload": payload,
                "last_heartbeat": row[4],
                "status": status,
            })

        return {
            "total_servers": len(servers),

            "online": sum(
                1 for server in servers
                if server["status"] == "ONLINE"
            ),

            "offline": sum(
                1 for server in servers
                if server["status"] == "OFFLINE"
            ),

            "servers": servers,
        }

    finally:

        conn.close()