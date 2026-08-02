"""
Resource contracts.

Resources model addressable state.
Providers perform operations against resources.
"""

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
from .registry import ResourceCapabilityRegistry
from .resource import ResourceReference
from .snapshot import ResourceSnapshot

__all__ = [
    "DuplicateResourceCapabilityError",
    "ResourceCapabilityDescriptor",
    "ResourceCapabilityRegistry",
    "ResourceEffect",
    "ResourceError",
    "ResourceId",
    "ResourceKind",
    "ResourceReference",
    "ResourceSnapshot",
    "UnknownResourceCapabilityError",
]
