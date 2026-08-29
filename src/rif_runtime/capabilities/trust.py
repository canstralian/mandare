from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from .models import (
    BehaviorEvidence,
    CapabilityRecord,
    TrustAssessment,
    TrustStatus,
)


class TrustDecision(StrEnum):
    allow = "allow"
    deny = "deny"
    quarantine = "quarantine"


class CapabilityTrustEngine:
    """Evaluate declared authority against observed behaviour.

    Trust is evidence-driven: the declaration establishes the authority ceiling,
    while observed violations reduce that authority. Discovery therefore remains
    separate from execution authority.
    """

    def assess(
        self,
        record: CapabilityRecord,
        evidence: list[BehaviorEvidence] | None = None,
    ) -> TrustAssessment:
        observations = evidence if evidence is not None else record.behavior_evidence
        score = 1.0
        reasons: list[str] = []

        if not record.integrity.verified:
            score -= 0.5
            reasons.append("integrity is not verified")
        if record.identity is None:
            score -= 0.15
            reasons.append("agent identity is not established")
        if record.declaration is None:
            score -= 0.25
            reasons.append("capability declaration is absent")

        breached = False
        for item in observations:
            if not item.within_declaration:
                score -= 0.2
                breached = True
                reasons.append(f"undeclared behaviour: {item.action}")
            if item.policy_violation:
                score -= 0.35
                breached = True
                reasons.append(f"policy violation: {item.action}")
            if item.outcome == "failure":
                score -= 0.05

        score = max(0.0, min(1.0, score))
        # The declaration is the authority ceiling, so behaviour that steps
        # outside it costs the trusted status outright rather than only
        # shaving the score. Otherwise a first undeclared action would be
        # recorded as a reason while still authorising execution, and the
        # reasons would contradict the status they are attached to.
        if score < 0.4:
            status = TrustStatus.quarantined
        elif score < 0.75 or breached:
            status = TrustStatus.degraded
        else:
            status = TrustStatus.trusted

        assessment = TrustAssessment(
            score=score,
            status=status,
            reasons=reasons,
            assessed_at=datetime.now(UTC),
        )
        record.trust = assessment
        return assessment

    def authorize(
        self,
        record: CapabilityRecord,
        *,
        action: str,
        target: str | None = None,
    ) -> TrustDecision:
        declaration = record.declaration
        if declaration is None:
            return TrustDecision.deny
        if record.trust.status is TrustStatus.quarantined:
            return TrustDecision.quarantine
        if record.trust.status is not TrustStatus.trusted:
            return TrustDecision.deny
        if action not in declaration.actions:
            return TrustDecision.deny
        if declaration.targets and target is not None:
            if target not in declaration.targets:
                return TrustDecision.deny
        return TrustDecision.allow
