class ExecutionError(Exception):
    """
    Base exception for all execution kernel errors.
    """

    pass


class PolicyViolationError(ExecutionError):
    """
    Raised when execution is attempted without satisfying policy.
    """

    pass


class CapabilityNotFoundError(ExecutionError):
    """
    Raised when the requested capability cannot be resolved.
    """

    pass


class AdapterExecutionError(ExecutionError):
    """
    Raised when a capability adapter fails during execution.
    """

    pass


class ExecutionTimeoutError(ExecutionError):
    """
    Raised when execution exceeds its permitted runtime.
    """

    pass


class EvidenceGenerationError(ExecutionError):
    """
    Raised when execution completes but evidence cannot be recorded.
    """

    pass
