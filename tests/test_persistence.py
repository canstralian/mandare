from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest
from pathlib import Path

def test_decision_written():
    r = RIFRuntime()
    r.evaluate(PolicyRequest(
        actor="agent:test",
        action="http.request",
        target="https://api.anthropic.com"
    ))
    assert Path("data/decisions.jsonl").exists()
