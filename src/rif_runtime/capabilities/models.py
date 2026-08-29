from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CapabilityStatus(StrEnum):
    discovered = "discovered"
    identified = "identified"
    inspected = "inspected"
    scanned = "scanned"
    evaluated = "evaluated"
    admitted = "admitted"
    available = "available"
    revoked = "revoked"


class TrustStatus(StrEnum):
    trusted = "trusted"
    degraded = "degraded"
    quarantined = "quarantined"


class AgentIdentity(BaseModel):
    """Stable identity and issuer information for an agent or operator."""

    id: str
    issuer: str
    subject: str
    version: str | None = None
    declared_capabilities: list[str] = Field(default_factory=list)


class CapabilityDeclaration(BaseModel):
    """The authority a capability claims it is intended to exercise."""

    purpose: str
    actions: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    data_access: list[str] = Field(default_factory=list)
    egress: list[str] = Field(default_factory=list)
    risk: str = "unknown"


class BehaviorEvidence(BaseModel):
    """A normalized observation that can raise or lower execution trust."""

    action: str
    outcome: str = "success"
    within_declaration: bool = True
    policy_violation: bool = False
    evidence_ref: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrustAssessment(BaseModel):
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    status: TrustStatus = TrustStatus.trusted
    reasons: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CapabilityLifecycle(BaseModel):
    status: CapabilityStatus = CapabilityStatus.discovered
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: str | None = None


class CapabilityProvenance(BaseModel):
    source: str
    publisher: str | None = None
    version: str | None = None
    commit: str | None = None
    retrieved_at: datetime | None = None


class CapabilityIntegrity(BaseModel):
    digest: str | None = None
    signature: str | None = None
    verified: bool = False


class CapabilityEvaluation(BaseModel):
    evaluator: str
    suite: str
    passed: bool
    score: float | None = None
    evidence_ref: str | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CapabilityRecord(BaseModel):
    id: str
    name: str
    description: str | None = None
    provenance: CapabilityProvenance
    integrity: CapabilityIntegrity = Field(default_factory=CapabilityIntegrity)
    permissions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    lifecycle: CapabilityLifecycle = Field(default_factory=CapabilityLifecycle)
    evaluations: list[CapabilityEvaluation] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    identity: AgentIdentity | None = None
    declaration: CapabilityDeclaration | None = None
    behavior_evidence: list[BehaviorEvidence] = Field(default_factory=list)
    trust: TrustAssessment = Field(default_factory=TrustAssessment)
