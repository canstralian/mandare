from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from rif_runtime.schemas import PolicyDecision, PolicyRequest, Posture


class DecisionExplanation(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    request: PolicyRequest
    decision: PolicyDecision
    precedence: tuple[str, ...]
    posture_before: Posture
    posture_after: Posture
    environment_snapshot: dict[str, Any]
    replay_consistent: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_decision(
        cls,
        request: PolicyRequest,
        decision: PolicyDecision,
        posture_before: Posture,
        posture_after: Posture,
        environment_snapshot: dict[str, Any],
        precedence: tuple[str, ...] = ("posture", "policy", "mcp", "package", "network", "default"),
    ) -> "DecisionExplanation":
        return cls(
            request=request,
            decision=decision,
            precedence=precedence,
            posture_before=posture_before,
            posture_after=posture_after,
            environment_snapshot=environment_snapshot,
        )
