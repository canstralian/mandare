from ..schemas import PolicyDecision, Posture
from .posture import PostureManager
from .telemetry import TelemetryStore


class ReflexiveLoop:
    def __init__(self) -> None:
        self.telemetry = TelemetryStore()
        self.posture_manager = PostureManager()

    def observe(self, decision: PolicyDecision, current_posture: Posture) -> Posture:
        """
        Record a policy decision and calculate the next posture based on recent denials.
        
        Parameters:
            decision (PolicyDecision): The policy decision to record.
            current_posture (Posture): The posture currently in effect.
        
        Returns:
            Posture: The posture selected from the current posture and denials recorded during the previous 60 minutes.
        """
        self.telemetry.record(decision)
        denials = self.telemetry.denial_count(minutes=60)
        return self.posture_manager.next_posture(current_posture, denials)
