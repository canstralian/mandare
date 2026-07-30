"""Capability Router: choose what may be offered, not what will be called.

Selection narrows the set of capabilities an execution engine is even told
about, using policy, cost, latency, confidence, identity, and remaining budget.
It is a *reduction* step, never an authorisation step — a capability surviving
selection still has every individual invocation mediated by
`GovernanceEngine.evaluate_capability`.

Ordering is deterministic (score, then name) so the same intent against the
same catalog always produces the same offer, which is what makes a recorded
run replayable.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from .budget import BudgetAccount
from .context import ExecutionContext
from .identity import TrustTier, tier_rank
from .mcp.capabilities import CapabilityClass, classify, is_severe
from .state import RuntimeMode

if TYPE_CHECKING:  # pragma: no cover - types only
    from .governance.engine import GovernanceEngine


class Capability(BaseModel):
    name: str
    provider: str = "mcp"
    description: str = ""
    # Selection inputs. Cost and latency are per-call estimates; confidence is
    # the router's prior that this capability answers the intent well.
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    confidence: float = 0.5
    min_tier: TrustTier = TrustTier.standard
    target: str = "mcp://local"
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def capability_class(self) -> CapabilityClass:
        return classify(self.name)

    @property
    def severe(self) -> bool:
        return is_severe(self.name)


class RoutingRejection(BaseModel):
    capability: str
    reason: str


class RoutingResult(BaseModel):
    selected: list[Capability] = Field(default_factory=list)
    rejected: list[RoutingRejection] = Field(default_factory=list)

    def names(self) -> list[str]:
        return [capability.name for capability in self.selected]

    def summary(self) -> dict[str, Any]:
        return {
            "selected": self.names(),
            "rejected": [r.model_dump() for r in self.rejected],
        }


class CapabilityRouter:
    def __init__(
        self,
        catalog: Iterable[Capability] = (),
        governance: "GovernanceEngine | None" = None,
        min_confidence: float = 0.25,
    ) -> None:
        self.catalog: list[Capability] = list(catalog)
        self.governance = governance
        self.min_confidence = min_confidence

    def register(self, capability: Capability) -> Capability:
        self.catalog = [c for c in self.catalog if c.name != capability.name]
        self.catalog.append(capability)
        return capability

    def select(
        self,
        context: ExecutionContext,
        budget: BudgetAccount | None = None,
        catalog: Sequence[Capability] | None = None,
        limit: int | None = None,
    ) -> RoutingResult:
        result = RoutingResult()
        for capability in catalog if catalog is not None else self.catalog:
            reason = self._reject_reason(capability, context, budget)
            if reason is None:
                result.selected.append(capability)
            else:
                result.rejected.append(
                    RoutingRejection(capability=capability.name, reason=reason)
                )

        result.selected.sort(key=lambda c: (-self._score(c), c.name))
        if limit is not None:
            for dropped in result.selected[limit:]:
                result.rejected.append(
                    RoutingRejection(capability=dropped.name, reason="over offer limit")
                )
            result.selected = result.selected[:limit]
        return result

    def _reject_reason(
        self,
        capability: Capability,
        context: ExecutionContext,
        budget: BudgetAccount | None,
    ) -> str | None:
        if context.mode is RuntimeMode.lockdown:
            return "runtime locked"
        if (
            context.mode is RuntimeMode.degraded
            and capability.capability_class is not CapabilityClass.read_only
        ):
            return "degraded mode offers read-only capabilities only"
        if tier_rank(context.identity.tier) < tier_rank(capability.min_tier):
            return f"requires {capability.min_tier.value} tier"
        if capability.confidence < self.min_confidence:
            return "below confidence floor"
        if budget is not None:
            axis = budget.would_exceed(
                cost_usd=capability.cost_usd,
                seconds=capability.latency_ms / 1000.0,
                capability_calls=1,
            )
            if axis is not None:
                return f"insufficient budget: {axis}"
        if self.governance is not None:
            decision = self.governance.evaluate_capability(
                context, capability.name, capability.target
            )
            if not decision.allowed:
                return f"policy: {decision.matched_rule}"
        return None

    def _score(self, capability: Capability) -> float:
        # Confidence dominates; cost and latency break ties downward. Severe
        # capabilities are ranked last so a cheaper safe option is offered
        # first when both survive selection.
        penalty = 0.5 if capability.severe else 0.0
        return (
            capability.confidence
            - penalty
            - capability.cost_usd
            - capability.latency_ms / 100_000.0
        )
