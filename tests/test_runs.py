"""Tests for the POST /v1/runs endpoint and Supabase integration helpers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rif_runtime.api import app
from rif_runtime.integrations import supabase as sb

client = TestClient(app)


# ── Supabase integration unit tests ───────────────────────────────────────────


def test_write_evidence_noop_without_supabase_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    sb.reset_clients()
    # Must not raise even when supabase is not installed or configured.
    sb.write_evidence("run-1", "policy_decision", {"decision": "allow"})


def test_write_run_noop_without_supabase_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    sb.reset_clients()
    sb.write_run("run-1", "user-1", "policy_approved", "test prompt")


def test_update_run_status_noop_without_supabase_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    sb.reset_clients()
    sb.update_run_status("run-1", "succeeded")


def test_verify_jwt_raises_503_when_not_configured(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    sb.reset_clients()

    with pytest.raises(HTTPException) as exc_info:
        sb.verify_jwt("fake.jwt.token")
    assert exc_info.value.status_code == 503


def test_service_client_raises_when_not_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    sb.reset_clients()

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        sb.service_client()


# ── /v1/runs endpoint tests ───────────────────────────────────────────────────


def test_runs_returns_401_without_auth_header():
    r = client.post("/v1/runs", json={"prompt": "hello"})
    assert r.status_code == 401


def test_runs_returns_503_when_supabase_not_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    sb.reset_clients()

    r = client.post(
        "/v1/runs",
        json={"prompt": "hello"},
        headers={"Authorization": "Bearer fake.token"},
    )
    assert r.status_code == 503


def test_runs_creates_run_with_valid_identity(monkeypatch):
    """A patched identity + prompt → valid RunRecord schema."""
    identity_id = "user-uuid-allowed"

    monkeypatch.setattr(sb, "verify_jwt", lambda _token: identity_id)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    sb.reset_clients()

    r = client.post(
        "/v1/runs",
        json={"prompt": "list allowed hosts"},
        headers={"Authorization": "Bearer any.token"},
    )

    # Policy decision (allow or deny) depends on the CI environment; both are
    # valid — assert only schema conformance.
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        body = r.json()
        assert body["identity_id"] == identity_id
        assert body["status"] in ("policy_approved", "denied")
        assert "run_id" in body
        assert "created_at" in body
    else:
        assert "X-RIF-Run-Id" in r.headers


def test_runs_evidence_written_regardless_of_decision(monkeypatch):
    """Evidence is captured on both allow and deny paths."""
    evidence_calls: list[tuple[str, str, dict]] = []

    def _capture(run_id: str, kind: str, payload: dict) -> None:
        evidence_calls.append((run_id, kind, payload))

    identity_id = "user-uuid-evidence"
    monkeypatch.setattr(sb, "verify_jwt", lambda _token: identity_id)
    monkeypatch.setattr(sb, "write_evidence", _capture)
    monkeypatch.setattr(sb, "write_run", lambda *_: None)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    sb.reset_clients()

    r = client.post(
        "/v1/runs",
        json={"prompt": "query graph"},
        headers={"Authorization": "Bearer any.token"},
    )

    assert len(evidence_calls) == 1
    run_id_used, kind, payload = evidence_calls[0]
    assert kind == "policy_decision"
    assert "decision" in payload

    if r.status_code == 200:
        assert r.json()["run_id"] == run_id_used
    else:
        assert r.headers.get("X-RIF-Run-Id") == run_id_used
