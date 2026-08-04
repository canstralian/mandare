from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..schemas import PolicyDecision


@dataclass
class TelemetryStore:
    max_events: int = 1000
    events: deque[PolicyDecision] = field(default_factory=deque)

    def record(self, decision: PolicyDecision) -> None:
        """Store a policy decision, retaining no more than the configured maximum number of events."""
        self.events.append(decision)
        while len(self.events) > self.max_events:
            self.events.popleft()

    def recent(self, minutes: int = 60) -> list[PolicyDecision]:
        """
        Retrieve policy decisions recorded within the specified number of minutes.
        
        Parameters:
            minutes (int): Lookback period in minutes from the current UTC time.
        
        Returns:
            list[PolicyDecision]: Decisions with timestamps at or after the UTC cutoff.
        """
        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp >= cutoff]

    def denial_count(self, minutes: int = 60) -> int:
        """Count denied policy decisions recorded within the specified time window.
        
        Parameters:
        	minutes (int): Number of minutes to include before the current time.
        
        Returns:
        	int: Number of recent policy decisions with a decision of `"deny"`.
        """
        return sum(1 for e in self.recent(minutes) if e.decision == "deny")
