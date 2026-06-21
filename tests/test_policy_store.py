import pytest
from pydantic import ValidationError

from rif_runtime.configuration.policies import PolicyRule, PolicyStore
from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import EnvironmentProfile, PolicyRequest, Posture


def test_policy_store_upsert_and_delete(tmp_path):
    store = PolicyStore(str(tmp_path / "policies.json"))

    rule = PolicyRule(
        id="test_rule",
        effect="deny",
        action="http.request",
        target="example.com",
    )

    store.upsert(rule)
    assert any(r.id == "test_rule" for r in store.list())

    assert store.delete("test_rule") is True
    assert not any(r.id == "test_rule" for r in store.list())


def test_custom_policy_rule_overrides_engine_default():
    profile = EnvironmentProfile(networking_type="open", allowed_hosts=[])
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com"
    )

    rule = PolicyRule(
        id="block_example", effect="deny", action="http.request", target="example.com"
    )
    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", profile, Posture.normal, [rule]
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "policy.block_example"


def test_custom_allow_rule_overrides_network_denial():
    profile = EnvironmentProfile(networking_type="limited", allowed_hosts=[])
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://api.anthropic.com"
    )

    rule = PolicyRule(
        id="allow_known_model_hosts",
        effect="allow",
        action="http.request",
        target="api.anthropic.com",
    )
    decision = PolicyEngine().evaluate(req, "RIF_CI", profile, Posture.normal, [rule])

    assert decision.decision == "allow"
    assert decision.matched_rule == "policy.allow_known_model_hosts"


def test_custom_rule_matches_full_url_target():
    profile = EnvironmentProfile(networking_type="open", allowed_hosts=[])
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com/path"
    )

    rule = PolicyRule(
        id="block_example",
        effect="deny",
        action="http.request",
        target="https://example.com",
    )
    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", profile, Posture.normal, [rule]
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "policy.block_example"


def test_policy_rule_rejects_invalid_effect():
    with pytest.raises(ValidationError):
        PolicyRule(
            id="bad_rule", effect="alloww", action="http.request", target="example.com"
        )
