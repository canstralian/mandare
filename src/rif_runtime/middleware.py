"""Security middleware for RIF Runtime.

Provides rate limiting (token bucket per IP) and request ID injection.
Both middleware classes use only stdlib + starlette (shipped with FastAPI).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Soft cap on tracked client IPs to bound memory under IP rotation.
_MAX_BUCKETS = 10_000

# ---------------------------------------------------------------------------
# Request ID Middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject a unique ``X-Request-ID`` header into every request/response.

    If the incoming request already carries the header (e.g. from a load
    balancer) the existing value is preserved; otherwise a new UUID4 is
    generated.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        # Stash on request state so downstream code can access it.
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Token Bucket Rate Limiter
# ---------------------------------------------------------------------------


@dataclass
class _TokenBucket:
    """Per-IP token bucket state."""

    tokens: float
    last_refill: float
    lock: threading.Lock = field(default_factory=threading.Lock)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware implementing a per-IP token bucket rate limiter.

    Configuration:
        rate: tokens added per second (requests/second sustained rate).
        burst: maximum bucket capacity (peak burst tolerance).

    Client identity uses ``request.client.host`` (the direct peer). Behind a
    reverse proxy this is the proxy IP for every request, so the bucket
    collapses to a single shared limit unless the process is the TLS
    terminator. Trusted ``X-Forwarded-For`` parsing is intentionally not
    enabled by default (spoofable); put rate limiting at the edge or terminate
    TLS in-process if per-client limits are required.

    Returns HTTP 429 with a ``Retry-After`` header when the bucket is empty.
    """

    def __init__(
        self,
        app: Any,
        *,
        rate: float = 20.0,
        burst: int = 40,
    ) -> None:
        super().__init__(app)
        if rate <= 0:
            raise ValueError("rate must be positive")
        if burst < 1:
            raise ValueError("burst must be >= 1")
        self._rate = float(rate)
        self._burst = int(burst)
        self._buckets: dict[str, _TokenBucket] = {}
        self._global_lock = threading.Lock()

    def _get_bucket(self, ip: str) -> _TokenBucket:
        with self._global_lock:
            bucket = self._buckets.get(ip)
            if bucket is not None:
                return bucket
            if len(self._buckets) >= _MAX_BUCKETS:
                self._evict_stale_unlocked()
            # If still full after eviction, drop an arbitrary entry.
            if len(self._buckets) >= _MAX_BUCKETS:
                self._buckets.pop(next(iter(self._buckets)))
            bucket = _TokenBucket(
                tokens=float(self._burst), last_refill=time.monotonic()
            )
            self._buckets[ip] = bucket
            return bucket

    def _evict_stale_unlocked(self) -> None:
        """Drop buckets idle longer than time-to-refill a full burst."""
        idle_ttl = max(60.0, float(self._burst) / self._rate)
        now = time.monotonic()
        stale = [
            key
            for key, bucket in self._buckets.items()
            if (now - bucket.last_refill) > idle_ttl
        ]
        for key in stale:
            del self._buckets[key]

    def _consume(self, ip: str) -> bool:
        """Try to consume one token. Returns True if allowed."""
        bucket = self._get_bucket(ip)
        with bucket.lock:
            now = time.monotonic()
            elapsed = now - bucket.last_refill
            bucket.tokens = min(
                float(self._burst),
                bucket.tokens + elapsed * self._rate,
            )
            bucket.last_refill = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def _retry_after(self, ip: str) -> float:
        """Seconds until at least one token is available."""
        bucket = self._get_bucket(ip)
        with bucket.lock:
            deficit = 1.0 - bucket.tokens
            return max(0.0, deficit / self._rate)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        if not self._consume(client_ip):
            retry_after = self._retry_after(client_ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        return await call_next(request)
