import pytest

from rif_runtime.capabilities import (
    AgentIdentity,
    BehaviorEvidence,
    CapabilityDeclaration,
    CapabilityEvaluation,
    CapabilityIntegrity,
    CapabilityProvenance,
    CapabilityRecord,
    CapabilityRegistry,
    TrustDecision,
    TrustStatus,
)
from rif_runtime.execution.exceptions import PolicyViolationError


def record() -> CapabilityRecord:
    return CapabilityRecord(
        id="web.fetch",
        name="web.fetch",
        provenance=CapabilityProvenance(source="https://example.invalid/web-fetch"),
        integrity=CapabilityIntegrity(verified=True),
        identity=AgentIdentity(
            id="agent:researcher",
            issuer="mandare:test",
            subject="researcher",
            declared_capabilities=["web.fetch"],
        ),
        declaration=CapabilityDeclaration(
            purpose="retrieve public web resources",
            actions=["fetch"],
            targets=["https://example.com"],
            data_access=["public"],
            egress=["https"],
            risk="low",
        ),
    )


def test_admission_requires_identity_and_declaration() -> None:
    registry = CapabilityRegistry()
    item = record()
    item.evaluations.append(
        CapabilityEvaluation(evaluator="tests", suite="basic", passed=True)
    )
    registry.register_record(item)

    admitted = registry.admit("web.fetch")

    assert admitted.lifecycle.status.value == "admitted"


def test_authorization_is_constrained_by_declaration() -> None:
    registry = CapabilityRegistry()
    registry.register_record(record())

    assert (
        registry.authorize(
            "web.fetch", action="fetch", target="https://example.com"
        )
        is TrustDecision.allow
    )

    with pytest.raises(PolicyViolationError):
        registry.authorize("web.fetch", action="delete", target="https://example.com")


def test_undeclared_behaviour_degrades_and_then_quarantines_trust() -> None:
    registry = CapabilityRegistry()
    registry.register_record(record())

    registry.observe(
        "web.fetch",
        BehaviorEvidence(action="delete", within_declaration=False),
    )
    assert registry.record("web.fetch").trust.status is TrustStatus.degraded

    registry.observe(
        "web.fetch",
        BehaviorEvidence(
            action="delete",
            within_declaration=False,
            policy_violation=True,
        ),
    )
    assert registry.record("web.fetch").trust.status is TrustStatus.quarantined

    with pytest.raises(PolicyViolationError):
        registry.authorize(
            "web.fetch", action="fetch", target="https://example.com"
        )
