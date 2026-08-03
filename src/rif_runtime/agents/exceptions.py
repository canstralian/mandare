"""
Agent runtime exceptions.
"""


class AgentError(Exception):
    """Base class for all agent runtime errors."""


class AgentManifestError(AgentError):
    """Raised when an agent manifest is invalid."""


class DuplicateAgentError(AgentError):
    """Raised when an agent is registered twice."""


class UnknownAgentError(AgentError):
    """Raised when an unknown agent is requested."""
