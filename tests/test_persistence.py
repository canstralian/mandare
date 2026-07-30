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
    # Assert against the store's own path: the data directory is relocatable
    # via RIF_DATA_DIR (conftest points it at a tmp dir).
    assert r.decisions_store.path.exists()
