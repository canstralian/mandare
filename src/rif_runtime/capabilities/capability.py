from __future__ import annotations

from abc import ABC, abstractmethod

from rif_runtime.execution.manifest import ExecutionManifest
from rif_runtime.execution.result import ExecutionResult


class Capability(ABC):
    """
    Base interface for all executable capabilities.

    Capabilities are side-effecting operations that execute only
    after successful policy evaluation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique capability identifier."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, manifest: ExecutionManifest) -> ExecutionResult:
        """Execute the approved manifest."""
        raise NotImplementedError
