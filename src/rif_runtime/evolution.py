"""Evolution Queue: the runtime's backlog of proposed changes.

The last pipeline stage. Denials, budget exhaustion, and execution failures are
signals that the current policy, budget, or capability set may be wrong. Rather
than adapting automatically — which would let traffic rewrite its own
governance — the runtime *queues a proposal* for an operator to accept.

This is the deliberate seam between reflexive and evolutionary behaviour:
posture reacts automatically because it only ever tightens; policy changes
require a human because they can loosen.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class ProposalSource(str, Enum):
    governance_denial = "governance_denial"
    budget_exhausted = "budget_exhausted"
    execution_failure = "execution_failure"
    capability_gap = "capability_gap"


class EvolutionProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    source: ProposalSource
    summary: str
    signal: dict[str, Any] = Field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvolutionQueue:
    def __init__(self, max_pending: int = 500) -> None:
        self.max_pending = max_pending
        self._items: deque[EvolutionProposal] = deque()
        self._lock = threading.Lock()

    def enqueue(
        self, source: ProposalSource, summary: str, **signal: Any
    ) -> EvolutionProposal:
        proposal = EvolutionProposal(source=source, summary=summary, signal=signal)
        with self._lock:
            self._items.append(proposal)
            while len(self._items) > self.max_pending:
                self._items.popleft()
        return proposal

    def pending(self) -> list[EvolutionProposal]:
        return [p for p in self._items if p.status is ProposalStatus.pending]

    def all(self) -> list[EvolutionProposal]:
        return list(self._items)

    def resolve(self, proposal_id: str, status: ProposalStatus) -> bool:
        """Operator action: accept or reject a queued proposal."""

        with self._lock:
            for index, proposal in enumerate(self._items):
                if proposal.proposal_id == proposal_id:
                    self._items[index] = proposal.model_copy(update={"status": status})
                    return True
        return False

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for proposal in self._items:
            counts[proposal.source.value] = counts.get(proposal.source.value, 0) + 1
        return {
            "total": len(self._items),
            "pending": len(self.pending()),
            "by_source": counts,
        }
