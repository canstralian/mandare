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


# --- wildcard rule precedence ------------------------------------------------
#
# Regression cover for the wildcard rules that PolicyEngine.evaluate() used to
# skip outright: the shipped `deny_unknown_by_default` rule was loaded, listed
# by GET /v1/policies, and never applied.


def _open_profile() -> EnvironmentProfile:
    return EnvironmentProfile(networking_type="open", allowed_hosts=[])


def _shipped_rules() -> list[PolicyRule]:
    from rif_runtime.configuration.policies import DEFAULT_POLICIES

    return [PolicyRule.model_validate(row) for row in DEFAULT_POLICIES["rules"]]


def test_shipped_catch_all_denies_unknown_target():
    """The default policy file's deny_unknown_by_default rule actually applies."""
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://unknown.example.net"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.normal, _shipped_rules()
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "policy.deny_unknown_by_default"


def test_shipped_specific_allow_survives_the_catch_all():
    """A concrete allow still wins even though a catch-all deny is configured."""
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://api.anthropic.com"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.normal, _shipped_rules()
    )

    assert decision.decision == "allow"
    assert decision.matched_rule == "policy.allow_known_model_hosts"


def test_action_wildcard_rule_matches_any_action_on_target():
    rule = PolicyRule(
        id="block_host_entirely", effect="deny", action="*", target="example.com"
    )
    req = PolicyRequest(
        actor="agent:test", action="api.call", target="https://example.com/v1"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.normal, [rule]
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "policy.block_host_entirely"


def test_target_wildcard_rule_matches_any_target_for_action():
    rule = PolicyRule(
        id="no_package_installs", effect="deny", action="package.install", target="*"
    )
    req = PolicyRequest(
        actor="agent:test", action="package.install", target="https://pypi.org/simple"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.normal, [rule]
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "policy.no_package_installs"


def test_more_specific_rule_wins_regardless_of_configured_order():
    """Specificity, not position, decides which of two matching rules applies."""
    broad = PolicyRule(
        id="broad_deny", effect="deny", action="http.request", target="*"
    )
    narrow = PolicyRule(
        id="narrow_allow", effect="allow", action="http.request", target="example.com"
    )
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com"
    )

    for rules in ([broad, narrow], [narrow, broad]):
        decision = PolicyEngine().evaluate(
            req, "RIF_Runtime", _open_profile(), Posture.normal, list(rules)
        )
        assert decision.matched_rule == "policy.narrow_allow", (
            f"specificity ignored for order {[r.id for r in rules]}"
        )
        assert decision.decision == "allow"


def test_equal_specificity_keeps_configured_order():
    first = PolicyRule(
        id="first", effect="deny", action="http.request", target="example.com"
    )
    second = PolicyRule(
        id="second", effect="allow", action="http.request", target="example.com"
    )
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.normal, [first, second]
    )

    assert decision.matched_rule == "policy.first"


def test_catch_all_allow_does_not_disable_the_host_allowlist():
    """A "*"/"*" allow is a fallback, not an override of network constraints.

    Letting the catch-all run before the profile check would turn one broad
    rule into a silent bypass of allowed_hosts.
    """
    rule = PolicyRule(id="allow_everything", effect="allow", action="*", target="*")
    profile = EnvironmentProfile(networking_type="limited", allowed_hosts=[])
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com"
    )

    decision = PolicyEngine().evaluate(req, "RIF_CI", profile, Posture.normal, [rule])

    assert decision.decision == "deny"
    assert decision.matched_rule == "network.host.denied"


def test_locked_posture_still_precedes_every_rule():
    rule = PolicyRule(id="allow_everything", effect="allow", action="*", target="*")
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.locked, [rule]
    )

    assert decision.decision == "deny"
    assert decision.matched_rule == "posture.locked"


def test_no_rules_falls_back_to_default_allow():
    """Removing every rule leaves the built-in fallback intact."""
    req = PolicyRequest(
        actor="agent:test", action="http.request", target="https://example.com"
    )

    decision = PolicyEngine().evaluate(
        req, "RIF_Runtime", _open_profile(), Posture.normal, []
    )

    assert decision.decision == "allow"
    assert decision.matched_rule == "default.allow"
