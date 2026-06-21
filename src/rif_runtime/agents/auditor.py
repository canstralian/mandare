class AuditorAgent:
    name = "agent:auditor"

    def audit(self, runtime):
        return {
            "agent": self.name,
            **runtime.audit_summary(),
        }
