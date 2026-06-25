from __future__ import annotations

import json
import os
import re
from typing import Any

from .prompts import JSON_SCHEMA, SYSTEM_PROMPT

REDACTION_POLICY_VERSION = "rif-intelligence-redaction-v1"
_MAX_TEXT_CHARS = 4096
_MAX_COLLECTION_ITEMS = 32

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|token|secret|password|credential|authorization|cookie|"
    r"private[_-]?key|session)",
    re.IGNORECASE,
)
_SECRET_PATTERNS = (
    re.compile(r"(?:s" + "k|rk)-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
)


def _redact_text(value: str) -> str:
    if len(value) > _MAX_TEXT_CHARS:
        value = f"{value[:_MAX_TEXT_CHARS]}[TRUNCATED]"
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def redact_secrets(value: Any, *, key: str | None = None) -> Any:
    """Return a bounded, recursively redacted payload suitable for provider egress."""
    if key and _SENSITIVE_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        items = [redact_secrets(item) for item in value[:_MAX_COLLECTION_ITEMS]]
        if len(value) > _MAX_COLLECTION_ITEMS:
            items.append("[TRUNCATED]")
        return items
    if isinstance(value, dict):
        items = list(value.items())
        redacted = {
            item_key: redact_secrets(item_value, key=str(item_key))
            for item_key, item_value in items[:_MAX_COLLECTION_ITEMS]
        }
        if len(items) > _MAX_COLLECTION_ITEMS:
            redacted["__truncated__"] = True
        return redacted
    return value


def generate_structured(
    payload: dict[str, Any],
    *,
    egress_permitted: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    """Invoke the provider only after a policy-backed egress guard permits it."""
    if not egress_permitted:
        return None, None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=10.0, max_retries=0)
        response = client.chat.completions.create(
            model=os.getenv("RIF_OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(redact_secrets(payload), sort_keys=True),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": JSON_SCHEMA["name"],
                    "strict": True,
                    "schema": JSON_SCHEMA["schema"],
                },
            },
        )
        content = response.choices[0].message.content
        return json.loads(content) if content else None, response.model
    except Exception:
        return None, None
