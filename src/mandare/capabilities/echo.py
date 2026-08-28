from __future__ import annotations

from mandare.execution.manifest import ExecutionManifest
from mandare.execution.result import (
    ExecutionResult,
    ExecutionStatus,
)

from .capability import Capability


class EchoCapability(Capability):
    """Simple capability used for runtime validation."""

    @property
    def name(self) -> str:
        return "echo"

    def execute(
        self,
        manifest: ExecutionManifest,
    ) -> ExecutionResult:
        return ExecutionResult(
            status=ExecutionStatus.SUCCEEDED,
            message="Echo capability executed.",
            output={
                "actor": manifest.actor,
                "action": manifest.action,
                "parameters": manifest.parameters,
            },
        )
