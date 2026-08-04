"""Authentication guard for mutable control-plane endpoints.

Covers: environment mutation, posture mutation, policy CRUD, and
Metasploit capability token minting (RIF issue #39).

Enterprise hardening (security-hardening PR):
- Brute-force lockout after N failed attempts per IP (sliding window).
- Structured JSON logging on every auth failure (never logs credentials).
- Request ID propagation from middleware.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections import deque

from fastapi import Depends, Header, HTTPException, Request, status

ENV_VAR = "RIF_CONTROL_PLANE_API_KEYS"

logger = logging.getLogger("rif_runtime.auth")

# ---------------------------------------------------------------------------
# Brute-force lockout state (module-level, thread-safe)
# ---------------------------------------------------------------------------

_lockout_lock = threading.Lock()
_failed_attempts: dict[str, deque[float]] = {}
_MAX_TRACKED_IPS = 10_000

# Defaults; overridden at startup from rif.toml [security] section.
_LOCKOUT_ATTEMPTS: int = 10
_LOCKOUT_WINDOW_SECONDS: float = 60.0


def configure_lockout(*, attempts: int = 10, window_seconds: float = 60.0) -> None:
    """Configure lockout thresholds (called during app startup)."""
    global _LOCKOUT_ATTEMPTS, _LOCKOUT_WINDOW_SECONDS  # noqa: PLW0603
    _LOCKOUT_ATTEMPTS = attempts
    _LOCKOUT_WINDOW_SECONDS = window_seconds


def _is_locked_out(ip: str) -> bool:
    """Check if an IP has exceeded the failure threshold."""
    with _lockout_lock:
        attempts = _failed_attempts.get(ip)
        if attempts is None:
            return False
        now = time.monotonic()
        # Evict expired entries from the sliding window.
        while attempts and (now - attempts[0]) > _LOCKOUT_WINDOW_SECONDS:
            attempts.popleft()
        return len(attempts) >= _LOCKOUT_ATTEMPTS


def _record_failure(ip: str) -> None:
    """Record a failed auth attempt for the given IP."""
    with _lockout_lock:
        if ip not in _failed_attempts:
            if len(_failed_attempts) >= _MAX_TRACKED_IPS:
                # Drop an arbitrary idle entry to bound memory under IP rotation.
                _failed_attempts.pop(next(iter(_failed_attempts)))
            _failed_attempts[ip] = deque()
        _failed_attempts[ip].append(time.monotonic())


def reset_lockout_state() -> None:
    """Reset all lockout state (useful in tests)."""
    with _lockout_lock:
        _failed_attempts.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configured_keys() -> set[str]:
    """Read the comma-separated allowlist of API keys from the environment."""
    raw = os.getenv(ENV_VAR, "")
    return {key.strip() for key in raw.split(",") if key.strip()}


def _digest(value: str) -> bytes:
    """Fixed-length digest of ``value``.

    Comparing digests instead of raw strings means every comparison is the
    same length, so ``hmac.compare_digest`` never raises on a length
    mismatch between the supplied key and a configured key.
    """
    return hashlib.sha256(value.encode("utf-8")).digest()


def _sanitize_log_token(value: str) -> str:
    """Strip CR/LF so user-controlled values cannot forge log lines."""
    return value.replace("\r", "").replace("\n", "")


def _log_auth_failure(request: Request, reason: str) -> None:
    """Emit a structured log entry for an authentication failure."""
    request_id = getattr(request.state, "request_id", "unknown")
    client_ip = request.client.host if request.client else "unknown"
    path = _sanitize_log_token(request.url.path)
    entry = {
        "event": "auth_failure",
        "request_id": _sanitize_log_token(str(request_id)),
        "ip": _sanitize_log_token(client_ip),
        "path": path,
        "reason": reason,
    }
    logger.warning(json.dumps(entry, separators=(",", ":")))


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """FastAPI dependency that authenticates mutable control-plane requests.

    Fails closed: if no keys are configured via ``RIF_CONTROL_PLANE_API_KEYS``,
    every guarded request is rejected rather than silently allowed through.

    Enterprise hardening:
    - Returns 403 (not 401) after lockout to avoid timing oracle.
    - Structured logging on failure (never logs credentials).
    """
    client_ip = request.client.host if request.client else "unknown"

    # Check lockout FIRST (before any key comparison).
    if _is_locked_out(client_ip):
        _log_auth_failure(request, "locked_out")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="too many failed authentication attempts",
        )

    configured = _configured_keys()
    if not configured:
        _log_auth_failure(request, "not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="control-plane authentication is not configured",
        )

    candidate = _digest(x_api_key) if x_api_key else b""
    # Evaluate every comparison (fixed-length digests, so no ValueError on
    # length mismatch) before checking the outcome, so the check takes the
    # same time regardless of which configured key -- if any -- matches.
    matches = [hmac.compare_digest(candidate, _digest(key)) for key in configured]
    if not x_api_key or not any(matches):
        # Only count toward lockout when a key was actually supplied — missing
        # headers are misconfiguration/probes, not brute-force guessing.
        if x_api_key is not None:
            _record_failure(client_ip)
        _log_auth_failure(
            request, "invalid_key" if x_api_key is not None else "missing_key"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
    return x_api_key


ControlPlaneAuth = Depends(require_api_key)
