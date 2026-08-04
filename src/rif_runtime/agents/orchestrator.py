"""Enterprise orchestrator agent with circuit breaker and policy gate."""

from __future__ import annotations

import logging
from typing import Any

from rif_runtime.audit import AuditRecord
from rif_runtime.schemas import PolicyRequest

from ._circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitOpen,
    CircuitState,
)
from ._policy_gate import GateResult, PolicyGate
from .template import ActionResult, BaseAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Orchestrates governed actions with per-target circuit breakers."""

    def __init__(
        self,
        *,
        policy_gate: PolicyGate | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
        audit_chain: list[AuditRecord] | None = None,
    ) -> None:
        super().__init__(
            name="agent:orchestrator",
            description="Coordinates governed actions with circuit breaker protection",
            policy_gate=policy_gate,
            audit_chain=audit_chain,
        )
        self._cb_config = circuit_breaker_config or CircuitBreakerConfig()
        self._target_breakers: dict[str, CircuitBreaker] = {}

    def request_http(self, target: str, reason: str | None = None, context: dict[str, Any] | None = None) -> PolicyRequest:
        return self.request("http.request", target, reason, context)

    def request_api(self, target: str, reason: str | None = None, context: dict[str, Any] | None = None) -> PolicyRequest:
        return self.request("api.call", target, reason, context)

    def request_mcp(self, target: str, reason: str | None = None, context: dict[str, Any] | None = None) -> PolicyRequest:
        return self.request("mcp.invoke", target, reason, context)

    def dispatch_http(self, target: str, reason: str | None = None, context: dict[str, Any] | None = None) -> ActionResult:
        return self._dispatch_with_target_cb("http.request", target, reason, context)

    def dispatch_api(self, target: str, reason: str | None = None, context: dict[str, Any] | None = None) -> ActionResult:
        return self._dispatch_with_target_cb("api.call", target, reason, context)

    def dispatch_mcp(self, target: str, reason: str | None = None, context: dict[str, Any] | None = None) -> ActionResult:
        return self._dispatch_with_target_cb("mcp.invoke", target, reason, context)

    def get_target_breaker(self, target: str) -> CircuitBreaker:
        if target not in self._target_breakers:
            self._target_breakers[target] = CircuitBreaker(
                name=f"cb:orchestrator:{target}",
                config=self._cb_config,
            )
        return self._target_breakers[target]

    def target_breaker_stats(self) -> dict[str, CircuitBreakerStats]:
        return {target: cb.stats for target, cb in self._target_breakers.items()}

    def reset_target_breaker(self, target: str) -> bool:
        cb = self._target_breakers.get(target)
        if cb is not None:
            cb.reset()
            return True
        return False

    def execute(self, request: PolicyRequest) -> dict[str, Any]:
        return {"agent": self.name, "action": request.action, "target": request.target, "status": "dispatched"}

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base["target_breakers"] = {target: cb.state.value for target, cb in self._target_breakers.items()}
        return base

    def _dispatch_with_target_cb(self, action: str, target: str, reason: str | None, context: dict[str, Any] | None) -> ActionResult:
        target_cb = self.get_target_breaker(target)
        if not target_cb.allow_request():
            retry_after = target_cb.time_until_recovery()
            return ActionResult(
                success=False, agent=self.name, action=action, target=target,
                error=f"Target circuit open for '{target}'; retry after {retry_after:.1f}s",
            )
        result = self.dispatch(action, target, reason, context)
        if result.success:
            target_cb.record_success()
        else:
            target_cb.record_failure()
        return result
