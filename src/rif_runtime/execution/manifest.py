from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ExecutionManifest:
    """
    Immutable execution request produced after policy evaluation.

    The manifest is the contract between the Policy Engine and the
    Execution Kernel. It describes what is permitted to execute,
    but does not perform execution itself.
    """

    actor: str
    capability: str
    action: str
    target: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    manifest_id: str = field(default_factory=lambda: str(uuid4()))
