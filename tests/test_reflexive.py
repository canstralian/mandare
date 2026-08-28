from mandare.runtime import MandareRuntime
from mandare.schemas import PolicyRequest


def test_reflexive_escalates_after_three_denials():
    r = MandareRuntime()
    for i in range(3):
        r.evaluate(
            PolicyRequest(
                actor="agent:test",
                action="http.request",
                target=f"https://evil{i}.example.com",
            )
        )
    assert r.posture == "elevated"


def test_graph_records_decisions():
    r = MandareRuntime()
    r.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://api.anthropic.com/v1/messages",
        )
    )
    assert r.graph_summary()["edges"] == 1
