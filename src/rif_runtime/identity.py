"""Identity resolution: who is asking, and how much trust that confers.

Deny by default. An actor the resolver does not recognise resolves to the
``untrusted`` tier rather than to a permissive default, so an unregistered
principal can never route to a capability that requires standing.

Trust tier is an *input* to governance, never a substitute for it: a high tier
widens what the router may consider, but every capability call is still
evaluated by the policy engine.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .intent import Intent


class TrustTier(str, Enum):
    """Ordered standing. Compare with `tier_rank`, never with `<` on the enum."""

    untrusted = "untrusted"
    standard = "standard"
    elevated = "elevated"
    operator = "operator"


TRUST_LADDER: tuple[TrustTier, ...] = (
    TrustTier.untrusted,
    TrustTier.standard,
    TrustTier.elevated,
    TrustTier.operator,
)

# Actor prefix -> tier. Mirrors the actor vocabulary already used across the
# runtime ("agent:orchestrator", "human:operator").
PREFIX_TIERS: Mapping[str, TrustTier] = {
    "human:": TrustTier.operator,
    "service:": TrustTier.elevated,
    "agent:": TrustTier.standard,
}


def tier_rank(tier: TrustTier) -> int:
    return TRUST_LADDER.index(TrustTier(tier))


class IdentityState(BaseModel):
    principal: str
    actor: str
    tier: TrustTier = TrustTier.untrusted
    roles: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def at_least(self, tier: TrustTier) -> bool:
        return tier_rank(self.tier) >= tier_rank(tier)


class IdentityResolver:
    """Maps an intent's actor onto standing.

    ``registry`` pins specific actors to an explicit identity; anything else
    falls back to the actor-prefix convention, and an unrecognised prefix
    resolves to ``untrusted``.
    """

    def __init__(self, registry: Mapping[str, IdentityState] | None = None) -> None:
        self.registry = dict(registry or {})

    def register(self, identity: IdentityState) -> IdentityState:
        self.registry[identity.actor] = identity
        return identity

    def resolve(self, intent: Intent) -> IdentityState:
        pinned = self.registry.get(intent.actor)
        if pinned is not None:
            return pinned
        return IdentityState(
            principal=intent.actor,
            actor=intent.actor,
            tier=self._tier_for(intent.actor),
        )

    def _tier_for(self, actor: str) -> TrustTier:
        for prefix, tier in PREFIX_TIERS.items():
            if actor.startswith(prefix):
                return tier
        return TrustTier.untrusted
