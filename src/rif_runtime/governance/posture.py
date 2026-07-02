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


class PostureManager:
    def next_posture(self, current: Posture, denials: int) -> Posture:
        if denials >= 20:
            return Posture.locked
        if denials >= 10:
            return Posture.restricted
        if denials >= 3:
            return Posture.elevated
        return current
