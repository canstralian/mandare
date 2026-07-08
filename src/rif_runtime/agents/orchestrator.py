from rif_runtime.schemas import PolicyRequest


class OrchestratorAgent:
    name = "agent:orchestrator"

    def request_http(self, target: str, reason: str | None = None):
        return PolicyRequest(
            actor=self.name,
            action="http.request",
            target=target,
            reason=reason,
        )
