
import os
import httpx

from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "deepseek/deepseek-v3.2-20251201"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash"

# Initialize Gemini only if an API key exists
gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


def generate_openrouter_response(prompt: str) -> str:
    """Generate a response using OpenRouter."""

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    response = httpx.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=60.0,
    )

    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    if not content:
        raise ValueError("OpenRouter returned an empty response")

    return content


def generate_gemini_response(prompt: str) -> str:
    """Generate a response using Gemini."""

    if not gemini_client:
        raise ValueError("GEMINI_API_KEY not configured")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return response.text


def generate_ai_response(prompt: str) -> str:
    """
    Primary: OpenRouter DeepSeek
    Fallback: Google Gemini
    """

    # Try OpenRouter first
    try:
        print(f"[AI] Trying OpenRouter: {OPENROUTER_MODEL}")

        result = generate_openrouter_response(prompt)

        print("[AI SUCCESS] OpenRouter response received")

        return result

    except Exception as openrouter_error:
        print(f"[AI FALLBACK] OpenRouter failed: {openrouter_error}")

    # Try Gemini as fallback
    try:
        print(f"[AI] Trying Gemini: {GEMINI_MODEL}")

        result = generate_gemini_response(prompt)

        print("[AI SUCCESS] Gemini fallback response received")

        return result

    except Exception as gemini_error:
        print(f"[AI ERROR] Gemini failed: {gemini_error}")

        raise RuntimeError(
            "Both OpenRouter and Gemini AI providers failed. "
            f"OpenRouter: {openrouter_error if 'openrouter_error' in locals() else 'Unknown'}. "
            f"Gemini: {gemini_error}"
        )
