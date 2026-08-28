from __future__ import annotations

from mandare.capabilities.registry import CapabilityRegistry

from .manifest import ExecutionManifest
from .result import ExecutionResult


class ExecutionKernel:
    """
    Governed execution entry point.

    The kernel is responsible for coordinating execution.
    It never contains capability-specific logic.
    """

    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        manifest: ExecutionManifest,
    ) -> ExecutionResult:
        capability = self._registry.resolve(
            manifest.capability,
        )

        return capability.execute(manifest)
