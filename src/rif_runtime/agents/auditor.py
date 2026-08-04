"""Enterprise auditor agent with chain integrity verification."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from rif_runtime.audit import AuditRecord, append_record, verify_chain
from rif_runtime.schemas import PolicyDecision

from ._circuit_breaker import CircuitBreaker
from ._policy_gate import PolicyGate
from .template import BaseAgent

if TYPE_CHECKING:
    from rif_runtime.runtime import RIFRuntime

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditFinding:
    """A single finding from an audit pass."""
    severity: str
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Complete audit report from a full audit pass."""
    agent: str
    chain_valid: bool
    total_records: int
    findings: list[AuditFinding]
    decision_summary: dict[str, int]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditorAgent(BaseAgent):
    """Enterprise auditor with chain verification and anomaly detection."""

    def __init__(self, *, audit_chain: list[AuditRecord] | None = None, policy_gate: PolicyGate | None = None, denial_threshold: int = 10) -> None:
        super().__init__(name="agent:auditor", description="Verifies audit chain integrity and detects policy anomalies", policy_gate=policy_gate, audit_chain=audit_chain)
        self._denial_threshold = denial_threshold

    def audit(self, runtime: RIFRuntime) -> dict[str, Any]:
        summary = runtime.audit_summary()
        chain_valid = self.verify_chain_integrity()
        return {"agent": self.name, "chain_valid": chain_valid, **summary}

    def full_audit(self) -> AuditReport:
        findings: list[AuditFinding] = []
        chain_valid = self.verify_chain_integrity()
        if not chain_valid:
            findings.append(AuditFinding(severity="critical", category="integrity", message="Audit chain hash verification failed", details={"chain_length": len(self._audit_chain)}))

        decision_counts = self._count_decisions()
        deny_count = decision_counts.get("deny", 0)
        if deny_count >= self._denial_threshold:
            findings.append(AuditFinding(severity="warning", category="anomaly", message=f"High denial count detected: {deny_count} denials", details={"deny_count": deny_count, "threshold": self._denial_threshold}))

        missing_fields_count = self._count_incomplete_records()
        if missing_fields_count > 0:
            findings.append(AuditFinding(severity="info", category="completeness", message=f"{missing_fields_count} records missing recommended fields", details={"count": missing_fields_count}))

        return AuditReport(agent=self.name, chain_valid=chain_valid, total_records=len(self._audit_chain), findings=findings, decision_summary=dict(decision_counts))

    def verify_chain_integrity(self) -> bool:
        if not self._audit_chain:
            return True
        return verify_chain(self._audit_chain)

    def _count_decisions(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for record in self._audit_chain:
            decision = record.payload.get("decision")
            if decision is not None:
                counter[str(decision)] += 1
        return dict(counter)

    def _count_incomplete_records(self) -> int:
        required_fields = {"type", "actor", "action"}
        count = 0
        for record in self._audit_chain:
            if not required_fields.issubset(record.payload.keys()):
                count += 1
        return count
