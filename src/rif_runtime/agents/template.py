"""Starting point for new governed agents.

Copy this module, rename ``TemplateAgent``, and replace ``request()`` /
``handle_decision()`` with the actions your agent needs. Agents in this
package are deliberately thin: they construct ``PolicyRequest`` objects
and consume ``PolicyDecision`` results — they never bypass the policy
engine or talk to targets directly.
"""

from typing import Any

from rif_runtime.schemas import PolicyDecision, PolicyRequest


class TemplateAgent:
    """Minimal governed agent: build policy requests, react to decisions.

    Attributes:
        name: Actor identity recorded on every decision. Convention is an
            ``agent:<role>`` prefix (see ``OrchestratorAgent`` et al.).
        description: Short human-readable purpose, exported via ``to_dict``.
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description

    def validate(self) -> bool:
        """Check the agent is well-formed before it issues requests.

        Returns:
            True when ``name`` follows the ``agent:<role>`` convention
            with a non-empty role.
        """
        prefix, _, role = self.name.partition(":")
        return prefix == "agent" and bool(role)

    def request(
        self,
        action: str,
        target: str,
        reason: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyRequest:
        """Build a request for the runtime to evaluate.

        Args:
            action: Governed action name, e.g. ``http.request``.
            target: The host, URL, package, or tool being acted on.
            reason: Optional intent string recorded for the audit trail.
            context: Optional extra metadata for policy evaluation.
        """
        return PolicyRequest(
            actor=self.name,
            action=action,
            target=target,
            reason=reason,
            context=context or {},
        )

    def handle_decision(self, decision: PolicyDecision) -> dict[str, str]:
        """React to the runtime's verdict; replace with real behavior."""
        return {
            "agent": self.name,
            "decision": decision.decision,
            "rule": decision.matched_rule,
        }

    def to_dict(self) -> dict[str, str]:
        """Export the agent's identity for audits and telemetry."""
        return {
            "name": self.name,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, description={self.description!r})"
        )
