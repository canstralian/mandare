"""Execution layer: where a model-backed engine plugs into the kernel.

The kernel depends on the `ExecutionEngine` protocol, never on a vendor SDK.
That is what makes the runtime model-agnostic in practice rather than in
principle: Azure Foundry, OpenAI, Anthropic, Ollama, and local inference are
all adapters behind this one interface, and none of them is a dependency of
`rif_runtime` itself.

`CapabilityApprovalGate` is the seam an engine's tool-approval middleware binds
to. An engine that auto-approves its own tool calls would place the model's
chosen actions outside governance entirely — pre-flight admission judges the
*intent*, but the tool calls are chosen afterwards, from text that may itself
be adversarial. The gate mediates each call against the policy engine and
records it, so denials still drive posture and still land in the ledger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from .budget import BudgetAccount, BudgetExceeded
from .capabilities import Capability
from .context import ExecutionContext

if TYPE_CHECKING:  # pragma: no cover - types only
    from .evidence import EvidenceLedger
    from .governance.engine import GovernanceEngine


class CapabilityCall(BaseModel):
    capability: str
    target: str = "mcp://local"
    arguments: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    output: str = ""
    tokens: int = 0
    latency_ms: float = 0.0
    capability_calls: list[CapabilityCall] = Field(default_factory=list)
    success: bool = True
    error: str | None = None
    model: str | None = None


@runtime_checkable
class ExecutionEngine(Protocol):
    """What the kernel requires of any model-backed execution engine."""

    @property
    def model(self) -> str: ...

    async def run(
        self,
        context: ExecutionContext,
        capabilities: list[Capability],
        gate: "CapabilityApprovalGate",
    ) -> ExecutionResult: ...


class CapabilityDenied(RuntimeError):
    def __init__(self, capability: str, reason: str) -> None:
        super().__init__(f"capability denied: {capability}: {reason}")
        self.capability = capability
        self.reason = reason


class CapabilityApprovalGate:
    """Per-call mediation. Bind an engine's tool-approval hook to `approve`.

    Every invocation is evaluated against the policy engine and appended to the
    ledger, whether allowed or denied. `denials` is what the kernel feeds into
    posture and the evolution queue after a run.
    """

    def __init__(
        self,
        context: ExecutionContext,
        governance: "GovernanceEngine",
        ledger: "EvidenceLedger | None" = None,
        budget: BudgetAccount | None = None,
    ) -> None:
        self.context = context
        self.governance = governance
        self.ledger = ledger
        self.budget = budget
        self.approved: list[CapabilityCall] = []
        self.denials: list[dict[str, Any]] = []

    def approve(self, call: CapabilityCall) -> bool:
        """True if this specific invocation may proceed, now."""

        decision = self.governance.evaluate_capability(
            self.context, call.capability, call.target
        )
        if decision.allowed and self.budget is not None:
            try:
                self.budget.consume(capability_calls=1)
            except BudgetExceeded as exceeded:
                self._deny(
                    call, f"budget exhausted: {exceeded.axis}", "budget.exceeded"
                )
                return False

        if not decision.allowed:
            self._deny(call, decision.reason, decision.matched_rule)
            return False

        self.approved.append(call)
        if self.ledger is not None:
            self.ledger.record(
                "capability.approved",
                context=self.context.summary(),
                capability=call.capability,
                target=call.target,
                matched_rule=decision.matched_rule,
                policy_version=decision.policy_version,
            )
        return True

    def require(self, call: CapabilityCall) -> None:
        """Raising variant, for engines that cannot act on a boolean."""

        if not self.approve(call):
            reason = self.denials[-1]["reason"] if self.denials else "denied"
            raise CapabilityDenied(call.capability, reason)

    def _deny(self, call: CapabilityCall, reason: str, matched_rule: str) -> None:
        record = {
            "capability": call.capability,
            "target": call.target,
            "reason": reason,
            "matched_rule": matched_rule,
        }
        self.denials.append(record)
        if self.ledger is not None:
            self.ledger.record(
                "capability.denied", context=self.context.summary(), **record
            )


class EchoExecutionEngine:
    """Dependency-free reference engine.

    Exercises the full pipeline — including per-call approval — without a model
    provider, so the kernel is testable in CI and in a fresh clone. Real
    adapters live outside the core package and are installed as extras.
    """

    def __init__(self, model: str = "echo", calls: list[CapabilityCall] | None = None):
        self._model = model
        self.calls = calls or []

    @property
    def model(self) -> str:
        return self._model

    async def run(
        self,
        context: ExecutionContext,
        capabilities: list[Capability],
        gate: CapabilityApprovalGate,
    ) -> ExecutionResult:
        performed: list[CapabilityCall] = []
        for call in self.calls:
            if gate.approve(call):
                performed.append(call)

        offered = ", ".join(c.name for c in capabilities) or "none"
        return ExecutionResult(
            output=f"[{self._model}] offered={offered} performed={len(performed)}",
            tokens=len(context.prompt.split()),
            capability_calls=performed,
            success=True,
            model=self._model,
        )
