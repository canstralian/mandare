"""Route-surface regressions: recovered-state, version, and request validation."""

from fastapi.testclient import TestClient

from rif_runtime import __version__
from rif_runtime.api import app
from rif_runtime.auth import ENV_VAR
from rif_runtime.mcp.requests import MAX_TOKEN_TTL_SECONDS

client = TestClient(app)


def test_recovered_state_route_returns_replayed_state():
    # Regression: the route called runtime.recovered_summary(), which did not
    # exist -- every request 500'd with AttributeError.
    r = client.get("/v1/recovered-state")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "historical_decisions",
        "historical_denials",
        "graph_nodes",
        "graph_edges",
        "last_posture",
    }
    assert isinstance(body["historical_decisions"], int)


def test_persistence_summary_route():
    r = client.get("/v1/persistence/summary")
    assert r.status_code == 200
    assert "decisions_total" in r.json()


def test_app_version_tracks_package_version():
    # Regression: the FastAPI app hardcoded "0.1.0" while pyproject moved on.
    assert app.version == __version__
    assert client.get("/").json()["version"] == __version__


def test_openapi_schema_builds():
    # Guards the response_model annotations added to the routes: a bad
    # annotation surfaces here rather than at first request.
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/v1/recovered-state" in r.json()["paths"]


def test_mcp_invoke_rejects_wrong_types():
    r = client.post("/v1/mcp/invoke", json={"actor": 42, "target": ["not", "a", "str"]})
    assert r.status_code == 422


def test_mcp_invoke_applies_defaults():
    r = client.post("/v1/mcp/invoke", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["actor"] == "agent:mcp"
    assert body["action"] == "mcp.invoke"
    assert body["target"] == "unknown"


def test_metasploit_evaluate_requires_an_intent_key():
    r = client.post("/v1/mcp/metasploit/evaluate", json={"capability": "module.search"})
    assert r.status_code == 422


def test_metasploit_evaluate_rejects_unknown_mode():
    r = client.post(
        "/v1/mcp/metasploit/evaluate",
        json={
            "intent": {"capability": "module.search", "target": "cve-2017-0144"},
            "mode": "no_such_lane",
        },
    )
    assert r.status_code == 422


def test_token_route_rejects_non_positive_ttl(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "test-key")
    r = client.post(
        "/v1/mcp/metasploit/token",
        json={
            "intent": {"capability": "module.execute", "target": "10.10.10.5"},
            "ttl_seconds": 0,
        },
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422


def test_token_route_caps_ttl(monkeypatch):
    # Authority is time-bound: one approval must not mint a near-permanent grant.
    monkeypatch.setenv(ENV_VAR, "test-key")
    r = client.post(
        "/v1/mcp/metasploit/token",
        json={
            "intent": {"capability": "module.execute", "target": "10.10.10.5"},
            "ttl_seconds": MAX_TOKEN_TTL_SECONDS + 1,
        },
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422


def test_token_route_accepts_ttl_at_the_cap(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "test-key")
    r = client.post(
        "/v1/mcp/metasploit/token",
        json={
            "intent": {"capability": "module.execute", "target": "10.10.10.5"},
            "ttl_seconds": MAX_TOKEN_TTL_SECONDS,
        },
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 200
    assert r.json()["signature"]
