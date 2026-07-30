from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from rif_runtime.schemas import Decision, PolicyDecision


@dataclass
class TelemetryStore:
    max_events: int = 1000
    events: deque[PolicyDecision] = field(default_factory=deque)

    def record(self, decision: PolicyDecision) -> None:
        self.events.append(decision)
        while len(self.events) > self.max_events:
            self.events.popleft()

    def recent(self, minutes: int = 60) -> list[PolicyDecision]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp >= cutoff]

    def denial_count(self, minutes: int = 60) -> int:
        return sum(1 for e in self.recent(minutes) if e.decision == Decision.deny)
