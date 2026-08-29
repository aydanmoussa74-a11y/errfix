"""Thin client that turns a cleaned stack trace into a problem/fix pair."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = (
    "You are errfix, a zero-config stack-trace summarizer. "
    "Given a traceback, reply with JSON only: "
    '{"problem": "Brief summary", "fix": "Suggested code correction"}.'
)


def explain_error(cleaned_trace: str) -> dict:
    """Send ``cleaned_trace`` to an inference endpoint and return a structured dict.

    Environment:
      ERRFIX_API_URL   – inference endpoint (defaults to OpenAI chat completions)
      ERRFIX_API_KEY   – bearer token (falls back to OPENAI_API_KEY)
      ERRFIX_MODEL     – model name

    On network or parse failure a local heuristic summary is returned so the
    CLI still produces a two-line answer.
    """
    if not cleaned_trace or not cleaned_trace.strip():
        return {
            "problem": "No stack trace was provided.",
            "fix": "Pipe a traceback into errfix, e.g. `python app.py 2>&1 | errfix`.",
        }

    endpoint = os.environ.get("ERRFIX_API_URL", DEFAULT_ENDPOINT)
    api_key = os.environ.get("ERRFIX_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("ERRFIX_MODEL", DEFAULT_MODEL)

    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": cleaned_trace},
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return _extract_pair(data)
    except Exception:
        return _heuristic_explain(cleaned_trace)


def _extract_pair(data: dict[str, Any]) -> dict:
    content = ""
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
    elif "problem" in data or "fix" in data:
        return {
            "problem": str(data.get("problem") or "See traceback."),
            "fix": str(data.get("fix") or ""),
        }
    else:
        content = data.get("content") or data.get("output") or json.dumps(data)

    parsed = _parse_json_content(content)
    if parsed:
        return parsed
    return {
        "problem": content.strip().splitlines()[0] if content.strip() else "Unparsed model response.",
        "fix": content.strip(),
    }


def _parse_json_content(content: str) -> dict | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    return {
        "problem": str(obj.get("problem") or "See traceback."),
        "fix": str(obj.get("fix") or ""),
    }


def _heuristic_explain(cleaned_trace: str) -> dict:
    """Offline fallback used when the inference endpoint is unavailable."""
    lines = [line.rstrip() for line in cleaned_trace.strip().splitlines() if line.strip()]
    exc_line = next((line for line in reversed(lines) if _looks_like_exception(line)), None)
    frame_line = next((line for line in reversed(lines) if line.lstrip().startswith("File ")), None)

    problem = exc_line or (lines[-1] if lines else "Unrecognized error output.")
    if frame_line:
        problem = f"{problem} ({frame_line})"

    fix = (
        "Inspect the last frame in the traceback, confirm the referenced name "
        "exists in that scope, and apply the smallest change that satisfies "
        "the exception type."
    )
    if exc_line and "ModuleNotFoundError" in exc_line:
        name = exc_line.split("named")[-1].strip().strip("'\"")
        fix = f"Install the missing package or fix the import: `pip install {name}`."
    elif exc_line and "FileNotFoundError" in exc_line:
        fix = "Create the missing file/directory or correct the path passed to open()."
    elif exc_line and "TypeError" in exc_line:
        fix = "Check argument count and types on the call site shown in the last frame."
    elif exc_line and "NameError" in exc_line:
        fix = "Define the name before use, or import it from the module that provides it."
    elif exc_line and "KeyError" in exc_line:
        fix = "Guard the lookup with `dict.get` or ensure the key is written first."
    elif exc_line and "IndexError" in exc_line:
        fix = "Check sequence length before indexing, or use a slice / next(iter(...), default)."
    elif exc_line and "AttributeError" in exc_line:
        fix = "Verify the object type at the call site and use the correct attribute or method."
    elif exc_line and "ZeroDivisionError" in exc_line:
        fix = "Guard the divisor so it cannot be zero before performing the division."

    return {"problem": problem, "fix": fix}


def _looks_like_exception(line: str) -> bool:
    if "Error" in line or "Exception" in line or "Warning" in line:
        return True
    return ":" in line and line[:1].isupper()
