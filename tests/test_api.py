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
