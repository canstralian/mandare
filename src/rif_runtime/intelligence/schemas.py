from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from rif_runtime.schemas import Decision, Posture

_COMMAND_OR_TOOL_PATTERN = re.compile(
    r"(?im)(?:```|^\s*(?:\$|#\s*!|curl\b|wget\b|nmap\b|masscan\b|"
    r"sqlmap\b|msfconsole\b|nc\b|netcat\b|bash\b|sh\b|powershell\b|"
    r"cmd(?:\.exe)?\b|python(?:3)?\s+-c\b)|\b(?:tool_call|mcp\.invoke)\b)"
)


def _reject_executable_text(value: str) -> str:
    if _COMMAND_OR_TOOL_PATTERN.search(value):
        raise ValueError(
            "RIF intelligence is planning-only; executable or tool-like text is not permitted"
        )
    return value


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

    @field_validator("title", "summary")
    @classmethod
    def no_executable_text(cls, value: str) -> str:
        return _reject_executable_text(value)

    @field_validator("recommended_steps", "constraints")
    @classmethod
    def no_executable_collections(cls, values: list[str]) -> list[str]:
        return [_reject_executable_text(value) for value in values]

    @model_validator(mode="after")
    def no_execution_commands(self) -> "GuardedSecurityDraft":
        if self.execution_commands:
            raise ValueError(
                "execution_commands must be empty; RIF intelligence is planning-only"
            )
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
    decision_verified: bool = False
    source: Literal["llm_assisted", "deterministic_fallback"]
    model_used: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    redaction_policy_version: str
    input_hash: str
    output_hash: str
    interpretation: str
    warnings: list[str] = Field(default_factory=list)
    draft: GuardedSecurityDraft | None = None

    @field_validator("interpretation")
    @classmethod
    def no_executable_interpretation(cls, value: str) -> str:
        return _reject_executable_text(value)

    @field_validator("warnings")
    @classmethod
    def no_executable_warnings(cls, values: list[str]) -> list[str]:
        return [_reject_executable_text(value) for value in values]
