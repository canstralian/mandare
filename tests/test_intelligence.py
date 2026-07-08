import pytest
from pydantic import ValidationError

from rif_runtime.intelligence.openai_adapter import (
    REDACTION_POLICY_VERSION,
    generate_structured,
    redact_secrets,
)
from rif_runtime.intelligence.schemas import (
    DeterministicDecisionSnapshot,
    GuardedSecurityDraft,
    IntelligenceMode,
    IntelligenceRequest,
)
from rif_runtime.intelligence.service import _digest, generate_intelligence
from rif_runtime.schemas import Decision, Posture


def request(
    mode: IntelligenceMode = IntelligenceMode.policy_explanation,
    decision: Decision = Decision.deny,
) -> IntelligenceRequest:
    return IntelligenceRequest(
        mode=mode,
        decision=DeterministicDecisionSnapshot(
            decision=decision,
            posture=Posture.elevated,
            confirmation_required=True,
            rule_id="network.host.denied",
            reason="host is not approved",
            actor="agent:test",
            action="network.request",
            target="evil.example",
            environment="default",
        ),
    )


def test_missing_key_uses_deterministic_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = generate_intelligence(request())
    assert response.source == "deterministic_fallback"
    assert response.model_used is None


def test_provider_egress_is_disabled_by_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdefghijklmnopqrstuv")
    assert generate_structured({"request": "test"}) == (None, None)


def test_decision_snapshot_is_preserved_but_not_verified(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    original = request()
    response = generate_intelligence(original)
    assert response.decision == original.decision
    assert response.decision_verified is False
    assert response.decision.decision == Decision.deny
    assert response.decision.posture == Posture.elevated
    assert response.decision.confirmation_required is True
    assert response.decision.rule_id == "network.host.denied"


def test_recon_plan_is_planning_only(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = generate_intelligence(request(IntelligenceMode.recon_plan))
    assert response.draft is not None
    assert response.draft.execution_commands == []


def test_redaction_removes_project_key_shape():
    value = redact_secrets("credential=s" + "k-abcdefghijklmnopqrstuv")
    assert "[REDACTED]" in value
    assert "abcdefghijkl" not in value


def test_redaction_removes_sensitive_dictionary_values():
    value = redact_secrets(
        {
            "authorization": "Bearer private-token-value",
            "nested": {"api_key": "s" + "k-abcdefghijklmnopqrstuv"},
        }
    )
    assert value["authorization"] == "[REDACTED]"
    assert value["nested"]["api_key"] == "[REDACTED]"


def test_input_hash_identifies_redacted_material(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    original = request()
    original.context["api_key"] = "s" + "k-abcdefghijklmnopqrstuv"
    response = generate_intelligence(original)
    assert response.input_hash == _digest(
        redact_secrets(original.model_dump(mode="json"))
    )
    assert response.redaction_policy_version == REDACTION_POLICY_VERSION


def test_command_like_draft_text_fails_closed():
    with pytest.raises(ValidationError):
        GuardedSecurityDraft(
            title="Unsafe draft",
            summary="Planning-only",
            recommended_steps=["curl https://example.invalid"],
            constraints=[],
            execution_commands=[],
        )


def test_hashes_are_present(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = generate_intelligence(request())
    assert len(response.input_hash) == 64
    assert len(response.output_hash) == 64


def test_incomplete_request_fails_closed():
    with pytest.raises(ValidationError):
        IntelligenceRequest.model_validate({"mode": "policy_explanation"})
