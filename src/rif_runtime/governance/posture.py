from rif_runtime.schemas import Posture


class PostureManager:
    def next_posture(self, current: Posture, denials: int) -> Posture:
        if denials >= 20:
            return Posture.locked
        if denials >= 10:
            return Posture.restricted
        if denials >= 3:
            return Posture.elevated
        return current
