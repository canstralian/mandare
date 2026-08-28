from mandare.capabilities.echo import EchoCapability
from mandare.capabilities.registry import CapabilityRegistry
from mandare.execution.kernel import ExecutionKernel
from mandare.execution.manifest import ExecutionManifest
from mandare.execution.result import ExecutionStatus


def test_execution_kernel_executes_echo_capability() -> None:
    registry = CapabilityRegistry([EchoCapability()])
    kernel = ExecutionKernel(registry)

    manifest = ExecutionManifest(
        actor="agent:test",
        capability="echo",
        action="ping",
    )

    result = kernel.execute(manifest)

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.output["actor"] == "agent:test"
    assert result.output["action"] == "ping"
