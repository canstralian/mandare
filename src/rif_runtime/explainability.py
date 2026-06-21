from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from rif_runtime.schemas import Decision, PolicyDecision, PolicyRequest, Posture


class DecisionExplanation(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    actor: str
    action: str
    target: str
    decision: Decision
    matched_rule: str
    precedence: tuple[str, ...]
    posture_before: Posture
    posture_after: Posture
    environment: str
    environment_snapshot: dict[str, Any]
    reason: str
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
        precedence: tuple[str, ...] = ("posture", "mcp", "package", "network", "default"),
    ) -> "DecisionExplanation":
        return cls(
            actor=request.actor,
            action=request.action,
            target=request.target,
            decision=decision.decision,
            matched_rule=decision.matched_rule,
            precedence=precedence,
            posture_before=posture_before,
            posture_after=posture_after,
            environment=decision.environment,
            environment_snapshot=environment_snapshot,
            reason=decision.reason,
        )
