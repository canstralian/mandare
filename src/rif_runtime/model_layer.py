"""Local model client used only for advisory classification and explanation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, TypeVar
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LocalModelError(RuntimeError):
    """Raised when a local model endpoint cannot produce a valid response."""


@dataclass(frozen=True)
class LocalModel:
    name: str
    endpoint: str
    role: str
    timeout_ms: int = 8_000

    def infer_text(self, prompt: str) -> str:
        payload = json.dumps({"model": self.name, "prompt": prompt, "stream": False}).encode()
        request = Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_ms / 1000) as response:
                body: dict[str, Any] = json.loads(response.read().decode())
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LocalModelError(f"{self.name} inference failed: {exc}") from exc

        if not isinstance(body, dict):
            raise LocalModelError(f'{self.name} returned non-object JSON response')
        if 'error' in body:
            raise LocalModelError(f'{self.name} returned error: {body["error"]}')
        text = body.get('response') or body.get('content')
        if not isinstance(text, str) or not text.strip():
            raise LocalModelError(f"{self.name} returned no text response")
        return text.strip()

    def infer_structured(self, prompt: str, schema: type[T]) -> T:
        raw = self.infer_text(
            f"{prompt}\n\nReturn only valid JSON matching this schema:\n{schema.model_json_schema()}"
        )
        try:
            return schema.model_validate_json(raw)
        except Exception as exc:  # model output is untrusted input
            raise LocalModelError(f"{self.name} returned invalid {schema.__name__}: {raw[:240]}") from exc


def default_mythos_nano() -> LocalModel:
    return LocalModel(
        name=os.getenv("RIF_MYTHOS_MODEL", "mythos-nano-i1-gguf"),
        endpoint=os.getenv("RIF_MYTHOS_ENDPOINT", "http://localhost:11434/api/generate"),
        role="edge_reflex",
    )


def default_deephat() -> LocalModel:
    return LocalModel(
        name=os.getenv("RIF_DEEPHAT_MODEL", "deephat-v1-7b"),
        endpoint=os.getenv("RIF_DEEPHAT_ENDPOINT", "http://localhost:11435/api/generate"),
        role="security_reasoner",
    )
