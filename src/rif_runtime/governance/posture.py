"""Governance posture management with configurable thresholds.

Posture escalation is driven by denial counts within a sliding window.
Thresholds are configurable via ``[governance]`` in ``rif.toml`` or injected
directly as a ``PostureThresholds`` instance.
"""

from __future__ import annotations

from dataclasses import dataclass

from rif_runtime.schemas import Posture

POSTURE_LADDER: tuple[Posture, ...] = (
    Posture.normal,
    Posture.elevated,
    Posture.restricted,
    Posture.locked,
)


@dataclass(frozen=True, slots=True)
class PostureThresholds:
    """Configurable denial-count thresholds for posture escalation.

    Defaults match the original hardcoded values so existing behaviour
    is preserved when no explicit configuration is provided.
    """

    elevated_at: int = 3
    restricted_at: int = 10
    locked_at: int = 20


def escalate_posture(current: Posture) -> Posture:
    """Raise posture by one rung, capped at ``locked``."""

    index = POSTURE_LADDER.index(Posture(current))
    return POSTURE_LADDER[min(index + 1, len(POSTURE_LADDER) - 1)]


class PostureManager:
    """Determines the next posture level based on denial counts.

    Args:
        thresholds: Optional configurable thresholds. Falls back to
                    defaults matching the original hardcoded values.
    """

    def __init__(self, thresholds: PostureThresholds | None = None) -> None:
        self._thresholds = thresholds or PostureThresholds()

    @property
    def thresholds(self) -> PostureThresholds:
        """Return the active threshold configuration."""
        return self._thresholds

    def next_posture(self, current: Posture, denials: int) -> Posture:
        """Compute the next posture level given current denial count."""
        if denials >= self._thresholds.locked_at:
            return Posture.locked
        if denials >= self._thresholds.restricted_at:
            return Posture.restricted
        if denials >= self._thresholds.elevated_at:
            return Posture.elevated
        return current
