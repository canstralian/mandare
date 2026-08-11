from typing import Any

from ..schemas import PolicyDecision


class DeputyAgent:
    name = "agent:deputy"

    def review(self, decision: PolicyDecision) -> dict[str, Any]:
        if decision.decision == "deny":
            return {
                "agent": self.name,
                "finding": "policy denial observed",
                "rule": decision.matched_rule,
                "recommendation": (
                    "inspect target, actor intent, and environment posture"
                ),
            }
        return {
            "agent": self.name,
            "finding": "request allowed",
            "rule": decision.matched_rule,
            "recommendation": "continue monitoring",
        }
