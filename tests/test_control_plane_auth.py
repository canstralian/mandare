import os

from fastapi.testclient import TestClient

from rif_runtime.api import app
from rif_runtime.auth import ENV_VAR

client = TestClient(app)

GUARDED_REQUESTS = [
    ("post", "/v1/environment/default"),
    ("post", "/v1/posture/normal"),
    ("post", "/v1/posture/reset"),
    ("post", "/v1/mcp/metasploit/token", {"intent": {"capability": "module.search", "target": "10.10.10.5"}}),
    ("post", "/v1/policy/evaluate", {"actor": "agent:test", "action": "read", "target": "resource"}),
]


def _call(method, path, json=None, headers=None):
    return getattr(client, method)(path, json=json, headers=headers)


def test_guarded_endpoints_reject_when_no_keys_configured(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    for method, path, *rest in GUARDED_REQUESTS:
        body = rest[0] if rest else None
        response = _call(method, path, json=body)
        assert response.status_code == 503, f"{method} {path} did not fail closed"


def test_guarded_endpoints_reject_missing_or_wrong_key(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "correct-key")
    for method, path, *rest in GUARDED_REQUESTS:
        body = rest[0] if rest else None
        no_key = _call(method, path, json=body)
        assert no_key.status_code == 401

        wrong_key = _call(
            method, path, json=body, headers={"X-API-Key": "wrong-key"}
        )
        assert wrong_key.status_code == 401


def test_guarded_endpoints_accept_valid_key(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "correct-key")
    headers = {"X-API-Key": "correct-key"}

    response = _call("post", "/v1/environment/default", headers=headers)
    assert response.status_code != 401

    response = _call("post", "/v1/posture/normal", headers=headers)
    assert response.status_code != 401

    response = _call("post", "/v1/posture/reset", headers=headers)
    assert response.status_code != 401

    response = _call(
        "post",
        "/v1/mcp/metasploit/token",
        json={"intent": {"capability": "module.search", "target": "10.10.10.5"}},
        headers=headers,
    )
    assert response.status_code != 401

    response = _call(
        "post",
        "/v1/policy/evaluate",
        json={"actor": "agent:test", "action": "read", "target": "resource"},
        headers=headers,
    )
    assert response.status_code != 401


def test_policy_crud_requires_key(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "correct-key")
    headers = {"X-API-Key": "correct-key"}
    rule = {"id": "test-rule", "effect": "allow", "action": "*", "target": "*"}

    unauthenticated = client.put("/v1/policies/test-rule", json=rule)
    assert unauthenticated.status_code == 401

    authenticated = client.put("/v1/policies/test-rule", json=rule, headers=headers)
    assert authenticated.status_code != 401

    delete_unauth = client.delete("/v1/policies/test-rule")
    assert delete_unauth.status_code == 401

    delete_auth = client.delete("/v1/policies/test-rule", headers=headers)
    assert delete_auth.status_code != 401


def test_read_only_endpoints_stay_open(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert client.get("/health").status_code == 200
    assert client.get("/v1/environments").status_code == 200
    assert client.get("/v1/policies").status_code == 200


def test_api_key_length_mismatch_returns_401_not_500(monkeypatch):
    """Cursor Bugbot finding: a key shorter/longer than any configured key
    must not raise ValueError inside hmac.compare_digest -- it should fall
    through to a clean 401."""
    monkeypatch.setenv(ENV_VAR, "a-much-longer-configured-key-value")
    headers = {"X-API-Key": "short"}
    response = _call("post", "/v1/posture/normal", headers=headers)
    assert response.status_code == 401
