"""Supabase integration — optional dependency.

Install:      pip install "rif-runtime[supabase]"
Env vars:
    SUPABASE_URL              — project URL (required for any Supabase feature)
    SUPABASE_SERVICE_ROLE_KEY — used by the runtime for evidence/state writes
    SUPABASE_ANON_KEY         — used for verifying user JWTs from the frontend

The functions in this module are safe to import even when the supabase
package is not installed; errors surface only when they are called.

Evidence-write helpers (write_evidence, write_run, update_run_status) are
no-ops when SUPABASE_URL is not set, so the runtime works in local-only
deployments without any configuration changes.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

_MISSING_PKG = (
    "supabase package not installed — run: pip install 'rif-runtime[supabase]'"
)
_NOT_CONFIGURED_SVC = (
    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for evidence writes"
)
_NOT_CONFIGURED_ANON = (
    "SUPABASE_URL and SUPABASE_ANON_KEY must be set for JWT verification"
)

# Module-level singletons (lazily initialised).
_svc: Any = None
_anon: Any = None


def _create_client(url: str, key: str) -> Any:
    try:
        from supabase import create_client  # type: ignore[attr-defined]
    except ImportError as exc:
        raise ImportError(_MISSING_PKG) from exc
    return create_client(url, key)


def service_client() -> Any:
    """Singleton Supabase client authenticated with the service-role key."""
    global _svc
    if _svc is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError(_NOT_CONFIGURED_SVC)
        _svc = _create_client(url, key)
    return _svc


def anon_client() -> Any:
    """Singleton Supabase client authenticated with the anon key."""
    global _anon
    if _anon is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        if not url or not key:
            raise RuntimeError(_NOT_CONFIGURED_ANON)
        _anon = _create_client(url, key)
    return _anon


def verify_jwt(token: str) -> str:
    """Verify a Supabase JWT and return the user UUID string.

    Raises:
        HTTPException 401 — invalid or expired token
        HTTPException 503 — Supabase not configured or package not installed
    """
    try:
        client = anon_client()
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        response = client.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token verification failed",
        ) from exc

    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        )
    return str(response.user.id)


def write_evidence(run_id: str, kind: str, payload: dict[str, Any]) -> None:
    """Insert a row into the evidence_ledger table.

    No-ops silently when SUPABASE_URL is not set (local-only deployment).
    Exceptions are swallowed — local JSONL is the authoritative store.
    """
    if not os.environ.get("SUPABASE_URL"):
        return
    try:
        service_client().table("evidence_ledger").insert(
            {"run_id": run_id, "kind": kind, "payload": payload}
        ).execute()
    except Exception:
        logger.warning("supabase: evidence write failed [%s]", run_id, exc_info=True)


def write_run(run_id: str, identity_id: str, run_status: str, prompt: str) -> None:
    """Insert a row into the execution_runs table.

    No-ops silently when SUPABASE_URL is not set.
    """
    if not os.environ.get("SUPABASE_URL"):
        return
    try:
        service_client().table("execution_runs").insert(
            {
                "run_id": run_id,
                "identity_id": identity_id,
                "status": run_status,
                "prompt": prompt,
            }
        ).execute()
    except Exception:
        logger.warning("supabase: run write failed [%s]", run_id, exc_info=True)


def update_run_status(run_id: str, run_status: str) -> None:
    """Update the status column of an execution_runs row.

    No-ops silently when SUPABASE_URL is not set.
    """
    if not os.environ.get("SUPABASE_URL"):
        return
    try:
        service_client().table("execution_runs").update({"status": run_status}).eq(
            "run_id", run_id
        ).execute()
    except Exception:
        logger.warning("supabase: status update failed [%s]", run_id, exc_info=True)


def reset_clients() -> None:
    """Reset the module-level client singletons (for testing)."""
    global _svc, _anon
    _svc = None
    _anon = None
