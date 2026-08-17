from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..schemas import PolicyDecision


@dataclass
class TelemetryStore:
    max_events: int = 1000
    events: deque[PolicyDecision] = field(default_factory=deque)

    def record(self, decision: PolicyDecision) -> None:
        self.events.append(decision)
        while len(self.events) > self.max_events:
            self.events.popleft()

    def clear(self) -> None:
        """Drop the rolling window (used by posture reset)."""

        self.events.clear()

    def recent(self, minutes: int = 60) -> list[PolicyDecision]:
        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp >= cutoff]

    def denial_count(self, minutes: int = 60) -> int:
        return sum(1 for e in self.recent(minutes) if e.decision == "deny")
