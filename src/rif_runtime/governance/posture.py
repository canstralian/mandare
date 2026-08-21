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


def posture_severity(posture: Posture) -> int:
    """Rung of ``posture`` on the ladder; higher is more restrictive."""

    return POSTURE_LADDER.index(Posture(posture))


def at_least_posture(current: Posture, floor: Posture) -> Posture:
    """The more restrictive of ``current`` and ``floor``.

    Used to apply a configured posture as a lower bound rather than an
    assignment, so configuration can only ever tighten the runtime.
    """

    return max(Posture(current), Posture(floor), key=posture_severity)


class PostureManager:
    def next_posture(self, current: Posture, denials: int) -> Posture:
        if denials >= 20:
            return Posture.locked
        if denials >= 10:
            return Posture.restricted
        if denials >= 3:
            return Posture.elevated
        return current
