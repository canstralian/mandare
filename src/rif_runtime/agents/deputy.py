from typing import Any

from ..schemas import PolicyDecision


class DeputyAgent:
    name = "agent:deputy"

    def review(self, decision: PolicyDecision) -> dict[str, Any]:
        """
        Evaluate a policy decision and produce a finding with a corresponding recommendation.
        
        Parameters:
            decision (PolicyDecision): The policy decision to evaluate.
        
        Returns:
            dict[str, Any]: A report containing the agent name, matched rule, finding, and recommendation.
        """
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
