from __future__ import annotations

from pydantic import BaseModel, Field

from .store import JsonStore


class PolicyRule(BaseModel):
    id: str
    effect: str
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
    def __init__(self, path: str = "data/policies.json"):
        self.store = JsonStore(path, DEFAULT_POLICIES)

    def list(self) -> list[PolicyRule]:
        return [PolicyRule.model_validate(row) for row in self.store.read()["rules"]]

    def upsert(self, rule: PolicyRule) -> PolicyRule:
        rules = [r.model_dump() for r in self.list()]
        kept = [r for r in rules if r["id"] != rule.id]
        kept.append(rule.model_dump())
        self.store.write({"rules": kept})
        return rule

    def delete(self, rule_id: str) -> bool:
        rules = [r.model_dump() for r in self.list()]
        kept = [r for r in rules if r["id"] != rule_id]
        self.store.write({"rules": kept})
        return len(kept) != len(rules)
