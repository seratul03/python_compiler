import re
from typing import Dict

from ai.groq_client import call_groq

_PRECHECK_PROMPT = """You are a strict compiler assistant.

Rules:

* Only fix actual errors
* Keep changes minimal
* Do not rewrite full code unnecessarily
* Output STRICT format only

Return exactly:

STATUS: OK or ERROR
MESSAGE: short explanation
FIXED_CODE: <corrected code>

Code:
{code}"""

_RUNTIME_PROMPT = """The following code produced an error.

Fix it.

Code:
{code}

Error:
{error}

Return exactly:

STATUS: OK or ERROR
MESSAGE: short explanation
FIXED_CODE: <corrected code>"""


def _strip_code_fence(text: str) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def _parse_ai_response(text: str) -> Dict[str, str]:
    if not text:
        return {
            "status": "ERROR",
            "message": "Empty AI response.",
            "fixed_code": "",
        }

    status_match = re.search(r"STATUS:\s*(OK|ERROR)", text)
    message_match = re.search(r"MESSAGE:\s*(.*)", text)
    fixed_match = re.search(r"FIXED_CODE:\s*(.*)", text, re.DOTALL)

    status = status_match.group(1) if status_match else "ERROR"
    message = message_match.group(1).strip() if message_match else ""
    fixed_code = fixed_match.group(1).strip() if fixed_match else ""

    fixed_code = _strip_code_fence(fixed_code)

    return {
        "status": status,
        "message": message,
        "fixed_code": fixed_code,
    }


def check_code(code: str) -> Dict[str, str]:
    """Analyze code before execution and return status, message, and fix."""
    try:
        raw = call_groq(_PRECHECK_PROMPT.format(code=code))
    except Exception as exc:
        return {
            "status": "ERROR",
            "message": f"AI request failed: {exc}",
            "fixed_code": code,
        }

    result = _parse_ai_response(raw)
    if result["status"] == "OK":
        result["message"] = result["message"] or "Your code is good to run"
        result["fixed_code"] = code
    elif not result["fixed_code"]:
        result["fixed_code"] = code

    return result


def analyze_output(code: str, output: str, error: str) -> Dict[str, str]:
    """Analyze runtime errors and return status, message, and fix."""
    error_text = error or output
    try:
        raw = call_groq(_RUNTIME_PROMPT.format(code=code, error=error_text))
    except Exception as exc:
        return {
            "status": "ERROR",
            "message": f"AI request failed: {exc}",
            "fixed_code": code,
        }

    result = _parse_ai_response(raw)
    if result["status"] == "OK":
        result["message"] = result["message"] or "Your code is good to run"
        result["fixed_code"] = code
    elif not result["fixed_code"]:
        result["fixed_code"] = code

    return result
