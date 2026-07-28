"""Execution telemetry: tokens, latency, capability calls, success.

Distinct from `governance/telemetry.py`, which tracks *decisions* in a rolling
window to drive posture. This module measures *executions* so the evolution
queue and operators can see cost and failure trends.

`elapsed()` is monotonic — it measures duration, so a wall-clock adjustment
mid-run cannot produce a negative or inflated latency in the ledger.
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TelemetrySample(BaseModel):
    intent_id: str | None = None
    tokens: int = 0
    latency_ms: float = 0.0
    capability_calls: int = 0
    success: bool = True
    error: str | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Telemetry:
    def __init__(self, max_samples: int = 1000) -> None:
        self.max_samples = max_samples
        self.samples: deque[TelemetrySample] = deque()
        self._started: float | None = None

    def start(self) -> None:
        self._started = time.monotonic()

    def elapsed_ms(self) -> float:
        if self._started is None:
            return 0.0
        return (time.monotonic() - self._started) * 1000.0

    def elapsed(self) -> float:
        """Seconds since `start()`, for budget accounting."""

        return self.elapsed_ms() / 1000.0

    def capture(
        self,
        tokens: int = 0,
        latency_ms: float | None = None,
        capability_calls: int = 0,
        success: bool = True,
        error: str | None = None,
        intent_id: str | None = None,
    ) -> TelemetrySample:
        sample = TelemetrySample(
            intent_id=intent_id,
            tokens=tokens,
            latency_ms=self.elapsed_ms() if latency_ms is None else latency_ms,
            capability_calls=capability_calls,
            success=success,
            error=error,
        )
        self.samples.append(sample)
        while len(self.samples) > self.max_samples:
            self.samples.popleft()
        return sample

    def summary(self) -> dict[str, Any]:
        total = len(self.samples)
        if total == 0:
            return {
                "executions": 0,
                "failures": 0,
                "total_tokens": 0,
                "total_capability_calls": 0,
                "mean_latency_ms": 0.0,
            }
        failures = sum(1 for s in self.samples if not s.success)
        return {
            "executions": total,
            "failures": failures,
            "total_tokens": sum(s.tokens for s in self.samples),
            "total_capability_calls": sum(s.capability_calls for s in self.samples),
            "mean_latency_ms": sum(s.latency_ms for s in self.samples) / total,
        }
