"""Enterprise base class for governed agents.

All agents in this package inherit from ``BaseAgent``. It provides:
- Identity validation (agent:<role> naming convention)
- Integrated policy gate enforcement
- Circuit breaker awareness
- Structured audit-trail integration
- Observable telemetry export

Copy this module, subclass ``BaseAgent``, and override ``execute()``
with the logic your agent needs. The policy gate and circuit breaker
are invoked automatically by the dispatch pipeline.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from rif_runtime.audit import AuditRecord, append_record
from rif_runtime.schemas import PolicyDecision, PolicyRequest

from ._circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpen
from ._policy_gate import GateResult, PolicyGate

logger = logging.getLogger(__name__)

_AGENT_PREFIX: Final[str] = "agent:"


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Structured outcome of an agent action dispatch."""

    success: bool
    agent: str
    action: str
    target: str
    gate_result: GateResult | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class BaseAgent:
    """Enterprise governed agent base class."""

    __slots__ = (
        "_audit_chain",
        "_circuit_breaker",
        "_policy_gate",
        "description",
        "name",
    )

    def __init__(
        self,
        name: str,
        description: str = "",
        *,
        policy_gate: PolicyGate | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        audit_chain: list[AuditRecord] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self._policy_gate = policy_gate
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            name=f"cb:{name}",
            config=CircuitBreakerConfig(),
        )
        self._audit_chain: list[AuditRecord] = audit_chain if audit_chain is not None else []

    def validate(self) -> bool:
        """Check the agent is well-formed."""
        prefix, _, role = self.name.partition(":")
        return prefix == "agent" and bool(role)

    def request(
        self,
        action: str,
        target: str,
        reason: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyRequest:
        """Build a PolicyRequest for the runtime to evaluate."""
        return PolicyRequest(
            actor=self.name,
            action=action,
            target=target,
            reason=reason,
            context=context or {},
        )

    def dispatch(
        self,
        action: str,
        target: str,
        reason: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ActionResult:
        """Full dispatch pipeline: gate -> circuit breaker -> execute -> audit."""
        req = self.request(action, target, reason, context)

        if not self._circuit_breaker.allow_request():
            retry_after = self._circuit_breaker.time_until_recovery()
            return ActionResult(
                success=False,
                agent=self.name,
                action=action,
                target=target,
                error=f"Circuit open; retry after {retry_after:.1f}s",
            )

        gate_result: GateResult | None = None
        if self._policy_gate is not None:
            gate_result = self._policy_gate.check(req)
            if not gate_result.allowed:
                self._circuit_breaker.record_failure()
                return ActionResult(
                    success=False,
                    agent=self.name,
                    action=action,
                    target=target,
                    gate_result=gate_result,
                    error=f"Policy denied: {gate_result.decision.reason}",
                )

        try:
            payload = self.execute(req)
            self._circuit_breaker.record_success()
        except CircuitOpen:
            raise
        except Exception as exc:
            self._circuit_breaker.record_failure()
            self._audit_action(action, target, success=False, error=str(exc))
            return ActionResult(
                success=False,
                agent=self.name,
                action=action,
                target=target,
                gate_result=gate_result,
                error=str(exc),
            )

        self._audit_action(action, target, success=True)
        return ActionResult(
            success=True,
            agent=self.name,
            action=action,
            target=target,
            gate_result=gate_result,
            payload=payload,
        )

    def execute(self, request: PolicyRequest) -> dict[str, Any]:
        """Execute the governed action. Override in subclasses."""
        return {"agent": self.name, "status": "no-op"}

    def handle_decision(self, decision: PolicyDecision) -> dict[str, str]:
        """React to the runtime's verdict."""
        return {
            "agent": self.name,
            "decision": decision.decision,
            "rule": decision.matched_rule,
        }

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    @property
    def audit_chain(self) -> Sequence[AuditRecord]:
        return self._audit_chain

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "valid": self.validate(),
            "circuit_state": self._circuit_breaker.state.value,
        }

    def _audit_action(
        self,
        action: str,
        target: str,
        *,
        success: bool,
        error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "type": "agent.action",
            "agent": self.name,
            "action": action,
            "target": target,
            "success": success,
        }
        if error:
            payload["error"] = error
        append_record(self._audit_chain, payload)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, description={self.description!r})"
        )
