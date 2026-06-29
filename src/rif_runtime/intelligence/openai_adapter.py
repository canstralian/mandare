from __future__ import annotations

import json
import os
import re
from typing import Any

from .prompts import JSON_SCHEMA, SYSTEM_PROMPT

_SECRET_PATTERNS = (
    re.compile(r"(?:s" + "k)-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, str):
        for pattern in _SECRET_PATTERNS:
            value = pattern.sub("[REDACTED]", value)
        return value
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    return value


def generate_structured(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=10.0, max_retries=0)
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model=os.getenv("RIF_OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(redact_secrets(payload), sort_keys=True)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": JSON_SCHEMA["name"],
                    "strict": True,
                    "schema": JSON_SCHEMA["schema"]
                }
            },
        )
        content = response.choices[0].message.content
        return json.loads(content) if content else None, response.model
    except Exception:
        return None, None
