"""Authentication guard for mutable control-plane endpoints.

Covers: environment mutation, posture mutation, policy CRUD, and
Metasploit capability token minting (RIF issue #39).
"""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Depends, Header, HTTPException, status

ENV_VAR = "RIF_CONTROL_PLANE_API_KEYS"


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


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """FastAPI dependency that authenticates mutable control-plane requests.

    Fails closed: if no keys are configured via ``RIF_CONTROL_PLANE_API_KEYS``,
    every guarded request is rejected rather than silently allowed through.
    """
    configured = _configured_keys()
    if not configured:
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
    return x_api_key


ControlPlaneAuth = Depends(require_api_key)
