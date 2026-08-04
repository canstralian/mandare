"""Policy gate middleware for governed agent actions.

A PolicyGate wraps the runtime's PolicyEngine and provides a clean
pre-execution check that agents call before dispatching any governed
action. It integrates with the audit chain and circuit breaker to
provide a unified enforcement point.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from rif_runtime.audit import AuditRecord, append_record
from rif_runtime.schemas import (
    Decision,
    EnvironmentProfile,
    PolicyDecision,
    PolicyRequest,
    Posture,
)

logger = logging.getLogger(__name__)


class PolicyEvaluator(Protocol):
    """Protocol for anything that evaluates policy requests."""

    def evaluate(
        self,
        req: PolicyRequest,
        env_name: str,
        profile: EnvironmentProfile,
        posture: Posture,
        policy_rules: Sequence[Any] = (),
    ) -> PolicyDecision: ...


@dataclass(frozen=True, slots=True)
class GateResult:
    """Outcome of a policy gate check.

    Attributes:
        allowed: Whether the action may proceed.
        decision: The full PolicyDecision from the engine.
        audit_record: The audit record appended for this check.
        timestamp: UTC time of the evaluation.
    """

    allowed: bool
    decision: PolicyDecision
    audit_record: AuditRecord | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PolicyGateError(Exception):
    """Raised when an action is denied by the policy gate."""

    def __init__(self, decision: PolicyDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Policy gate denied: action={decision.action} "
            f"target={decision.target} rule={decision.matched_rule} "
            f"reason={decision.reason}"
        )


class PolicyGate:
    """Pre-execution policy enforcement point.

    Agents call ``check()`` before any governed action. If the policy
    engine denies the request, the gate can either raise or return a
    denial result depending on configuration.

    Args:
        evaluator: Policy engine instance (satisfies PolicyEvaluator protocol).
        env_name: Active environment name.
        profile: Active environment profile.
        posture: Current security posture.
        audit_chain: Shared audit chain to which gate checks are appended.
        policy_rules: Loaded policy rules sequence.
        raise_on_deny: If True, raises PolicyGateError on denial instead
            of returning a GateResult with allowed=False.
    """

    __slots__ = (
        "_audit_chain",
        "_env_name",
        "_evaluator",
        "_policy_rules",
        "_posture",
        "_profile",
        "_raise_on_deny",
    )

    def __init__(
        self,
        evaluator: PolicyEvaluator,
        env_name: str,
        profile: EnvironmentProfile,
        posture: Posture,
        audit_chain: list[AuditRecord],
        policy_rules: Sequence[Any] = (),
        *,
        raise_on_deny: bool = False,
    ) -> None:
        self._evaluator = evaluator
        self._env_name = env_name
        self._profile = profile
        self._posture = posture
        self._audit_chain = audit_chain
        self._policy_rules = policy_rules
        self._raise_on_deny = raise_on_deny

    def check(self, request: PolicyRequest) -> GateResult:
        """Evaluate a policy request and record the decision."""
        decision = self._evaluator.evaluate(
            req=request,
            env_name=self._env_name,
            profile=self._profile,
            posture=self._posture,
            policy_rules=self._policy_rules,
        )

        audit_payload: dict[str, Any] = {
            "type": "policy_gate.check",
            "actor": request.actor,
            "action": request.action,
            "target": request.target,
            "decision": decision.decision.value,
            "matched_rule": decision.matched_rule,
            "reason": decision.reason,
        }
        record = append_record(self._audit_chain, audit_payload)

        allowed = decision.decision != Decision.deny
        result = GateResult(
            allowed=allowed,
            decision=decision,
            audit_record=record,
        )

        if not allowed:
            logger.warning(
                "Policy gate denied: actor=%s action=%s target=%s rule=%s",
                request.actor,
                request.action,
                request.target,
                decision.matched_rule,
            )
            if self._raise_on_deny:
                raise PolicyGateError(decision)

        return result

    @property
    def posture(self) -> Posture:
        """Current security posture."""
        return self._posture

    def update_posture(self, posture: Posture) -> None:
        """Hot-update the security posture without rebuilding the gate."""
        object.__setattr__(self, "_posture", posture)

    def __repr__(self) -> str:
        return (
            f"PolicyGate(env={self._env_name!r}, "
            f"posture={self._posture}, "
            f"raise_on_deny={self._raise_on_deny})"
        )
