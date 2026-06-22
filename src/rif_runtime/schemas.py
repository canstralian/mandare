from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Decision(str, Enum):
    allow = "allow"
    deny = "deny"
    review = "review"


class Posture(str, Enum):
    normal = "normal"
    elevated = "elevated"
    restricted = "restricted"
    locked = "locked"


class PolicyRequest(BaseModel):
    actor: str
    action: str
    target: str
    reason: str | None = None
    context: dict = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    decision: Decision
    actor: str
    action: str
    target: str
    environment: str
    posture: Posture
    reason: str
    matched_rule: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnvironmentProfile(BaseModel):
    networking_type: str = "limited"
    allow_mcp_server_network_access: bool = False
    allow_package_manager_network_access: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class RuntimeConfig(BaseModel):
    default_environment: str
    environments: dict[str, EnvironmentProfile]


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    blocked = "blocked"


class IntentClassification(BaseModel):
    """Untrusted advisory classification; never a policy decision."""

    intent: str
    risk_level: RiskLevel
    domain: str
    requires_deep_reasoner: bool = False
    suggested_adapter: str | None = None
    rationale: str


class SecurityReasoningResult(BaseModel):
    """Bounded output from an optional specialist model."""

    decision: str
    findings: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class ModelRoute(BaseModel):
    stages: list[str]
    uses_deep_reasoner: bool


class GovernanceArtifact(BaseModel):
    request_id: str
    input_hash: str
    intent: IntentClassification | None = None
    policy_decision: PolicyDecision
    model_route: ModelRoute
    deep_reasoning: SecurityReasoningResult | None = None
    final_summary: str | None = None
    replay_metadata: dict = Field(default_factory=dict)
