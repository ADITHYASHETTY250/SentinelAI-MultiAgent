
from development_agent.ai_client import generate_ai_response

prompt = """
You are SentinelAI, an AI production reliability engineer.

A production server has the following metrics:
CPU: 95%
RAM: 88%
Disk: 60%

Explain the possible issue and suggest safe troubleshooting steps.
Do not execute any system changes.
"""

try:
    result = generate_ai_response(prompt)

    print("\n========== SENTINELAI AI REPORT ==========\n")
    print(result)

except Exception as error:
    print("AI TEST FAILED:", error)
