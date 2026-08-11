from rif_runtime.schemas import Posture

POSTURE_LADDER: tuple[Posture, ...] = (
    Posture.normal,
    Posture.elevated,
    Posture.restricted,
    Posture.locked,
)

# Denial-count thresholds shared by live ReflexiveLoop and forensic replay.
DENIALS_ELEVATED = 3
DENIALS_RESTRICTED = 10
DENIALS_LOCKED = 20


def posture_for_denials(denials: int) -> Posture:
    """Map an absolute denial count to the threshold posture it implies."""

    if denials >= DENIALS_LOCKED:
        return Posture.locked
    if denials >= DENIALS_RESTRICTED:
        return Posture.restricted
    if denials >= DENIALS_ELEVATED:
        return Posture.elevated
    return Posture.normal


def escalate_posture(current: Posture) -> Posture:
    """Raise posture by one rung, capped at ``locked``."""

    index = POSTURE_LADDER.index(Posture(current))
    return POSTURE_LADDER[min(index + 1, len(POSTURE_LADDER) - 1)]


class PostureManager:
    def next_posture(self, current: Posture, denials: int) -> Posture:
        """Escalate posture from denial pressure; never de-escalate.

        Threshold mapping alone would replace ``locked`` with ``elevated`` when
        the rolling window holds only 3–9 denials (e.g. after manual lock or
        partial aging). Ratchet with ``max`` on the ladder so posture only
        moves up; operators reset explicitly via ``POST /v1/posture/reset``.
        """

        current = Posture(current)
        candidate = posture_for_denials(denials)
        return max(current, candidate, key=POSTURE_LADDER.index)
