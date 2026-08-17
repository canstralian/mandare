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
            result = current
        elif POSTURE_LADDER.index(candidate) < POSTURE_LADDER.index(current):
            result = current
        else:
            result = candidate
        # #region agent log
        import json
        import time

        open("/workspace/.cursor/debug-d042.log", "a").write(
            json.dumps(
                {
                    "id": f"log_{int(time.time() * 1000)}_np",
                    "timestamp": int(time.time() * 1000),
                    "location": "posture.py:next_posture",
                    "message": "next_posture inputs+return",
                    "data": {
                        "current": str(current),
                        "denials": denials,
                        "result": str(result),
                        "deescalated": (
                            Posture(result) != Posture(current)
                            and POSTURE_LADDER.index(Posture(result))
                            < POSTURE_LADDER.index(Posture(current))
                        ),
                        "runId": "post-fix",
                    },
                    "hypothesisId": "A",
                }
            )
            + "\n"
        )
        # #endregion
        return result
