from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResourceKind(StrEnum):
    """
    Categories of addressable resources.

    A resource models state, not the provider used to access it.
    """

    REPOSITORY = "repository"
    DOCUMENT = "document"
    PAGE = "page"
    FILESYSTEM = "filesystem"
    OBJECT_STORE = "object_store"
    VECTOR_STORE = "vector_store"
    DATABASE = "database"
    MCP_SERVER = "mcp_server"
    SERVICE = "service"


@dataclass(frozen=True, slots=True)
class ResourceId:
    """
    Stable identifier for a resource.

    Resource identity is independent of location or transport.
    """

    kind: ResourceKind
    namespace: str
    name: str

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.namespace}/{self.name}"
