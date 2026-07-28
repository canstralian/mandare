from __future__ import annotations

from rif_runtime.schemas import Decision, PolicyDecision


class DeputyAgent:
    name = "agent:deputy"

    def review(self, decision: PolicyDecision) -> dict[str, str]:
        if decision.decision == Decision.deny:
            return {
                "agent": self.name,
                "finding": "policy denial observed",
                "rule": decision.matched_rule,
                "recommendation": "inspect target, actor intent, and environment posture",
            }
        return {
            "agent": self.name,
            "finding": "request allowed",
            "rule": decision.matched_rule,
            "recommendation": "continue monitoring",
        }
