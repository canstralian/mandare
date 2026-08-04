"""Enterprise deputy agent for decision review and escalation."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

from rif_runtime.audit import AuditRecord, append_record
from rif_runtime.schemas import Decision, PolicyDecision, PolicyRequest

from ._circuit_breaker import CircuitBreaker
from ._policy_gate import PolicyGate
from .template import BaseAgent

logger = logging.getLogger(__name__)


class EscalationLevel(IntEnum):
    auto = 0
    team = 1
    management = 2
    emergency = 3


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    severity: EscalationLevel
    decision: PolicyDecision
    recommendation: str
    rationale: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class DeputyAgent(BaseAgent):
    """Reviews decisions and manages escalation workflows."""

    def __init__(self, *, audit_chain: list[AuditRecord] | None = None, policy_gate: PolicyGate | None = None, escalation_threshold: int = 3) -> None:
        super().__init__(name="agent:deputy", description="Reviews policy decisions and manages escalation workflows", policy_gate=policy_gate, audit_chain=audit_chain)
        self._escalation_threshold = escalation_threshold
        self._findings: list[ReviewFinding] = []
        self._escalation_level = EscalationLevel.auto

    def review_decision(self, decision: PolicyDecision) -> ReviewFinding:
        severity = self._classify_severity(decision)
        recommendation = self._generate_recommendation(decision, severity)
        rationale = self._generate_rationale(decision, severity)
        finding = ReviewFinding(severity=severity, decision=decision, recommendation=recommendation, rationale=rationale)
        self._findings.append(finding)
        self._record_review(finding)
        self._check_escalation()
        return finding

    def review_batch(self, decisions: Sequence[PolicyDecision]) -> list[ReviewFinding]:
        return [self.review_decision(d) for d in decisions]

    def escalation_report(self) -> dict[str, Any]:
        severity_counts = {level.name: sum(1 for f in self._findings if f.severity == level) for level in EscalationLevel}
        return {
            "agent": self.name,
            "total_findings": len(self._findings),
            "severity_counts": severity_counts,
            "current_escalation_level": self._escalation_level.name,
            "escalation_threshold": self._escalation_threshold,
            "requires_attention": self._escalation_level >= EscalationLevel.team,
            "recommendations": self._top_recommendations(),
        }

    @property
    def findings(self) -> Sequence[ReviewFinding]:
        return self._findings

    @property
    def escalation_level(self) -> EscalationLevel:
        return self._escalation_level

    def reset_findings(self) -> None:
        self._findings = []
        self._escalation_level = EscalationLevel.auto

    def execute(self, request: PolicyRequest) -> dict[str, Any]:
        return {"agent": self.name, "action": request.action, "target": request.target, "status": "reviewed", "escalation_level": self._escalation_level.name}

    def handle_decision(self, decision: PolicyDecision) -> dict[str, str]:
        finding = self.review_decision(decision)
        return {"agent": self.name, "decision": decision.decision.value, "severity": finding.severity.name, "recommendation": finding.recommendation}

    def _classify_severity(self, decision: PolicyDecision) -> EscalationLevel:
        if decision.decision == Decision.deny:
            if decision.action in ("http.request", "api.call", "mcp.invoke"):
                return EscalationLevel.team
            return EscalationLevel.auto
        if decision.decision == Decision.allow:
            return EscalationLevel.auto
        return EscalationLevel.team

    def _generate_recommendation(self, decision: PolicyDecision, severity: EscalationLevel) -> str:
        if severity >= EscalationLevel.management:
            return "Immediate review required; suspend related operations"
        if severity >= EscalationLevel.team:
            return "Team review recommended; monitor for pattern"
        if decision.decision == Decision.deny:
            return "Denial logged; verify policy rule correctness"
        return "No action required"

    def _generate_rationale(self, decision: PolicyDecision, severity: EscalationLevel) -> str:
        parts: list[str] = []
        parts.append(f"Decision: {decision.decision.value}")
        parts.append(f"Action: {decision.action}")
        parts.append(f"Rule: {decision.matched_rule}")
        if decision.reason:
            parts.append(f"Reason: {decision.reason}")
        parts.append(f"Severity classification: {severity.name}")
        return "; ".join(parts)

    def _record_review(self, finding: ReviewFinding) -> None:
        payload: dict[str, Any] = {
            "type": "deputy.review",
            "agent": self.name,
            "severity": finding.severity.name,
            "recommendation": finding.recommendation,
            "decision_action": finding.decision.action,
            "decision_target": finding.decision.target,
            "decision_outcome": finding.decision.decision.value,
        }
        append_record(self._audit_chain, payload)

    def _check_escalation(self) -> None:
        high_severity_count = sum(1 for f in self._findings if f.severity >= EscalationLevel.team)
        if high_severity_count >= self._escalation_threshold:
            new_level = EscalationLevel.management
        elif high_severity_count > 0:
            new_level = EscalationLevel.team
        else:
            new_level = EscalationLevel.auto
        if new_level > self._escalation_level:
            logger.warning("Escalation level raised: %s -> %s (findings=%d)", self._escalation_level.name, new_level.name, high_severity_count)
            self._escalation_level = new_level

    def _top_recommendations(self) -> list[str]:
        seen: set[str] = set()
        recs: list[str] = []
        for f in reversed(self._findings):
            if f.severity >= EscalationLevel.team and f.recommendation not in seen:
                seen.add(f.recommendation)
                recs.append(f.recommendation)
            if len(recs) >= 5:
                break
        return recs
