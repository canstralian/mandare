"""Intent: the first stage of the kernel pipeline.

An intent is what was *asked for*. It is never authority — the central RIF
invariant. Governance decides what the request is permitted to become; the
intent itself only records what arrived, who it came from, and when.

The digest pins the request into the evidence chain so a recorded execution can
be tied back to the exact intent that produced it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .security import sha256_digest

# The pipeline stage that turns an intent into a model invocation. Kept as the
# default action so intents flow through the same PolicyEngine vocabulary as
# every other governed action.
AGENT_RUN_ACTION = "agent.run"


class Intent(BaseModel):
    intent_id: str = Field(default_factory=lambda: str(uuid4()))
    actor: str = "agent:kernel"
    request: str
    action: str = AGENT_RUN_ACTION
    target: str = "agent"
    metadata: dict[str, str] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def digest(self) -> str:
        """Stable hash of the semantic content, excluding id and timestamp."""

        return sha256_digest(
            {
                "actor": self.actor,
                "request": self.request,
                "action": self.action,
                "target": self.target,
                "metadata": self.metadata,
            }
        )

    def summary(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "digest": self.digest(),
        }
