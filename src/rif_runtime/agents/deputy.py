class DeputyAgent:
    name = "agent:deputy"

    def review(self, decision):
        if decision.decision == "deny":
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
