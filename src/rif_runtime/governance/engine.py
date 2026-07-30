"""Governance Engine: the pipeline's decision stage.

Wraps the existing `PolicyEngine` rather than reimplementing it, so the kernel
and the HTTP control plane apply exactly the same rules, in the same
precedence, and produce the same `PolicyDecision` shape.

Two entry points, deliberately distinct:

* `evaluate(context)` — pre-flight. Judges the *intent*: may this principal,
  in this environment and posture, invoke the agent at all?
* `evaluate_capability(context, capability, target)` — per-call. Judges one
  concrete action the model chose *during* execution.

Pre-flight admission is not authorisation to act. A model's tool calls are
chosen after the pre-flight check, from text that may itself be adversarial, so
each one is mediated separately. `CapabilityApprovalGate` in `execution.py` is
what binds an execution engine to this method.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..configuration.policies import PolicyRule, PolicyStore
from ..context import ExecutionContext, policy_version
from ..policy import PolicyEngine
from ..schemas import Decision, PolicyDecision, PolicyRequest, Posture

# What the caller sees when governance refuses. Deliberately free of policy
# internals -- an untrusted principal learns that it was denied, not which rule
# to work around.
SAFE_RESPONSE = (
    "This request was not permitted by the active governance policy. "
    "No capability was invoked."
)

# Every capability invocation is evaluated inside the `mcp.` action namespace.
# Without this a capability named "exploit.run" would reach PolicyEngine as an
# action matching no rule and no built-in constraint, and fall through to
# `default.allow` -- silently ungoverned. Prefixing puts it under the profile's
# `allow_mcp_server_network_access` gate, which denies by default.
CAPABILITY_ACTION_PREFIX = "mcp."


def capability_action(capability: str) -> str:
    """Map a capability name into the policy engine's action vocabulary."""

    normalized = capability.strip().lower()
    if normalized.startswith(CAPABILITY_ACTION_PREFIX):
        return normalized
    return f"{CAPABILITY_ACTION_PREFIX}{normalized}"


class GovernanceDecision(BaseModel):
    allowed: bool
    decision: Decision
    reason: str
    matched_rule: str
    policy_version: str
    posture: Posture
    response: str | None = None
    policy_decision: PolicyDecision

    def summary(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision.value,
            "reason": self.reason,
            "matched_rule": self.matched_rule,
            "policy_version": self.policy_version,
            "posture": self.posture.value,
        }


class GovernanceEngine:
    def __init__(
        self,
        policy: PolicyEngine | None = None,
        policy_store: PolicyStore | None = None,
    ) -> None:
        self.policy = policy or PolicyEngine()
        self.policy_store = policy_store or PolicyStore()

    def rules(self) -> list[PolicyRule]:
        return self.policy_store.list()

    def policy_version(self) -> str:
        return policy_version(self.rules())

    def evaluate(self, context: ExecutionContext) -> GovernanceDecision:
        """Pre-flight: may this intent reach an execution engine at all?"""

        return self._decide(
            context,
            PolicyRequest(
                actor=context.intent.actor,
                action=context.intent.action,
                target=context.intent.target,
                reason=f"intent {context.intent.digest()[:12]}",
                context=context.summary(),
            ),
        )

    def evaluate_capability(
        self,
        context: ExecutionContext,
        capability: str,
        target: str,
        reason: str | None = None,
    ) -> GovernanceDecision:
        """Per-call: may the model invoke this specific capability, now?

        Called once per tool invocation during execution, not once per run.
        """

        return self._decide(
            context,
            PolicyRequest(
                actor=context.intent.actor,
                action=capability_action(capability),
                target=target,
                reason=reason or f"capability {capability}",
                context=context.summary(),
            ),
        )

    def _decide(
        self, context: ExecutionContext, request: PolicyRequest
    ) -> GovernanceDecision:
        rules = self.rules()
        decision = self.policy.evaluate(
            request,
            context.environment,
            context.profile,
            context.posture,
            rules,
        )
        allowed = decision.decision == Decision.allow
        return GovernanceDecision(
            allowed=allowed,
            decision=decision.decision,
            reason=decision.reason,
            matched_rule=decision.matched_rule,
            policy_version=policy_version(rules),
            posture=decision.posture,
            response=None if allowed else SAFE_RESPONSE,
            policy_decision=decision,
        )
