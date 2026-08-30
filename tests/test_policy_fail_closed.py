from rif_runtime.configuration.policies import PolicyRule
from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import EnvironmentProfile, PolicyRequest, Posture


def _request(action: str = "http.request") -> PolicyRequest:
    return PolicyRequest(
        actor="agent:test",
        action=action,
        target="https://unmatched.example.net",
    )


def _open_profile() -> EnvironmentProfile:
    return EnvironmentProfile(networking_type="open", allowed_hosts=[])


def test_unmatched_request_is_denied_when_no_policy_rules_exist():
    decision = PolicyEngine().evaluate(
        _request(), "RIF_Test", _open_profile(), Posture.normal, []
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "default.deny"
    assert decision.reason == "no applicable policy rule"


def test_explicit_allow_still_wins_over_fail_closed_fallback():
    rule = PolicyRule(
        id="allow_example",
        effect="allow",
        action="http.request",
        target="unmatched.example.net",
    )

    decision = PolicyEngine().evaluate(
        _request(), "RIF_Test", _open_profile(), Posture.normal, [rule]
    )

    assert decision.decision == "allow"
    assert decision.matched_rule == "policy.allow_example"


def test_configured_catch_all_still_controls_unmatched_requests():
    rule = PolicyRule(
        id="deny_everything",
        effect="deny",
        action="*",
        target="*",
        reason="explicit catch-all",
    )

    decision = PolicyEngine().evaluate(
        _request(), "RIF_Test", _open_profile(), Posture.normal, [rule]
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "policy.deny_everything"
    assert decision.reason == "explicit catch-all"


def test_locked_posture_still_precedes_fail_closed_fallback():
    decision = PolicyEngine().evaluate(
        _request(), "RIF_Test", _open_profile(), Posture.locked, []
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "posture.locked"
