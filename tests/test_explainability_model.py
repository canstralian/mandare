from rif_runtime.explainability import DecisionExplanation
from rif_runtime.schemas import Decision, PolicyDecision, PolicyRequest, Posture


def test_decision_explanation_captures_causal_path():
    request = PolicyRequest(
        actor="agent:test",
        action="http.request",
        target="https://blocked.example.com",
    )
    decision = PolicyDecision(
        decision=Decision.deny,
        actor=request.actor,
        action=request.action,
        target=request.target,
        environment="RIF_Runtime",
        posture=Posture.normal,
        reason="host denied: blocked.example.com",
        matched_rule="network.host.denied",
    )

    explanation = DecisionExplanation.from_decision(
        request=request,
        decision=decision,
        posture_before=Posture.normal,
        posture_after=Posture.elevated,
        environment_snapshot={
            "networking_type": "limited",
            "allowed_hosts": ["api.anthropic.com"],
        },
    )

    assert explanation.actor == "agent:test"
    assert explanation.decision == Decision.deny
    assert explanation.matched_rule == "network.host.denied"
    assert explanation.precedence == ("posture", "mcp", "package", "network", "default")
    assert explanation.posture_before == Posture.normal
    assert explanation.posture_after == Posture.elevated
    assert explanation.replay_consistent is True
