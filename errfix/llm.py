"""OpenAI-compatible LLM client with defensive response handling."""

from __future__ import annotations

import json
import os
import re

import httpx


_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _parse_json_content(content: object) -> dict[str, str]:
    """Parse a model response and return only the fields the CLI renders."""
    if not isinstance(content, str):
        raise ValueError("model returned non-text content")

    text = _JSON_FENCE.sub("", content.strip()).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model response was not a JSON object")

    problem = parsed.get("problem")
    fix = parsed.get("fix")
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("model response is missing a valid problem")
    if not isinstance(fix, str) or not fix.strip():
        raise ValueError("model response is missing a valid fix")

    return {"problem": problem.strip(), "fix": fix.strip()}


def explain_error(cleaned_trace: str) -> dict[str, str]:
    """Send a sanitized trace to an OpenAI-compatible endpoint."""
    api_key = os.getenv("ERRFIX_API_KEY")
    if not api_key:
        return {
            "problem": "ERRFIX_API_KEY environment variable missing.",
            "fix": "Export ERRFIX_API_KEY in your shell or configure ~/.errfixrc.",
        }

    system_prompt = (
        "You are an expert CLI developer tool. Analyze the provided stack trace. "
        "Return ONLY a valid raw JSON object with exactly two keys:\n"
        "1. 'problem': A 1-2 sentence explanation of the root cause.\n"
        "2. 'fix': The exact code modification or terminal command required to resolve it."
    )

    url = os.getenv("ERRFIX_API_URL", "https://openrouter.ai/api/v1/chat/completions")
    model = os.getenv("ERRFIX_MODEL", "meta-llama/llama-3-8b-instruct:free")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this error:\n{cleaned_trace}"},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_json_content(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "problem": f"API response could not be processed: {exc}",
            "fix": "Check the endpoint, model, API key, and network connection, then try again.",
        }
