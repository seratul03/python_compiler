import os
import requests
from dotenv import load_dotenv

load_dotenv()

_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.3-70b-versatile"


def call_groq(prompt: str) -> str:
    """Send a prompt to Groq and return the assistant response text."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in .env")

    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        _GROQ_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=30,
    )
    if response.status_code >= 400:
        error_detail = ""
        try:
            error_payload = response.json()
            error_info = error_payload.get("error", {}) if isinstance(error_payload, dict) else {}
            error_detail = error_info.get("message") or response.text
        except ValueError:
            error_detail = response.text
        raise RuntimeError(f"Groq API error {response.status_code}: {error_detail}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Unexpected Groq API response") from exc
