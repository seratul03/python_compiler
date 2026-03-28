import re
from typing import Dict

from ai.groq_client import call_groq, call_groq_messages

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

_SUCCESS_PROMPT = """You are a strict post-run code reviewer.

Give a concise review that includes:
- Runtime (given)
- Estimated time complexity in Big-O based on the code
- One short improvement tip if relevant

Return exactly:

STATUS: OK
MESSAGE: <review summary>
FIXED_CODE: <leave empty>

Code:
{code}

Output:
{output}

Runtime:
{runtime_seconds:.6f} seconds"""

_CHAT_SYSTEM_PROMPT = """You are the PyFlux AI assistant.

You are a conversational coding assistant and debugging helper.
Answer questions about code, compiler errors, runtime errors, and improvements.
Explain reasoning when the user asks or when it helps clarity.
If the user wants a fix, provide corrected code and explain the change.
If the question is unclear, ask a brief clarifying question.
Keep responses concise and helpful.
When you include code, use fenced Markdown blocks like ```python ... ```.
"""


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
        result["message"] = result["message"] or "Pre-run check: no issues found."
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


def review_success(code: str, output: str, runtime_seconds: float) -> Dict[str, str]:
    """Generate a post-run review when execution succeeds."""
    trimmed_output = output or ""
    if len(trimmed_output) > 1200:
        trimmed_output = trimmed_output[:1200] + "..."

    try:
        raw = call_groq(
            _SUCCESS_PROMPT.format(
                code=code,
                output=trimmed_output,
                runtime_seconds=runtime_seconds,
            )
        )
    except Exception as exc:
        return {
            "status": "OK",
            "message": f"Runtime: {runtime_seconds:.3f}s. Complexity: Unknown. AI request failed: {exc}",
            "fixed_code": "",
        }

    result = _parse_ai_response(raw)
    if result["status"] != "OK":
        result["status"] = "OK"
    if not result["message"]:
        result["message"] = f"Runtime: {runtime_seconds:.3f}s. Complexity: Unknown."
    result["fixed_code"] = ""
    return result


def _build_chat_messages(message: str, code: str, error: str, history) -> list[dict]:
    messages = [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]

    context_parts = []
    if code:
        context_parts.append(f"Code:\n{code}")
    if error:
        context_parts.append(f"Error/Output:\n{error}")
    if context_parts:
        messages.append(
            {
                "role": "system",
                "content": "Context:\n" + "\n\n".join(context_parts),
            }
        )

    if isinstance(history, list):
        for item in history[-12:]:
            role = item.get("role") if isinstance(item, dict) else None
            content = item.get("content") if isinstance(item, dict) else None
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": str(content)})

    messages.append({"role": "user", "content": message})
    return messages


def chat_with_ai(
    message: str,
    code: str = "",
    error: str = "",
    history=None,
) -> Dict[str, str]:
    """Chat with the AI about code, errors, or improvements."""
    try:
        messages = _build_chat_messages(message, code, error, history)
        raw = call_groq_messages(messages)
        reply = raw.strip()
        if not reply:
            raise RuntimeError("Empty AI response.")
        return {"reply": reply}
    except Exception as exc:
        return {"error": f"AI request failed: {exc}"}
