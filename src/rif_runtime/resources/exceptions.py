from __future__ import annotations


class ResourceError(Exception):
    """Base exception for the resources subsystem."""


class DuplicateResourceCapabilityError(ResourceError):
    """Raised when attempting to register a duplicate capability."""


class UnknownResourceCapabilityError(ResourceError):
    """Raised when a requested capability is not registered."""
