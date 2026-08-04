from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"


@dataclass(slots=True)
class ExecutionResult:
    """
    Immutable result produced by the Execution Kernel.

    Every execution attempt, successful or otherwise, produces an
    ExecutionResult suitable for evidence recording and replay.
    """

    status: ExecutionStatus
    message: str = ""
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
