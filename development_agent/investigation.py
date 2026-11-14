
import json
from datetime import datetime, timezone

from development_agent.ai_client import generate_ai_response


# ==========================================
# SENTINELAI AI INVESTIGATION ENGINE
# ==========================================

def build_investigation_prompt(incident, metrics, logs=None):
    """
    Build a detailed AI incident investigation prompt.
    """

    incident_data = {
        "incident_type": incident.get(
            "incident_type", "Unknown"
        ),
        "severity": incident.get(
            "severity", "Unknown"
        ),
        "description": incident.get(
            "description", "No description available"
        ),
    }

    system_metrics = {
        "cpu_percent": metrics.get(
            "cpu_percent", None
        ),
        "ram_percent": metrics.get(
            "ram_percent", None
        ),
        "disk_percent": metrics.get(
            "disk_percent", None
        ),
        "timestamp": metrics.get(
            "timestamp", "Unknown"
        ),
    }

    production_logs = (
        logs if logs else "No production logs provided."
    )

    current_time = datetime.now(
        timezone.utc
    ).isoformat()

    prompt = f"""
You are SENTINELAI, an expert AI Production Reliability
Engineer and Site Reliability Engineering (SRE) analyst.

Your responsibility is to investigate production incidents,
analyze system health, identify possible root causes,
and recommend safe corrective actions.

You are assisting a human system administrator.

==================================================
INVESTIGATION CONTEXT
==================================================

Investigation Time:
{current_time}

INCIDENT INFORMATION:

{json.dumps(incident_data, indent=2)}

SYSTEM METRICS:

{json.dumps(system_metrics, indent=2)}

PRODUCTION LOGS:

{production_logs}

==================================================
YOUR INVESTIGATION TASKS
==================================================

Analyze the incident carefully and generate a detailed
production incident investigation report.

1. INCIDENT SUMMARY

- Explain what happened.
- Explain what the incident indicates.
- Describe the current severity.

2. ROOT CAUSE ANALYSIS

- Identify possible reasons for the incident.
- Connect your analysis to the supplied metrics and logs.
- Clearly distinguish confirmed evidence from hypotheses.
- Do not invent missing information.

3. SYSTEM HEALTH ANALYSIS

Analyze the available:

- CPU utilization.
- RAM utilization.
- Disk utilization.
- Relevant production logs.

Explain whether the available information indicates
normal operation or possible abnormal behavior.

If information is unavailable, mention it explicitly.

4. PRODUCTION IMPACT

Explain the possible effects on:

- Application performance.
- Service availability.
- Server stability.
- User experience.

Do not claim an impact has occurred unless evidence supports it.

5. SEVERITY ASSESSMENT

Evaluate the supplied severity.

Explain why the incident may be LOW, MEDIUM, HIGH,
or CRITICAL.

Do not silently change the recorded incident severity.
If you disagree with it, explain why.

6. RECOMMENDED RECOVERY ACTIONS

Provide practical troubleshooting steps in priority order.

For every recommendation, explain:

- What the administrator should do.
- Why the action is recommended.
- What result to expect.

Prefer safe diagnostic commands and read-only checks.

7. PREVENTION STRATEGY

Suggest practical ways to prevent similar incidents.

8. CONFIDENCE AND MISSING INFORMATION

Provide:

- Confidence level: LOW, MEDIUM, or HIGH.
- Evidence supporting the investigation.
- Missing information required for better diagnosis.

Confidence must reflect the available evidence.
Do not present guesses as confirmed facts.

==================================================
SAFETY REQUIREMENTS
==================================================

- Never execute commands or modify production systems.
- Never recommend destructive operations.
- Never restart or terminate production services automatically.
- Human administrator approval is mandatory for changes.
- Do not expose credentials, passwords, API keys or secrets.
- Do not invent metrics, logs or incident details.
- Clearly identify assumptions and uncertainty.

==================================================
RESPONSE FORMAT
==================================================

Return a professional Markdown report using these headings:

# AI Incident Investigation

## 1. Incident Summary

## 2. Root Cause Analysis

## 3. System Health Analysis

## 4. Production Impact

## 5. Severity Assessment

## 6. Recommended Recovery Actions

## 7. Prevention Strategy

## 8. Confidence and Missing Information

## 9. Final Recommendation

Make the report concise, technically accurate,
actionable and understandable to a system administrator.
"""

    return prompt


# ==========================================
# INVESTIGATE PRODUCTION INCIDENT
# ==========================================

def investigate_incident(incident, metrics, logs=None):
    """
    Investigate an incident using the configured Gemini AI client.

    Returns a structured Python result while preserving
    compatibility with the existing backend.
    """

    try:

        prompt = build_investigation_prompt(
            incident,
            metrics,
            logs
        )

        # Generate AI investigation using existing Gemini client.

        ai_report = generate_ai_response(prompt)

        if not ai_report:

            raise ValueError(
                "Gemini returned an empty investigation report."
            )

        return {
            "incident_type": incident.get(
                "incident_type", "Unknown"
            ),

            "severity": incident.get(
                "severity", "Unknown"
            ),

            "ai_analysis": ai_report,

            "status": "completed",

            "investigation_time": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except Exception as error:

        print(
            f"[SENTINELAI AI ERROR] "
            f"Incident investigation failed: {error}"
        )

        return {
            "incident_type": incident.get(
                "incident_type", "Unknown"
            ),

            "severity": incident.get(
                "severity", "Unknown"
            ),

            "ai_analysis": (
                "AI investigation could not be completed.\n\n"
                f"Error: {str(error)}\n\n"
                "Please check the Gemini API connection "
                "and retry the investigation."
            ),

            "status": "failed",

            "investigation_time": datetime.now(
                timezone.utc
            ).isoformat(),
        }
