"""PolicyEngine correctness: decision posture stamps and constraint denies."""

from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import EnvironmentProfile, PolicyRequest, Posture


def _limited_profile(**overrides: object) -> EnvironmentProfile:
    data: dict = {
        "networking_type": "limited",
        "allowed_hosts": ["api.anthropic.com"],
        "allow_package_manager_network_access": False,
        "allow_mcp_server_network_access": False,
    }
    data.update(overrides)
    return EnvironmentProfile.model_validate(data)


def test_network_deny_stamps_live_posture_not_hardcoded_elevated():
    # Regression: constraint denies used to hardcode Posture.elevated on the
    # decision even when the runtime was still normal, poisoning the audit log.
    engine = PolicyEngine()
    decision = engine.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://blocked.example.com",
        ),
        "RIF_Runtime",
        _limited_profile(),
        Posture.normal,
    )
    assert decision.decision == "deny"
    assert decision.matched_rule == "network.host.denied"
    assert decision.posture == Posture.normal


def test_constraint_denies_preserve_restricted_posture():
    engine = PolicyEngine()
    decision = engine.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="package.install",
            target="https://pypi.org/simple/foo",
        ),
        "RIF_Runtime",
        _limited_profile(),
        Posture.restricted,
    )
    assert decision.decision == "deny"
    assert decision.matched_rule == "package.egress.disabled"
    assert decision.posture == Posture.restricted


def test_allow_still_stamps_live_posture():
    engine = PolicyEngine()
    decision = engine.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://api.anthropic.com/v1/messages",
        ),
        "RIF_Runtime",
        _limited_profile(),
        Posture.elevated,
    )
    assert decision.decision == "allow"
    assert decision.posture == Posture.elevated
