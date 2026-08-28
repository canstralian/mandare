from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .resource import ResourceReference


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    """
    Immutable observation of resource state.
    """

    resource: ResourceReference
    snapshot_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)
