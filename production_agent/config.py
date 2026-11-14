
import os

# Production monitoring configuration

AGENT_NAME = "SentinelAI-Production-Agent"

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 5

# System monitoring thresholds
CPU_THRESHOLD = 85.0
RAM_THRESHOLD = 85.0
DISK_THRESHOLD = 90.0

# Communication settings
DEVELOPMENT_AGENT_URL = os.getenv(
    "DEVELOPMENT_AGENT_URL",
    "http://127.0.0.1:8001"
)

# Monitoring mode
MONITORING_ENABLED = True
