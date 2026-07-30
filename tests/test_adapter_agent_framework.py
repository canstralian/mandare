"""The Agent Framework adapter stays importable without its SDK, and its MCP
egress is governed by the environment profile rather than by the environment
variable alone.
"""

import pytest

from rif_runtime.adapters.agent_framework import AgentFrameworkEngine
from rif_runtime.context import ContextAssembler
from rif_runtime.execution import ExecutionEngine
from rif_runtime.runtime import RIFRuntime
from rif_runtime.state import RuntimeState


def _context(environment: str, actor: str = "human:alice"):
    runtime = RIFRuntime()
    runtime.set_environment(environment)
    state = RuntimeState(runtime=runtime)
    intent = state.capture_intent("do the thing", actor=actor)
    from rif_runtime.identity import IdentityResolver

    return ContextAssembler().build(intent, IdentityResolver().resolve(intent), state)


def test_adapter_imports_without_the_sdk_installed():
    # agent-framework/azure-identity are an optional extra; importing the
    # adapter must not require them.
    engine = AgentFrameworkEngine(mcp_url="https://api.github.com/mcp")
    assert engine.model


def test_adapter_satisfies_the_execution_protocol():
    assert isinstance(AgentFrameworkEngine(), ExecutionEngine)


def test_sealed_environment_blocks_mcp_egress():
    # RIF_Runtime sets allow_mcp_server_network_access: false.
    engine = AgentFrameworkEngine(mcp_url="https://api.github.com/mcp")
    reason = engine.check_mcp_egress(_context("RIF_Runtime"))
    assert reason is not None
    assert "seals MCP egress" in reason


def test_mcp_host_must_be_in_allowed_hosts():
    # RIF_Research permits MCP egress but only to its allowed_hosts.
    engine = AgentFrameworkEngine(mcp_url="https://evil.example.com/mcp")
    reason = engine.check_mcp_egress(_context("RIF_Research"))
    assert reason is not None
    assert "not in allowed_hosts" in reason


def test_permitted_host_passes_the_egress_check():
    engine = AgentFrameworkEngine(mcp_url="https://api.github.com/mcp")
    assert engine.check_mcp_egress(_context("RIF_Research")) is None


def test_missing_mcp_url_is_reported():
    engine = AgentFrameworkEngine(mcp_url="")
    reason = engine.check_mcp_egress(_context("RIF_Research"))
    assert reason is not None
    assert "RIF_MCP_SERVER" in reason


def test_connect_refuses_before_opening_a_session():
    import asyncio

    engine = AgentFrameworkEngine(mcp_url="https://evil.example.com/mcp")
    context = _context("RIF_Research")

    async def attempt():
        async with engine.connect(context):
            pass  # pragma: no cover - must not be reached

    # PermissionError, not an SDK ImportError: the egress check runs first.
    with pytest.raises(PermissionError):
        asyncio.run(attempt())
