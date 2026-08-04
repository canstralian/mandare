"""
Resource contracts.

Resources model addressable state.
Providers perform operations against resources.
"""

from .builder import RepositorySnapshotBuilder
from .descriptor import (
    ResourceCapabilityDescriptor,
    ResourceEffect,
)
from .exceptions import (
    DuplicateResourceCapabilityError,
    ResourceError,
    UnknownResourceCapabilityError,
)
from .identity import (
    ResourceId,
    ResourceKind,
)
from .inventory import (
    ModuleInfo,
    TestInfo,
)
from .registry import ResourceCapabilityRegistry
from .repository import (
    RepositoryResource,
    RepositorySnapshot,
)
from .resource import ResourceReference
from .scanner import RepositoryScanner
from .snapshot import ResourceSnapshot

__all__ = [
    "DuplicateResourceCapabilityError",
    "ModuleInfo",
    "RepositoryResource",
    "RepositoryScanner",
    "RepositorySnapshot",
    "RepositorySnapshotBuilder",
    "ResourceCapabilityDescriptor",
    "ResourceCapabilityRegistry",
    "ResourceEffect",
    "ResourceError",
    "ResourceId",
    "ResourceKind",
    "ResourceReference",
    "ResourceSnapshot",
    "TestInfo",
    "UnknownResourceCapabilityError",
]
