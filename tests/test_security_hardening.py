"""Tests for the security-hardening PR.

Covers:
- RequestIDMiddleware (X-Request-ID injection & passthrough)
- RateLimitMiddleware (token bucket + 429)
- Auth lockout (brute-force blocking + reset)
- Metasploit signing key derivation (HKDF from RIF_SECRET_KEY)
"""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from rif_runtime.auth import (
    _is_locked_out,
    _record_failure,
    configure_lockout,
    reset_lockout_state,
)
from rif_runtime.middleware import RateLimitMiddleware, RequestIDMiddleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _echo_app(request: Request) -> JSONResponse:
    """Trivial ASGI endpoint that echoes the request-id from state."""
    rid = getattr(request.state, "request_id", None)
    return JSONResponse({"request_id": rid})


@pytest.fixture()
def client_with_middleware() -> TestClient:
    """TestClient against a tiny Starlette app with both middlewares."""
    app = Starlette(routes=[Route("/echo", _echo_app)])
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware, rate=5.0, burst=5)
    return TestClient(app, raise_server_errors=True)


@pytest.fixture(autouse=True)
def _reset_lockout() -> None:
    """Ensure lockout state is clean between tests."""
    reset_lockout_state()
    configure_lockout(attempts=10, window_seconds=60.0)


# ---------------------------------------------------------------------------
# RequestIDMiddleware
# ---------------------------------------------------------------------------


class TestRequestIDMiddleware:
    def test_generates_uuid_when_absent(
        self, client_with_middleware: TestClient
    ) -> None:
        resp = client_with_middleware.get("/echo")
        assert resp.status_code == 200
        rid = resp.headers["x-request-id"]
        # UUID4 format: 8-4-4-4-12 hex chars
        assert len(rid) == 36
        assert rid.count("-") == 4

    def test_preserves_existing_header(
        self, client_with_middleware: TestClient
    ) -> None:
        resp = client_with_middleware.get(
            "/echo", headers={"x-request-id": "my-custom-id"}
        )
        assert resp.status_code == 200
        assert resp.headers["x-request-id"] == "my-custom-id"
        assert resp.json()["request_id"] == "my-custom-id"


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    def test_allows_requests_within_burst(
        self, client_with_middleware: TestClient
    ) -> None:
        # burst=5, so first 5 should succeed
        for _ in range(5):
            resp = client_with_middleware.get("/echo")
            assert resp.status_code == 200

    def test_returns_429_after_burst_exceeded(
        self, client_with_middleware: TestClient
    ) -> None:
        # Exhaust the burst
        for _ in range(5):
            client_with_middleware.get("/echo")
        # Next should be rate-limited
        resp = client_with_middleware.get("/echo")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.json()["detail"] == "rate limit exceeded"

    def test_bucket_refills_over_time(
        self, client_with_middleware: TestClient
    ) -> None:
        # Exhaust burst
        for _ in range(5):
            client_with_middleware.get("/echo")
        # Wait enough for 1 token (rate=5/s -> 0.2s per token)
        time.sleep(0.3)
        resp = client_with_middleware.get("/echo")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Auth lockout
# ---------------------------------------------------------------------------


class TestAuthLockout:
    def test_not_locked_initially(self) -> None:
        assert not _is_locked_out("192.168.1.1")

    def test_locks_out_after_threshold(self) -> None:
        configure_lockout(attempts=3, window_seconds=60.0)
        ip = "10.0.0.1"
        for _ in range(3):
            _record_failure(ip)
        assert _is_locked_out(ip)

    def test_different_ips_independent(self) -> None:
        configure_lockout(attempts=3, window_seconds=60.0)
        for _ in range(3):
            _record_failure("10.0.0.1")
        assert _is_locked_out("10.0.0.1")
        assert not _is_locked_out("10.0.0.2")

    def test_reset_clears_state(self) -> None:
        configure_lockout(attempts=2, window_seconds=60.0)
        _record_failure("10.0.0.1")
        _record_failure("10.0.0.1")
        assert _is_locked_out("10.0.0.1")
        reset_lockout_state()
        assert not _is_locked_out("10.0.0.1")


# ---------------------------------------------------------------------------
# Metasploit signing key derivation
# ---------------------------------------------------------------------------


class TestSigningKeyDerivation:
    def test_explicit_key_takes_precedence(self) -> None:
        with patch.dict(
            os.environ,
            {"RIF_MSF_SIGNING_KEY": "explicit-key"},
            clear=False,
        ):
            from rif_runtime.mcp.metasploit import _derive_signing_key

            assert _derive_signing_key() == "explicit-key"

    def test_derives_from_secret_key(self) -> None:
        env = {
            "RIF_SECRET_KEY": "my-app-secret",
        }
        with patch.dict(os.environ, env, clear=False):
            # Remove explicit key if present
            os.environ.pop("RIF_MSF_SIGNING_KEY", None)
            from rif_runtime.mcp.metasploit import _derive_signing_key

            key = _derive_signing_key()
            # Derived key is a hex string (64 chars for 32 bytes)
            assert len(key) == 64
            assert all(c in "0123456789abcdef" for c in key)

    def test_derived_key_is_deterministic(self) -> None:
        env = {"RIF_SECRET_KEY": "deterministic-test"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("RIF_MSF_SIGNING_KEY", None)
            from rif_runtime.mcp.metasploit import _derive_signing_key

            key1 = _derive_signing_key()
            key2 = _derive_signing_key()
            assert key1 == key2
