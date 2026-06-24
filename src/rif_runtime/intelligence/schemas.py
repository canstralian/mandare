from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from rif_runtime.schemas import Decision, Posture


class IntelligenceMode(str, Enum):
    policy_explanation = "policy_explanation"
    governance_artifact_synthesis = "governance_artifact_synthesis"
    evidence_summary = "evidence_summary"
    drift_analysis = "drift_analysis"
    operator_brief = "operator_brief"
    recon_plan = "recon_plan"
    finding_triage = "finding_triage"
    remediation_draft = "remediation_draft"
    detection_rule_draft = "detection_rule_draft"
    alert_enrichment = "alert_enrichment"
    report_draft = "report_draft"


class EvidenceItem(BaseModel):
    id: str
    kind: str = "observation"
    content: str
    source: str | None = None
    timestamp: datetime | None = None


class DeterministicDecisionSnapshot(BaseModel):
    decision: Decision
    posture: Posture
    confirmation_required: bool = False
    rule_id: str
    reason: str
    actor: str
    action: str
    target: str
    environment: str


class GuardedSecurityDraft(BaseModel):
    title: str
    summary: str
    recommended_steps: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    execution_commands: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def no_execution_commands(self) -> "GuardedSecurityDraft":
        if self.execution_commands:
            raise ValueError("execution_commands must be empty; RIF intelligence is planning-only")
        return self


class IntelligenceRequest(BaseModel):
    mode: IntelligenceMode
    decision: DeterministicDecisionSnapshot
    evidence: list[EvidenceItem] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    operator_question: str | None = None


class IntelligenceResponse(BaseModel):
    mode: IntelligenceMode
    decision: DeterministicDecisionSnapshot
    source: Literal["llm_assisted", "deterministic_fallback"]
    model_used: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_hash: str
    output_hash: str
    interpretation: str
    warnings: list[str] = Field(default_factory=list)
    draft: GuardedSecurityDraft | None = None
