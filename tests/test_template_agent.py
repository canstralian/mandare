from rif_runtime.agents.template import TemplateAgent
from rif_runtime.configuration.policies import PolicyRule
from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import Decision, EnvironmentProfile, Posture


def make_agent():
    return TemplateAgent("agent:template", "example governed agent")


def test_validate_requires_agent_prefix():
    assert make_agent().validate()
    assert not TemplateAgent("").validate()
    assert not TemplateAgent("agent:").validate()
    assert not TemplateAgent("orchestrator").validate()


def test_request_builds_policy_request():
    req = make_agent().request(
        "http.request",
        "https://api.example.com/v1",
        reason="fetch upstream state",
        context={"env": "production"},
    )
    assert req.actor == "agent:template"
    assert req.action == "http.request"
    assert req.target == "https://api.example.com/v1"
    assert req.reason == "fetch upstream state"
    assert req.context == {"env": "production"}
    assert make_agent().request("http.request", "https://api.example.com").context == {}


def test_round_trip_through_policy_engine():
    agent = make_agent()
    engine = PolicyEngine()
    profile = EnvironmentProfile(allowed_hosts=["api.example.com"])
    # The engine fails closed, so the allow arm needs a rule that actually
    # authorizes the request. Passing the host allowlist only means no
    # constraint denied it, which is not an authorization.
    rules = [
        PolicyRule(
            id="allow_example_api",
            effect="allow",
            action="http.request",
            target="api.example.com",
        )
    ]
    allowed = engine.evaluate(
        agent.request("http.request", "https://api.example.com/v1"),
        "RIF_Test",
        profile,
        Posture.normal,
        rules,
    )
    denied = engine.evaluate(
        agent.request("http.request", "https://untrusted.example.net"),
        "RIF_Test",
        profile,
        Posture.normal,
        rules,
    )
    assert allowed.decision == Decision.allow
    assert denied.decision == Decision.deny
    assert agent.handle_decision(denied) == {
        "agent": "agent:template",
        "decision": "deny",
        "rule": "network.host.denied",
    }


def test_to_dict_and_repr():
    agent = make_agent()
    assert agent.to_dict() == {
        "name": "agent:template",
        "description": "example governed agent",
    }
    assert repr(agent) == (
        "TemplateAgent(name='agent:template', description='example governed agent')"
    )
