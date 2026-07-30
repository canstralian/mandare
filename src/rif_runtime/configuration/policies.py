from __future__ import annotations

import threading
from pathlib import Path

from pydantic import BaseModel, Field

from ..paths import POLICIES_FILE, data_path
from ..schemas import Decision
from .store import JsonStore


class PolicyRule(BaseModel):
    id: str
    effect: Decision
    action: str = "*"
    target: str = "*"
    reason: str = "configured policy rule"
    metadata: dict[str, str] = Field(default_factory=dict)


DEFAULT_POLICIES = {
    "rules": [
        {
            "id": "allow_known_model_hosts",
            "effect": "allow",
            "action": "http.request",
            "target": "api.anthropic.com",
            "reason": "known model API host",
        },
        {
            "id": "deny_unknown_by_default",
            "effect": "deny",
            "action": "*",
            "target": "*",
            "reason": "deny by default",
        },
    ]
}


class PolicyStore:
    def __init__(self, path: str | Path | None = None) -> None:
        # Resolved per instance so RIF_DATA_DIR applies; see rif_runtime.paths.
        self.store = JsonStore(path or data_path(POLICIES_FILE), DEFAULT_POLICIES)
        # upsert/delete are read-modify-write over the whole file. The API
        # shares one PolicyStore across FastAPI's sync threadpool, so two
        # concurrent writes would otherwise race and lose a rule.
        self._lock = threading.Lock()

    def list(self) -> list[PolicyRule]:
        return [PolicyRule.model_validate(row) for row in self.store.read()["rules"]]

    def upsert(self, rule: PolicyRule) -> PolicyRule:
        with self._lock:
            kept = [r.model_dump() for r in self.list() if r.id != rule.id]
            kept.append(rule.model_dump())
            self.store.write({"rules": kept})
        return rule

    def delete(self, rule_id: str) -> bool:
        with self._lock:
            rules = self.list()
            kept = [r.model_dump() for r in rules if r.id != rule_id]
            self.store.write({"rules": kept})
            return len(kept) != len(rules)
