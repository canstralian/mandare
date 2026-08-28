from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Decision(StrEnum):
    allow = "allow"
    deny = "deny"
    review = "review"


class Posture(StrEnum):
    normal = "normal"
    elevated = "elevated"
    restricted = "restricted"
    locked = "locked"


class PolicyRequest(BaseModel):
    actor: str
    action: str
    target: str
    reason: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    decision: Decision
    actor: str
    action: str
    target: str
    environment: str
    posture: Posture
    reason: str
    matched_rule: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EnvironmentProfile(BaseModel):
    networking_type: str = "limited"
    allow_mcp_server_network_access: bool = False
    allow_package_manager_network_access: bool = False
    allowed_hosts: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class RuntimeConfig(BaseModel):
    default_environment: str
    environments: dict[str, EnvironmentProfile]
