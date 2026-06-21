from fastapi.testclient import TestClient
from rif_runtime.api import app

client = TestClient(app)

def test_audit_endpoint():
    r = client.get("/v1/audit")
    assert r.status_code == 200

def test_graph_endpoint():
    r = client.get("/v1/graph/summary")
    assert r.status_code == 200
