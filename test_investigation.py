
from development_agent.investigation import investigate_incident

incident = {
    "incident_type": "High CPU Usage",
    "severity": "CRITICAL",
    "description": "Production server CPU usage reached 95%."
}

metrics = {
    "cpu_percent": 95,
    "ram_percent": 88,
    "disk_percent": 60
}

print("\nTesting SentinelAI incident investigation...\n")

result = investigate_incident(incident, metrics)

print("\n========== INVESTIGATION RESULT ==========\n")

print("Status:", result.get("status"))
print("Incident:", result.get("incident_type"))
print("\nAI REPORT:\n")
print(result.get("ai_analysis"))
