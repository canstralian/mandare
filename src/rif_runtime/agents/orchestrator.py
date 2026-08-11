from rif_runtime.governance.drift import DriftVector, recommend_correction
from rif_runtime.schemas import PolicyRequest, Posture


class OrchestratorAgent:
    """Example agent that builds PolicyRequests and consumes drift guidance.

    Illustrative rather than a framework: it shows the shape an agent takes
    when it defers every governance judgement to the runtime instead of
    carrying its own thresholds.
    """

    name = "agent:orchestrator"

    def request_http(self, target: str, reason: str | None = None) -> PolicyRequest:
        """Build an ``http.request`` PolicyRequest attributed to this agent."""
        return PolicyRequest(
            actor=self.name,
            action="http.request",
            target=target,
            reason=reason,
        )

    def _choose_correction(self, drift_vector: DriftVector) -> Posture:
        """Delegate to ``recommend_correction`` — deliberately no logic here.

        Keeping this a pure delegation is the point: a second copy of the
        thresholds living in an agent is how the agent and the runtime end up
        disagreeing about when to escalate.
        """
        return recommend_correction(drift_vector)

    def choose_correction(self, drift_vector: DriftVector) -> Posture:
        """Public entry point for the posture a caller should apply.

        The recommendation is advisory: this returns a Posture but never
        mutates runtime state.
        """
        return self._choose_correction(drift_vector)
