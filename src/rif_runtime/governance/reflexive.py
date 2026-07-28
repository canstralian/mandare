from __future__ import annotations

from rif_runtime.schemas import PolicyDecision, Posture

from .telemetry import TelemetryStore
from .posture import PostureManager


class ReflexiveLoop:
    def __init__(
        self,
        telemetry: TelemetryStore | None = None,
        posture_manager: PostureManager | None = None,
    ) -> None:
        # Collaborators are injectable so tests can drive the loop with a
        # pre-seeded telemetry window instead of replaying real traffic.
        self.telemetry = telemetry or TelemetryStore()
        self.posture_manager = posture_manager or PostureManager()

    def observe(self, decision: PolicyDecision, current_posture: Posture) -> Posture:
        self.telemetry.record(decision)
        denials = self.telemetry.denial_count(minutes=60)
        return self.posture_manager.next_posture(current_posture, denials)
