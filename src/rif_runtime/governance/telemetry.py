"""Governance telemetry with structured metrics emission.

Provides both the original ``TelemetryStore`` for in-memory event tracking
and a new ``MetricsRegistry`` for thread-safe structured metric emission
consumable by any log aggregator.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..schemas import PolicyDecision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Original TelemetryStore (unchanged public API)
# ---------------------------------------------------------------------------


@dataclass
class TelemetryStore:
    """In-memory ring buffer of recent policy decisions."""

    max_events: int = 1000
    events: deque[PolicyDecision] = field(default_factory=deque)

    def record(self, decision: PolicyDecision) -> None:
        self.events.append(decision)
        while len(self.events) > self.max_events:
            self.events.popleft()

    def recent(self, minutes: int = 60) -> list[PolicyDecision]:
        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
        return [e for e in self.events if e.timestamp >= cutoff]

    def denial_count(self, minutes: int = 60) -> int:
        return sum(1 for e in self.recent(minutes) if e.decision == "deny")


# ---------------------------------------------------------------------------
# Structured Metrics
# ---------------------------------------------------------------------------


def emit_metric(name: str, value: float, tags: dict[str, str]) -> None:
    """Emit a structured JSON log line consumable by any log aggregator.

    Format: {"metric": name, "value": value, "tags": {...}, "ts": iso_utc}
    """
    line = json.dumps(
        {
            "metric": name,
            "value": value,
            "tags": tags,
            "ts": datetime.now(UTC).isoformat(),
        },
        separators=(",", ":"),
    )
    logger.info(line)


class MetricsRegistry:
    """Thread-safe atomic counters with structured log emission.

    Tracks:
      - rif.decisions.total
      - rif.decisions.denied
      - rif.decisions.allowed
      - rif.posture.transitions
      - rif.policy.eval_latency_ms
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}

    def increment(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ) -> None:
        """Atomically increment a counter and emit a structured metric."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value
        emit_metric(name, value, tags or {})

    def record_latency(
        self, name: str, latency_ms: float, tags: dict[str, str] | None = None
    ) -> None:
        """Record a latency measurement (histogram-style emission)."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + latency_ms
        emit_metric(name, latency_ms, tags or {})

    def get(self, name: str) -> float:
        """Return current counter value (thread-safe read)."""
        with self._lock:
            return self._counters.get(name, 0.0)

    def snapshot(self) -> dict[str, float]:
        """Return a copy of all counters."""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._counters.clear()


# Module-level singleton for global access
metrics = MetricsRegistry()
