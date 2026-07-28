"""Governance: policy decisions, posture, and the reflexive loop.

`GovernanceEngine` is exported lazily. `runtime.py` imports this package for
`reflexive`/`posture`, while `engine.py` reaches back through `context` to
`state`, which imports `runtime` — an eager re-export would close that cycle at
import time.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - types only
    from .engine import GovernanceDecision, GovernanceEngine

__all__ = ["GovernanceDecision", "GovernanceEngine"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import engine

        return getattr(engine, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
