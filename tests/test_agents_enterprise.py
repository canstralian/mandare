"""Comprehensive test suite for the enterprise agents module."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

import pytest

from rif_runtime.audit import AuditRecord, append_record, verify_chain
from rif_runtime.schemas import Decision, EnvironmentProfile, PolicyDecision, PolicyRequest, Posture
from rif_runtime.agents import (
    ActionResult, AuditFinding, AuditReport, AuditorAgent, BaseAgent,
    CircuitBreaker, CircuitBreakerConfig, CircuitOpen, CircuitState,
    DeputyAgent, EscalationLevel, GateResult, OrchestratorAgent,
    PolicyGate, PolicyGateError, ReviewFinding,
)


def _make_allow_decision(action: str = "http.request", target: str = "example.com") -> PolicyDecision:
    return PolicyDecision(decision=Decision.allow, action=action, target=target, matched_rule="default-allow", reason="Allowed by default policy")


def _make_deny_decision(action: str = "http.request", target: str = "blocked.com") -> PolicyDecision:
    return PolicyDecision(decision=Decision.deny, action=action, target=target, matched_rule="block-list", reason="Target is on block list")


class FakeEvaluator:
    def __init__(self, decision: PolicyDecision) -> None:
        self._decision = decision

    def evaluate(self, req: PolicyRequest, env_name: str, profile: EnvironmentProfile, posture: Posture, policy_rules: Sequence[Any] = ()) -> PolicyDecision:
        return self._decision


def _make_gate(decision: PolicyDecision, raise_on_deny: bool = False) -> tuple[PolicyGate, list[AuditRecord]]:
    chain: list[AuditRecord] = []
    evaluator = FakeEvaluator(decision)
    gate = PolicyGate(evaluator=evaluator, env_name="test", profile=EnvironmentProfile(name="test", trust_level="high"), posture=Posture.permissive, audit_chain=chain, raise_on_deny=raise_on_deny)
    return gate, chain


class TestCircuitBreaker:
    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.closed
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout_s=1.0)
        cb = CircuitBreaker("test", config=config)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.open
        assert cb.allow_request() is False

    def test_transitions_to_half_open_after_recovery(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_s=0.05)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.open
        time.sleep(0.06)
        assert cb.allow_request() is True
        assert cb.state == CircuitState.half_open

    def test_closes_on_success_in_half_open(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_s=0.01)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        time.sleep(0.02)
        cb.allow_request()
        cb.record_success()
        assert cb.state == CircuitState.closed

    def test_reopens_on_failure_in_half_open(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_s=0.01)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        time.sleep(0.02)
        cb.allow_request()
        cb.record_failure()
        assert cb.state == CircuitState.open

    def test_reset_returns_to_closed(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        assert cb.state == CircuitState.open
        cb.reset()
        assert cb.state == CircuitState.closed
        assert cb.stats.total_calls == 0

    def test_stats_snapshot(self) -> None:
        cb = CircuitBreaker("test")
        cb.record_success()
        cb.record_failure()
        stats = cb.stats
        assert stats.total_calls == 2
        assert stats.total_successes == 1
        assert stats.total_failures == 1

    def test_time_until_recovery(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_s=10.0)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        remaining = cb.time_until_recovery()
        assert 9.0 < remaining <= 10.0


class TestPolicyGate:
    def test_allows_when_decision_is_allow(self) -> None:
        gate, chain = _make_gate(_make_allow_decision())
        req = PolicyRequest(actor="agent:test", action="http.request", target="example.com")
        result = gate.check(req)
        assert result.allowed is True
        assert result.audit_record is not None
        assert len(chain) == 1

    def test_denies_when_decision_is_deny(self) -> None:
        gate, chain = _make_gate(_make_deny_decision())
        req = PolicyRequest(actor="agent:test", action="http.request", target="blocked.com")
        result = gate.check(req)
        assert result.allowed is False

    def test_raises_on_deny_when_configured(self) -> None:
        gate, _ = _make_gate(_make_deny_decision(), raise_on_deny=True)
        req = PolicyRequest(actor="agent:test", action="http.request", target="blocked.com")
        with pytest.raises(PolicyGateError) as exc_info:
            gate.check(req)
        assert "block-list" in str(exc_info.value)

    def test_audit_chain_integrity(self) -> None:
        gate, chain = _make_gate(_make_allow_decision())
        req = PolicyRequest(actor="agent:test", action="http.request", target="example.com")
        gate.check(req)
        gate.check(req)
        assert len(chain) == 2
        assert verify_chain(chain) is True


class TestBaseAgent:
    def test_validate_correct_name(self) -> None:
        agent = BaseAgent(name="agent:worker")
        assert agent.validate() is True

    def test_validate_incorrect_name(self) -> None:
        agent = BaseAgent(name="not-an-agent")
        assert agent.validate() is False

    def test_validate_empty_role(self) -> None:
        agent = BaseAgent(name="agent:")
        assert agent.validate() is False

    def test_dispatch_success(self) -> None:
        agent = BaseAgent(name="agent:test")
        result = agent.dispatch("test.action", "target")
        assert result.success is True
        assert result.agent == "agent:test"

    def test_dispatch_with_policy_gate_allow(self) -> None:
        gate, _ = _make_gate(_make_allow_decision())
        agent = BaseAgent(name="agent:test", policy_gate=gate)
        result = agent.dispatch("http.request", "example.com")
        assert result.success is True
        assert result.gate_result is not None
        assert result.gate_result.allowed is True

    def test_dispatch_with_policy_gate_deny(self) -> None:
        gate, _ = _make_gate(_make_deny_decision())
        agent = BaseAgent(name="agent:test", policy_gate=gate)
        result = agent.dispatch("http.request", "blocked.com")
        assert result.success is False
        assert "denied" in (result.error or "").lower()

    def test_dispatch_circuit_breaker_open(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        agent = BaseAgent(name="agent:test", circuit_breaker=cb)
        result = agent.dispatch("test.action", "target")
        assert result.success is False
        assert "circuit" in (result.error or "").lower()

    def test_to_dict(self) -> None:
        agent = BaseAgent(name="agent:test", description="A test agent")
        d = agent.to_dict()
        assert d["name"] == "agent:test"
        assert d["valid"] is True
        assert d["circuit_state"] == "closed"


class TestOrchestratorAgent:
    def test_creates_per_target_breakers(self) -> None:
        orch = OrchestratorAgent()
        orch.dispatch_http("api-a.com")
        orch.dispatch_http("api-b.com")
        stats = orch.target_breaker_stats()
        assert "api-a.com" in stats
        assert "api-b.com" in stats

    def test_target_isolation(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_s=60)
        orch = OrchestratorAgent(circuit_breaker_config=config)
        target_cb = orch.get_target_breaker("failing.com")
        target_cb.record_failure()
        result = orch.dispatch_http("healthy.com")
        assert result.success is True

    def test_open_target_rejects(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_s=60)
        orch = OrchestratorAgent(circuit_breaker_config=config)
        target_cb = orch.get_target_breaker("failing.com")
        target_cb.record_failure()
        result = orch.dispatch_http("failing.com")
        assert result.success is False
        assert "circuit" in (result.error or "").lower()

    def test_reset_target_breaker(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=1)
        orch = OrchestratorAgent(circuit_breaker_config=config)
        target_cb = orch.get_target_breaker("target.com")
        target_cb.record_failure()
        assert target_cb.state == CircuitState.open
        assert orch.reset_target_breaker("target.com") is True
        assert target_cb.state == CircuitState.closed

    def test_to_dict_includes_targets(self) -> None:
        orch = OrchestratorAgent()
        orch.dispatch_http("example.com")
        d = orch.to_dict()
        assert "target_breakers" in d
        assert "example.com" in d["target_breakers"]


class TestAuditorAgent:
    def test_verify_empty_chain(self) -> None:
        auditor = AuditorAgent()
        assert auditor.verify_chain_integrity() is True

    def test_verify_valid_chain(self) -> None:
        chain: list[AuditRecord] = []
        append_record(chain, {"type": "test", "actor": "agent:a", "action": "x"})
        append_record(chain, {"type": "test", "actor": "agent:b", "action": "y"})
        auditor = AuditorAgent(audit_chain=chain)
        assert auditor.verify_chain_integrity() is True

    def test_full_audit_clean_chain(self) -> None:
        chain: list[AuditRecord] = []
        append_record(chain, {"type": "test", "actor": "agent:a", "action": "x"})
        auditor = AuditorAgent(audit_chain=chain)
        report = auditor.full_audit()
        assert report.chain_valid is True
        assert report.total_records == 1
        assert len(report.findings) == 0

    def test_full_audit_detects_high_denials(self) -> None:
        chain: list[AuditRecord] = []
        for _ in range(15):
            append_record(chain, {"type": "policy_gate.check", "decision": "deny", "actor": "a", "action": "x"})
        auditor = AuditorAgent(audit_chain=chain, denial_threshold=10)
        report = auditor.full_audit()
        assert any(f.category == "anomaly" for f in report.findings)

    def test_full_audit_detects_incomplete_records(self) -> None:
        chain: list[AuditRecord] = []
        append_record(chain, {"partial": "data"})
        auditor = AuditorAgent(audit_chain=chain)
        report = auditor.full_audit()
        assert any(f.category == "completeness" for f in report.findings)


class TestDeputyAgent:
    def test_review_allow_decision(self) -> None:
        deputy = DeputyAgent()
        decision = _make_allow_decision()
        finding = deputy.review_decision(decision)
        assert finding.severity == EscalationLevel.auto

    def test_review_deny_decision_escalates(self) -> None:
        deputy = DeputyAgent()
        decision = _make_deny_decision(action="http.request")
        finding = deputy.review_decision(decision)
        assert finding.severity >= EscalationLevel.team

    def test_escalation_threshold(self) -> None:
        deputy = DeputyAgent(escalation_threshold=2)
        deny = _make_deny_decision(action="http.request")
        deputy.review_decision(deny)
        assert deputy.escalation_level == EscalationLevel.team
        deputy.review_decision(deny)
        assert deputy.escalation_level == EscalationLevel.management

    def test_escalation_report(self) -> None:
        deputy = DeputyAgent()
        deputy.review_decision(_make_allow_decision())
        deputy.review_decision(_make_deny_decision())
        report = deputy.escalation_report()
        assert report["total_findings"] == 2
        assert "severity_counts" in report

    def test_reset_findings(self) -> None:
        deputy = DeputyAgent()
        deputy.review_decision(_make_deny_decision())
        assert len(deputy.findings) == 1
        deputy.reset_findings()
        assert len(deputy.findings) == 0
        assert deputy.escalation_level == EscalationLevel.auto

    def test_handle_decision(self) -> None:
        deputy = DeputyAgent()
        decision = _make_deny_decision()
        result = deputy.handle_decision(decision)
        assert result["agent"] == "agent:deputy"
        assert result["decision"] == "deny"
        assert "recommendation" in result

    def test_review_batch(self) -> None:
        deputy = DeputyAgent()
        decisions = [_make_allow_decision(), _make_deny_decision()]
        findings = deputy.review_batch(decisions)
        assert len(findings) == 2
