from fastapi.testclient import TestClient

from rif_runtime.api import app
from rif_runtime.auth import ENV_VAR
from rif_runtime.mcp.metasploit import GovernanceMode, MetasploitIntent
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import Posture

client = TestClient(app)


def test_capabilities_catalog_route():
    r = client.get("/v1/mcp/metasploit/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert "module.search" in body["read_only"]
    assert "module.execute" in body["consequential"]
    assert body["contract_hash"]


def test_evaluate_route_allows_read_only():
    r = client.post(
        "/v1/mcp/metasploit/evaluate",
        json={"intent": {"capability": "module.search", "target": "cve-2017-0144"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["decision"] == "allow"
    assert body["evidence"]["requested_capability"] == "module.search"


def test_evaluate_route_denies_execution():
    r = client.post(
        "/v1/mcp/metasploit/evaluate",
        json={
            "intent": {"capability": "exploit.run", "target": "10.10.10.5"},
            "mode": "read_only_firewall",
        },
    )
    body = r.json()
    assert body["decision"]["decision"] == "deny"
    assert body["decision"]["matched_rule"] == "msf.capability.execution_absent"


def test_token_mint_then_broker_allow_route(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "test-key")
    headers = {"X-API-Key": "test-key"}
    intent = {
        "capability": "module.execute",
        "target": "10.10.10.5",
        "params": {"rport": 445},
    }
    token = client.post(
        "/v1/mcp/metasploit/token",
        json={"intent": intent, "approver": "human:alice"},
        headers=headers,
    ).json()
    r = client.post(
        "/v1/mcp/metasploit/evaluate",
        json={"intent": intent, "mode": "lab_broker", "token": token},
    )
    body = r.json()
    assert body["decision"]["decision"] == "allow"
    assert body["decision"]["matched_rule"] == "msf.broker.authorized"


def test_evaluate_route_rejects_invalid_payload_with_422():
    r = client.post(
        "/v1/mcp/metasploit/evaluate",
        json={"intent": {"capability": "module.search"}},  # missing target
    )
    assert r.status_code == 422


def test_token_route_rejects_missing_intent_with_422(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "test-key")
    headers = {"X-API-Key": "test-key"}
    r = client.post(
        "/v1/mcp/metasploit/token",
        json={"approver": "human:alice"},
        headers=headers,
    )
    assert r.status_code == 422


def test_token_route_requires_api_key():
    r = client.post(
        "/v1/mcp/metasploit/token",
        json={
            "intent": {"capability": "module.execute", "target": "10.10.10.5"},
            "approver": "human:alice",
        },
    )
    assert r.status_code in (401, 503)


def test_runtime_severe_denial_escalates_posture():
    runtime = RIFRuntime()
    runtime.posture = Posture.normal
    intent = MetasploitIntent(capability="session.create", target="10.10.10.5")
    outcome = runtime.evaluate_metasploit(intent, mode=GovernanceMode.shadow)
    assert outcome.decision.decision == "deny"
    assert outcome.severe is True
    assert runtime.posture == Posture.elevated


def test_runtime_records_decision_and_evidence():
    runtime = RIFRuntime()
    before_decisions = runtime.decisions_store.count()
    before_evidence = runtime.evidence_store.count()
    intent = MetasploitIntent(capability="module.search", target="cve-2017-0144")
    runtime.evaluate_metasploit(intent)
    assert runtime.decisions_store.count() == before_decisions + 1
    assert runtime.evidence_store.count() == before_evidence + 1
