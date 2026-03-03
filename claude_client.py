import os
import json
import requests
from typing import Dict, Any

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/messages")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")


def build_prompt(payload: Dict[str, Any]) -> str:
    """
    Create a safe, wellness-only prompt. No diagnosing. Focus on patterns.
    """
    metrics = json.dumps(payload["metrics"], ensure_ascii=False, indent=2)
    notes = "\n".join(f"- {n}" for n in payload.get("notes", [])) or "- (none)"

    return f"""
You are a wellness analytics assistant. Do NOT provide medical diagnosis.
Only describe trends, possible lifestyle correlations, and practical, non-medical suggestions.

User context:
- period_days: {payload.get("period_days")}
- timezone: {payload.get("timezone")}
- notes:
{notes}

Aggregated wearable metrics (already normalized vs baseline):
{metrics}

Return JSON with keys:
- "summary" (string, 2-4 sentences)
- "flags" (array of objects: {{ "type": "sleep|stress|recovery|activity", "severity": "low|medium|high", "reason": string }})
- "insights" (array of 3-6 bullet strings)
- "suggestions" (array of 3-6 bullet strings)
- "questions" (array of 2-4 clarifying questions)
""".strip()


def analyze_with_claude(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not CLAUDE_API_KEY:
        raise RuntimeError("Missing CLAUDE_API_KEY env var")

    prompt = build_prompt(payload)

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "content-type": "application/json",
        # Some APIs require version headers; keep as placeholder:
        "anthropic-version": "2023-06-01"
    }

    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 800,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    resp = requests.post(CLAUDE_API_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Typical response is text; we expect JSON in text. Extract and parse.
    # Adjust this depending on actual API response format.
    text = ""
    if "content" in data and isinstance(data["content"], list):
        # e.g. [{"type":"text","text":"..."}]
        text = "".join(part.get("text", "") for part in data["content"])
    else:
        text = str(data)

    # Very simple JSON extraction:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Claude response did not contain JSON")

    return json.loads(text[start:end+1])
