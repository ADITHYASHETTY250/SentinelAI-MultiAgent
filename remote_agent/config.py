
import os
import platform
import socket

# SentinelAI Remote Agent Configuration

AGENT_NAME = "SentinelAI-Windows-Agent"

AGENT_ID = socket.gethostname()

SERVER_NAME = socket.gethostname()

OPERATING_SYSTEM = platform.platform()

BACKEND_URL = os.getenv(
    "SENTINELAI_BACKEND_URL",
    "http://127.0.0.1:8001"
)

API_KEY = os.getenv("SENTINELAI_AGENT_API_KEY", "")

HEARTBEAT_INTERVAL = 10

LOG_SCAN_INTERVAL = 10

MONITORING_ENABLED = True

CPU_THRESHOLD = 85.0
RAM_THRESHOLD = 85.0
DISK_THRESHOLD = 90.0
