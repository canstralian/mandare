"""
Agent Runtime.

Provides immutable agent manifests together with deterministic
registration and discovery primitives.
"""

from .exceptions import (
    AgentError,
    AgentManifestError,
    DuplicateAgentError,
    UnknownAgentError,
)
from .manifest import AgentManifest
from .registry import AgentRegistry

__all__ = [
    "AgentError",
    "AgentManifest",
    "AgentManifestError",
    "AgentRegistry",
    "DuplicateAgentError",
    "UnknownAgentError",
]
