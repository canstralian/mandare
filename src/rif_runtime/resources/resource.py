from __future__ import annotations

from dataclasses import dataclass

from .identity import ResourceId


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """
    Reference to a resource.

    The identifier represents the resource itself.
    The URI represents one access location.
    """

    id: ResourceId
    uri: str
    version: str | None = None
