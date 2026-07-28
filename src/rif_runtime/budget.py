"""Budget Manager: bounded execution.

A budget is an authority boundary expressed in resources rather than
permissions. An execution that runs out of budget is *denied*, not truncated —
the kernel records the denial like any other governance outcome so it drives
posture and lands in the ledger.

Budgets are per-intent: `open()` returns an account whose consumption is
tracked independently, so one runaway execution cannot spend another's
allowance.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping

from pydantic import BaseModel, Field

from .identity import IdentityState, TrustTier
from .intent import Intent


class Budget(BaseModel):
    """Ceilings for one execution. ``None`` means unbounded on that axis."""

    max_tokens: int | None = 100_000
    max_cost_usd: float | None = 1.0
    max_seconds: float | None = 120.0
    max_capability_calls: int | None = 25


# Standing widens the allowance; it never removes the ceiling entirely, so an
# operator-tier runaway is still bounded.
DEFAULT_TIER_BUDGETS: Mapping[TrustTier, Budget] = {
    TrustTier.untrusted: Budget(
        max_tokens=2_000, max_cost_usd=0.05, max_seconds=15.0, max_capability_calls=2
    ),
    TrustTier.standard: Budget(),
    TrustTier.elevated: Budget(
        max_tokens=250_000,
        max_cost_usd=5.0,
        max_seconds=300.0,
        max_capability_calls=100,
    ),
    TrustTier.operator: Budget(
        max_tokens=1_000_000,
        max_cost_usd=25.0,
        max_seconds=900.0,
        max_capability_calls=500,
    ),
}


class BudgetExceeded(RuntimeError):
    """Raised when a consume() would cross a ceiling."""

    def __init__(self, axis: str, limit: float, attempted: float) -> None:
        super().__init__(
            f"budget exceeded on {axis}: limit {limit}, attempted {attempted}"
        )
        self.axis = axis
        self.limit = limit
        self.attempted = attempted


class BudgetAccount:
    """Consumption tracker for a single intent."""

    def __init__(self, intent_id: str, budget: Budget) -> None:
        self.intent_id = intent_id
        self.budget = budget
        self.tokens = 0
        self.cost_usd = 0.0
        self.seconds = 0.0
        self.capability_calls = 0
        self._lock = threading.Lock()

    def would_exceed(
        self,
        *,
        tokens: int = 0,
        cost_usd: float = 0.0,
        seconds: float = 0.0,
        capability_calls: int = 0,
    ) -> str | None:
        """Name of the first axis this spend would cross, or None if it fits."""

        checks: tuple[tuple[str, float, int | float | None], ...] = (
            ("tokens", self.tokens + tokens, self.budget.max_tokens),
            ("cost_usd", self.cost_usd + cost_usd, self.budget.max_cost_usd),
            ("seconds", self.seconds + seconds, self.budget.max_seconds),
            (
                "capability_calls",
                self.capability_calls + capability_calls,
                self.budget.max_capability_calls,
            ),
        )
        for axis, projected, limit in checks:
            if limit is not None and projected > limit:
                return axis
        return None

    def consume(
        self,
        *,
        tokens: int = 0,
        cost_usd: float = 0.0,
        seconds: float = 0.0,
        capability_calls: int = 0,
    ) -> None:
        with self._lock:
            axis = self.would_exceed(
                tokens=tokens,
                cost_usd=cost_usd,
                seconds=seconds,
                capability_calls=capability_calls,
            )
            if axis is not None:
                limit = getattr(self.budget, f"max_{axis}")
                raise BudgetExceeded(axis, float(limit), float(getattr(self, axis)))
            self.tokens += tokens
            self.cost_usd += cost_usd
            self.seconds += seconds
            self.capability_calls += capability_calls

    def remaining(self) -> dict[str, float | None]:
        return {
            "tokens": _remaining(self.budget.max_tokens, self.tokens),
            "cost_usd": _remaining(self.budget.max_cost_usd, self.cost_usd),
            "seconds": _remaining(self.budget.max_seconds, self.seconds),
            "capability_calls": _remaining(
                self.budget.max_capability_calls, self.capability_calls
            ),
        }

    def spent(self) -> dict[str, float]:
        return {
            "tokens": float(self.tokens),
            "cost_usd": self.cost_usd,
            "seconds": self.seconds,
            "capability_calls": float(self.capability_calls),
        }


def _remaining(limit: int | float | None, used: int | float) -> float | None:
    return None if limit is None else max(0.0, float(limit) - float(used))


class BudgetManager:
    def __init__(
        self,
        tier_budgets: Mapping[TrustTier, Budget] | None = None,
        default: Budget | None = None,
    ) -> None:
        self.tier_budgets = dict(tier_budgets or DEFAULT_TIER_BUDGETS)
        self.default = default or Budget()

    def budget_for(self, identity: IdentityState) -> Budget:
        return self.tier_budgets.get(identity.tier, self.default)

    def open(self, intent: Intent, identity: IdentityState) -> BudgetAccount:
        return BudgetAccount(intent.intent_id, self.budget_for(identity))


class BudgetSnapshot(BaseModel):
    """Serialisable view of an account, for the ledger and telemetry."""

    intent_id: str
    limits: Budget
    spent: dict[str, float] = Field(default_factory=dict)
    remaining: dict[str, float | None] = Field(default_factory=dict)

    @classmethod
    def of(cls, account: BudgetAccount) -> "BudgetSnapshot":
        return cls(
            intent_id=account.intent_id,
            limits=account.budget,
            spent=account.spent(),
            remaining=account.remaining(),
        )
