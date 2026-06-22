from rif_runtime.model_router import ModelRouter
from rif_runtime.schemas import IntentClassification, RiskLevel


def classification(**overrides):
    payload = {
        "intent": "summarise",
        "risk_level": RiskLevel.low,
        "domain": "documentation",
        "requires_deep_reasoner": False,
        "rationale": "simple request",
    }
    payload.update(overrides)
    return IntentClassification(**payload)


def test_route_keeps_policy_engine_as_authority():
    route = ModelRouter.route(classification())

    assert route.stages == [
        "mythos-nano:classify",
        "rif-policy-engine",
        "mythos-nano:audit-summary",
    ]
    assert route.uses_deep_reasoner is False


def test_security_analysis_routes_to_deephat_after_policy():
    route = ModelRouter.route(
        classification(
            intent="security_review",
            risk_level=RiskLevel.medium,
            domain="security",
            requires_deep_reasoner=True,
        )
    )

    assert route.stages.index("rif-policy-engine") < route.stages.index("deephat-7b:reason")
    assert route.uses_deep_reasoner is True


def test_route_without_classifier_does_not_assume_model_authority():
    route = ModelRouter.route(None)

    assert route.stages == ["rif-policy-engine", "mythos-nano:audit-summary"]
