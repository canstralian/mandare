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
