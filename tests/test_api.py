import json

from fastapi.testclient import TestClient

from rif_runtime import api
from rif_runtime.api import app
from rif_runtime.auth import ENV_VAR
from rif_runtime.replay import ReplayEngine

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


def _decision_row(actor, target, decision="allow"):
    """
    Build a decision-log record with the specified actor, target, and decision.
    
    Parameters:
    	actor: The actor associated with the decision.
    	target: The target of the request.
    	decision: The decision recorded for the request.
    
    Returns:
    	dict: A decision-log record containing the supplied values and fixed test metadata.
    """
    return {
        "decision": decision,
        "actor": actor,
        "action": "http.request",
        "target": target,
        "environment": "RIF_CI",
        "posture": "normal",
        "reason": "seeded",
        "matched_rule": "default.allow",
    }


def test_recovered_state(tmp_path, monkeypatch):
    # Regression: this route previously called a non-existent
    # runtime.recovered_summary() and returned 500 on every request.
    #
    # Seeded through tmp_path rather than the shared data/decisions.jsonl so
    # the counts below are deterministic and unaffected by other tests.
    log = tmp_path / "decisions.jsonl"
    rows = [
        _decision_row("agent:a", "https://x.example.com"),
        _decision_row("agent:a", "https://y.example.com", decision="deny"),
        _decision_row("agent:b", "https://y.example.com", decision="deny"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        api, "ReplayEngine", lambda *a, **kw: ReplayEngine(str(log)), raising=True
    )

    r = client.get("/v1/recovered-state")
    assert r.status_code == 200
    body = r.json()
    assert body["historical_decisions"] == 3
    assert body["historical_denials"] == 2
    # actors agent:a, agent:b + targets x, y = 4 distinct nodes; 3 edges
    assert body["graph_nodes"] == 4
    assert body["graph_edges"] == 3
    # 2 denials is below the elevated threshold of 3
    assert body["last_posture"] == "normal"


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


def test_metasploit_token_bad_ttl_returns_422_not_500(monkeypatch):
    # int(None) and int({}) raise TypeError rather than ValueError, so these
    # payloads used to escape the handler's except clause as a 500 while a
    # non-numeric string correctly produced a 422.
    monkeypatch.setenv(ENV_VAR, "test-key")
    headers = {"X-API-Key": "test-key"}
    intent = {"capability": "module.search", "target": "10.10.10.5"}

    for bad_ttl in (None, {}, [], "abc"):
        r = client.post(
            "/v1/mcp/metasploit/token",
            json={"intent": intent, "ttl_seconds": bad_ttl},
            headers=headers,
        )
        assert r.status_code == 422, f"ttl_seconds={bad_ttl!r} gave {r.status_code}"
