"""The posture ladder: single source of truth for governance escalation.

Posture is monotonic under observation. Denial volume can only ever raise it;
nothing in the reflexive loop lowers it. Standing down a posture is an explicit
operator act (``POST /v1/posture/reset``), never a side effect of traffic.

Both the live reflexive loop (``ReflexiveLoop.observe``) and forensic replay
(``ReplayEngine.recover``) derive posture from denial counts here, so a
replayed runtime lands on the same rung as the live one that produced the log.
"""

from rif_runtime.schemas import Posture

POSTURE_LADDER: tuple[Posture, ...] = (
    Posture.normal,
    Posture.elevated,
    Posture.restricted,
    Posture.locked,
)

# Denial count -> the posture that volume of denials implies, highest first.
DENIAL_THRESHOLDS: tuple[tuple[int, Posture], ...] = (
    (20, Posture.locked),
    (10, Posture.restricted),
    (3, Posture.elevated),
)


def posture_rank(posture: Posture) -> int:
    """Position of ``posture`` on the ladder; higher means more restrictive."""

    return POSTURE_LADDER.index(Posture(posture))


def escalate_posture(current: Posture) -> Posture:
    """Raise posture by one rung, capped at ``locked``."""

    return POSTURE_LADDER[min(posture_rank(current) + 1, len(POSTURE_LADDER) - 1)]


def posture_for_denials(denials: int) -> Posture:
    """The posture floor implied by ``denials`` observed in the rolling window."""

    for threshold, posture in DENIAL_THRESHOLDS:
        if denials >= threshold:
            return posture
    return Posture.normal


def next_posture(current: Posture, denials: int) -> Posture:
    """Apply the denial-derived floor to ``current`` without de-escalating.

    Returns whichever of the two is higher on the ladder. Taking the max is
    what makes escalation one-way: a runtime driven to ``locked`` (by an
    operator, or by a severe MCP outcome) must not fall back to ``elevated``
    just because its rolling denial count sits in a lower band.
    """

    floor = posture_for_denials(denials)
    return floor if posture_rank(floor) > posture_rank(current) else Posture(current)


class PostureManager:
    """Collaborator seam for the reflexive loop; the rules live in this module."""

    def next_posture(self, current: Posture, denials: int) -> Posture:
        return next_posture(current, denials)
