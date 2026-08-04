from rif_runtime.schemas import PolicyRequest


class OrchestratorAgent:
    name = "agent:orchestrator"

    def request_http(self, target: str, reason: str | None = None) -> PolicyRequest:
        """Create a policy request for an HTTP request.
        
        Parameters:
        	target (str): The HTTP request target.
        	reason (str | None): Optional reason for the request.
        
        Returns:
        	PolicyRequest: The HTTP request policy request.
        """
        return PolicyRequest(
            actor=self.name,
            action="http.request",
            target=target,
            reason=reason,
        )
