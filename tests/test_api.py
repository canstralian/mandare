from fastapi.testclient import TestClient

from rif_runtime.api import app

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


def test_posture_reset():
    elevated = client.post("/v1/posture/elevated")
    assert elevated.status_code == 200
    assert elevated.json()["posture"] == "elevated"

    reset = client.post("/v1/posture/reset")
    assert reset.status_code == 200
    assert reset.json()["posture"] == "normal"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["posture"] == "normal"
