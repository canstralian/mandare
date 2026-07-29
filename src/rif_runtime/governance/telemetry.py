from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class TelemetryStore:
    max_events: int = 1000
    events: deque = field(default_factory=deque)

    def record(self, decision):
        self.events.append(decision)
        while len(self.events) > self.max_events:
            self.events.popleft()

    def recent(self, minutes: int = 60):
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp >= cutoff]

    def denial_count(self, minutes: int = 60):
        return sum(1 for e in self.recent(minutes) if e.decision == "deny")
