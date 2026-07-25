from fastapi.testclient import TestClient
from rif_runtime.api import app
from rif_runtime.auth import ENV_VAR

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_telemetry_summary():
    r = client.get("/v1/telemetry/summary")
    assert r.status_code == 200
    assert "event_count" in r.json()


def test_graph_summary():
    r = client.get("/v1/graph/summary")
    assert r.status_code == 200
    assert "edges" in r.json()


def test_mcp_invoke_is_dry_run_no_side_effects():
    # /v1/mcp/invoke is unauthenticated, so it must simulate only: a would-be
    # denial must not persist a decision or drive posture escalation.
    from rif_runtime import api

    before = api.runtime.decisions_store.count()
    r = client.post(
        "/v1/mcp/invoke",
        json={"actor": "agent:test", "target": "https://blocked.example.com"},
    )
    assert r.status_code == 200
    assert "decision" in r.json()
    assert api.runtime.decisions_store.count() == before


def test_posture_reset(monkeypatch):
    # Posture routes are guarded by ControlPlaneAuth (PR #41); configure a key
    # and pass it so this test still exercises #44's reset route-ordering fix.
    monkeypatch.setenv(ENV_VAR, "test-key")
    headers = {"X-API-Key": "test-key"}

    elevated = client.post("/v1/posture/elevated", headers=headers)
    assert elevated.status_code == 200
    assert elevated.json()["posture"] == "elevated"

    reset = client.post("/v1/posture/reset", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["posture"] == "normal"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["posture"] == "normal"
