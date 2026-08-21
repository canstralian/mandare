"""Authentication guards for the control-plane surface.

Two guards, two scopes:

``require_api_key``  — mutable operations: environment mutation, posture
mutation, policy CRUD, and Metasploit capability token minting (RIF issue
#39). Always enforced, and fails closed when no keys are configured.

``require_read_api_key`` — read operations that disclose governance state
(the audit summary, the configured rules, recovered state, persistence and
telemetry counters). Enforcement is **opt-in** via ``RIF_REQUIRE_READ_AUTH``
so that existing read clients are not broken by an upgrade; when enabled it
accepts the same keys and fails closed the same way.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Depends, Header, HTTPException, status

ENV_VAR = "RIF_CONTROL_PLANE_API_KEYS"
READ_AUTH_ENV_VAR = "RIF_REQUIRE_READ_AUTH"
_TRUTHY = {"1", "true", "yes", "on"}


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
    """
    Authenticate a mutable control-plane request using a configured API key.
    
    Parameters:
    	x_api_key (str | None): API key supplied in the ``X-API-Key`` header.
    
    Returns:
    	str: The supplied API key when authentication succeeds.
    
    Raises:
    	HTTPException: With status 503 if no API keys are configured, or status 401
    		if the key is missing or invalid.
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


def read_auth_required() -> bool:
    """
    Determines whether authentication is required for read operations.
    
    Returns:
    	bool: `true` if `RIF_REQUIRE_READ_AUTH` is set to a recognized truthy value, `false` otherwise.
    """
    return os.getenv(READ_AUTH_ENV_VAR, "").strip().lower() in _TRUTHY


def require_read_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """
    Authenticate read requests when read authentication is enabled.
    
    Parameters:
        x_api_key (str | None): API key supplied in the ``X-API-Key`` header.
    
    Returns:
        str | None: The supplied API key when authentication is enabled and succeeds; ``None`` when read authentication is disabled.
    """
    if not read_auth_required():
        return None
    return require_api_key(x_api_key)


ControlPlaneAuth = Depends(require_api_key)
ReadPlaneAuth = Depends(require_read_api_key)
