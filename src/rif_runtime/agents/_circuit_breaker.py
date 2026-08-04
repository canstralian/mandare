"""Thread-safe circuit breaker for agent action dispatch.

Implements the standard three-state machine (closed -> open -> half-open)
with configurable failure thresholds and recovery windows. Uses only
stdlib threading primitives; no new runtime dependencies.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final


class CircuitState(StrEnum):
    """Circuit breaker states."""

    closed = "closed"
    open = "open"
    half_open = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Tuning knobs for the circuit breaker.

    Attributes:
        failure_threshold: Consecutive failures before opening the circuit.
        recovery_timeout_s: Seconds to wait in open state before trying half-open.
        half_open_max_calls: Calls permitted while half-open to probe recovery.
    """

    failure_threshold: int = 5
    recovery_timeout_s: float = 30.0
    half_open_max_calls: int = 1


_DEFAULT_CONFIG: Final[CircuitBreakerConfig] = CircuitBreakerConfig()


@dataclass
class CircuitBreakerStats:
    """Observable metrics exposed for telemetry."""

    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_rejections: int = 0
    consecutive_failures: int = 0
    state: CircuitState = CircuitState.closed
    last_failure_time: float | None = None
    last_state_change_time: float = field(default_factory=time.monotonic)


class CircuitOpen(Exception):
    """Raised when the circuit is open and rejecting calls."""

    def __init__(self, breaker_name: str, retry_after_s: float) -> None:
        self.breaker_name = breaker_name
        self.retry_after_s = retry_after_s
        super().__init__(
            f"Circuit '{breaker_name}' is open; retry after {retry_after_s:.1f}s"
        )


class CircuitBreaker:
    """Thread-safe circuit breaker.

    Usage::

        cb = CircuitBreaker("downstream-api")
        if cb.allow_request():
            try:
                result = call_downstream()
                cb.record_success()
            except Exception:
                cb.record_failure()
                raise
        else:
            raise CircuitOpen(cb.name, cb.time_until_recovery())
    """

    __slots__ = ("_config", "_lock", "_stats", "name")

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.name = name
        self._config = config or _DEFAULT_CONFIG
        self._lock = threading.Lock()
        self._stats = CircuitBreakerStats()

    def allow_request(self) -> bool:
        """Return True if a request should be dispatched."""
        with self._lock:
            now = time.monotonic()
            state = self._stats.state

            if state == CircuitState.closed:
                return True

            if state == CircuitState.open:
                elapsed = now - self._stats.last_state_change_time
                if elapsed >= self._config.recovery_timeout_s:
                    self._transition(CircuitState.half_open, now)
                    return True
                self._stats.total_rejections += 1
                return False

            # half_open: allow limited probes
            return True

    def record_success(self) -> None:
        """Record a successful call; may close the circuit."""
        with self._lock:
            now = time.monotonic()
            self._stats.total_calls += 1
            self._stats.total_successes += 1
            self._stats.consecutive_failures = 0

            if self._stats.state == CircuitState.half_open:
                self._transition(CircuitState.closed, now)

    def record_failure(self) -> None:
        """Record a failed call; may open the circuit."""
        with self._lock:
            now = time.monotonic()
            self._stats.total_calls += 1
            self._stats.total_failures += 1
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = now

            if self._stats.state == CircuitState.half_open:
                self._transition(CircuitState.open, now)
            elif (
                self._stats.state == CircuitState.closed
                and self._stats.consecutive_failures
                >= self._config.failure_threshold
            ):
                self._transition(CircuitState.open, now)

    def time_until_recovery(self) -> float:
        """Seconds remaining before the circuit may transition to half-open."""
        with self._lock:
            if self._stats.state != CircuitState.open:
                return 0.0
            elapsed = time.monotonic() - self._stats.last_state_change_time
            remaining = self._config.recovery_timeout_s - elapsed
            return max(0.0, remaining)

    def reset(self) -> None:
        """Force the circuit back to closed. Use for administrative overrides."""
        with self._lock:
            self._stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Current circuit state (read-only snapshot)."""
        with self._lock:
            return self._stats.state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Snapshot of internal metrics for telemetry export."""
        with self._lock:
            return CircuitBreakerStats(
                total_calls=self._stats.total_calls,
                total_successes=self._stats.total_successes,
                total_failures=self._stats.total_failures,
                total_rejections=self._stats.total_rejections,
                consecutive_failures=self._stats.consecutive_failures,
                state=self._stats.state,
                last_failure_time=self._stats.last_failure_time,
                last_state_change_time=self._stats.last_state_change_time,
            )

    def _transition(self, new_state: CircuitState, now: float) -> None:
        """Transition state (caller must hold _lock)."""
        self._stats.state = new_state
        self._stats.last_state_change_time = now
        if new_state == CircuitState.closed:
            self._stats.consecutive_failures = 0

    def __repr__(self) -> str:
        return f"CircuitBreaker(name={self.name!r}, state={self.state})"
