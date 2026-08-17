from rif_runtime.schemas import Posture

POSTURE_LADDER: tuple[Posture, ...] = (
    Posture.normal,
    Posture.elevated,
    Posture.restricted,
    Posture.locked,
)


def escalate_posture(current: Posture) -> Posture:
    """Raise posture by one rung, capped at ``locked``."""

    index = POSTURE_LADDER.index(Posture(current))
    return POSTURE_LADDER[min(index + 1, len(POSTURE_LADDER) - 1)]


def posture_for_denials(denials: int) -> Posture:
    """Map a denial count to the minimum posture those denials imply.

    Used by reflexive escalation and by decision-log restore fallback.
    Absolute mapping (no current posture): below the elevated threshold this
    returns ``normal``.
    """

    if denials >= 20:
        return Posture.locked
    if denials >= 10:
        return Posture.restricted
    if denials >= 3:
        return Posture.elevated
    return Posture.normal


class PostureManager:
    def next_posture(self, current: Posture, denials: int) -> Posture:
        """Advance posture from denial thresholds without ever de-escalating.

        Denial counts may only raise posture or leave it unchanged. Operator
        ``set_posture`` / ``POST /v1/posture/*`` remain the sole de-escalate
        path (e.g. after a restart TelemetryStore is empty, so three fresh
        denials must not drop a restored ``locked``/``restricted`` posture).
        """

        current = Posture(current)
        candidate = posture_for_denials(denials)
        if candidate == Posture.normal:
            return current
        if POSTURE_LADDER.index(candidate) < POSTURE_LADDER.index(current):
            return current
        return candidate
