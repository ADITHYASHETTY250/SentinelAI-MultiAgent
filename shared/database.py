
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "sentinelai.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                ram_percent REAL,
                disk_percent REAL,
                health_status TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS ai_investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER,
                incident_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                ai_analysis TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'COMPLETED',
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(id)
            )
        """)

        # Security alert history
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                evidence TEXT,
                source TEXT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'NEW',
                email_sent INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Website monitoring history
        connection.execute("""
            CREATE TABLE IF NOT EXISTS website_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_name TEXT NOT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms REAL,
                error TEXT,
                checked_at TEXT NOT NULL
            )
        """)

        connection.commit()

    finally:
        connection.close()


# ==========================================
# HEARTBEAT FUNCTIONS
# ==========================================

def save_heartbeat(message):
    connection = get_connection()

    try:
        metrics = message["metrics"]
        health = message["health"]

        connection.execute("""
            INSERT INTO heartbeats (
                agent_name, timestamp, cpu_percent,
                ram_percent, disk_percent, health_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message["agent_name"],
            metrics["timestamp"],
            metrics["cpu_percent"],
            metrics["ram_percent"],
            metrics["disk_percent"],
            health["status"]
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================
# INCIDENT FUNCTIONS
# ==========================================

def create_incident(incident_type, severity, description):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            INSERT INTO incidents (
                incident_type, severity, description,
                status, created_at
            )
            VALUES (?, ?, ?, 'OPEN', ?)
        """, (
            incident_type,
            severity,
            description,
            datetime.now(timezone.utc).isoformat()
        ))

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def has_open_incident(incident_type):
    connection = get_connection()

    try:
        result = connection.execute("""
            SELECT id FROM incidents
            WHERE incident_type = ?
            AND status = 'OPEN'
            LIMIT 1
        """, (incident_type,)).fetchone()

        return result is not None

    finally:
        connection.close()


def resolve_incident(incident_type):
    connection = get_connection()

    try:
        connection.execute("""
            UPDATE incidents
            SET status = 'RESOLVED', resolved_at = ?
            WHERE incident_type = ?
            AND status = 'OPEN'
        """, (
            datetime.now(timezone.utc).isoformat(),
            incident_type
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================
# AI INVESTIGATION FUNCTIONS
# ==========================================

def save_ai_investigation(
    incident_id, incident_type, severity, ai_analysis
):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            INSERT INTO ai_investigations (
                incident_id, incident_type, severity,
                ai_analysis, status, created_at
            )
            VALUES (?, ?, ?, ?, 'COMPLETED', ?)
        """, (
            incident_id,
            incident_type,
            severity,
            ai_analysis,
            datetime.now(timezone.utc).isoformat()
        ))

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_ai_investigations():
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT * FROM ai_investigations
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ==========================================
# SECURITY ALERT FUNCTIONS
# ==========================================

def save_security_alert(
    alert_type,
    severity,
    evidence,
    source="Windows/Sample Logs",
    email_sent=False,
    timestamp=None
):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            INSERT INTO security_alerts (
                alert_type, severity, evidence,
                source, timestamp, email_sent
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert_type,
            severity,
            evidence,
            source,
            timestamp or datetime.now(timezone.utc).isoformat(),
            int(email_sent)
        ))

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_security_alerts():
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT * FROM security_alerts
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ==========================================
# WEBSITE MONITORING FUNCTIONS
# ==========================================

def save_website_check(result):
    connection = get_connection()

    try:
        status = "DOWN" if result.get("error") else "UP"

        connection.execute("""
            INSERT INTO website_checks (
                website_name,
                url,
                status,
                status_code,
                response_time_ms,
                error,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result["name"],
            result["url"],
            status,
            result.get("status_code"),
            result.get("response_time_ms"),
            result.get("error"),
            result["checked_at"]
        ))

        connection.commit()

    finally:
        connection.close()


def get_website_checks():
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT * FROM website_checks
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_latest_website_checks():
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT wc.*
            FROM website_checks wc
            INNER JOIN (
                SELECT url, MAX(id) AS latest_id
                FROM website_checks
                GROUP BY url
            ) latest
            ON wc.id = latest.latest_id
            ORDER BY wc.website_name
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()
