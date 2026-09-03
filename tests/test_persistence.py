from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest


def test_decision_written():
    r = RIFRuntime()
    r.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://api.anthropic.com",
        )
    )
    # Asserted against the runtime's own configured path rather than a literal
    # data/decisions.jsonl, so the test follows RIF_DATA_DIR.
    assert r.decisions_path.exists()
