from .telemetry import TelemetryStore
from .posture import PostureManager


class ReflexiveLoop:
    def __init__(self):
        self.telemetry = TelemetryStore()
        self.posture_manager = PostureManager()

    def observe(self, decision, current_posture):
        self.telemetry.record(decision)
        denials = self.telemetry.denial_count(minutes=60)
        return self.posture_manager.next_posture(current_posture, denials)
