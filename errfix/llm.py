import json
import os

import httpx


def explain_error(cleaned_trace: str) -> dict:
    api_key = os.getenv("ERRFIX_API_KEY")
    if not api_key:
        return {
            "problem": "ERRFIX_API_KEY environment variable missing.",
            "fix": "Run 'export ERRFIX_API_KEY=\"your_key_here\"' in your terminal.",
        }

    system_prompt = (
        "You are an expert CLI developer tool. Analyze the provided stack trace. "
        "Return ONLY a valid raw JSON object with exactly two keys:\n"
        "1. 'problem': A 1-2 sentence explanation of the root cause.\n"
        "2. 'fix': The exact code modification or terminal command required to resolve it."
    )

    # OpenAI-compatible (OpenRouter / Groq / OpenAI) chat completions
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
        parsed = json.loads(content)
        return {
            "problem": parsed.get("problem", "Could not parse problem."),
            "fix": parsed.get("fix", "No fix suggestion returned."),
        }
    except Exception as e:
        return {
            "problem": f"API request failed: {str(e)}",
            "fix": "Check internet connectivity and API key validity.",
        }
