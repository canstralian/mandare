"""Microsoft Agent Framework adapter: the Agent as a managed capability.

The Agent Framework plugs into the *execution* layer. It does not orchestrate —
the kernel already decided that this intent may run, which capabilities are on
offer, and what budget applies before this module is reached.

Tool approval is delegated to `CapabilityApprovalGate`, never auto-approved.
The framework's own `SkillsProvider.all_tools_auto_approval_rule` would approve
every tool the model selects, which places the model's chosen actions outside
governance: pre-flight admission judged the *intent*, but tool calls are chosen
afterwards from text that may itself be adversarial. Routing approval through
the gate keeps each call mediated by the policy engine, recorded in the ledger,
and counted toward posture.

The SDK is imported inside `connect()` so this module can be imported — and
type-checked — without `agent-framework` or `azure-identity` installed.

    pip install -e '.[foundry]'
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

from ..capabilities import Capability
from ..context import ExecutionContext
from ..execution import CapabilityApprovalGate, CapabilityCall, ExecutionResult

FOUNDRY_ENDPOINT_ENV = "AZURE_FOUNDRY_ENDPOINT"
MCP_SERVER_ENV = "RIF_MCP_SERVER"
MODEL_ENV = "AZURE_MODEL"
DEFAULT_MODEL = "gpt-4.1"


class AgentFrameworkEngine:
    """Runs one execution through an Agent Framework agent.

    `mcp_url` is validated against the active environment profile before any
    connection is opened: the runtime's own `allowed_hosts` and
    `allow_mcp_server_network_access` govern where capabilities may come from,
    and reading the URL straight from the environment would bypass that.
    """

    def __init__(
        self,
        project_endpoint: str | None = None,
        mcp_url: str | None = None,
        model: str | None = None,
        credential: Any = None,
    ) -> None:
        self.project_endpoint: str = (
            project_endpoint or os.environ.get(FOUNDRY_ENDPOINT_ENV) or ""
        )
        self.mcp_url: str = mcp_url or os.environ.get(MCP_SERVER_ENV) or ""
        self._model: str = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        self._credential = credential

    @property
    def model(self) -> str:
        return self._model

    def credential(self) -> Any:
        if self._credential is None:
            from azure.identity import AzureCliCredential

            self._credential = AzureCliCredential()
        return self._credential

    def check_mcp_egress(self, context: ExecutionContext) -> str | None:
        """Reason the configured MCP server is not reachable, or None."""

        if not self.mcp_url:
            return f"{MCP_SERVER_ENV} is not set"
        profile = context.profile
        if not profile.allow_mcp_server_network_access:
            return f"environment {context.environment} seals MCP egress"
        # Reuse the engine's own host matching so the adapter cannot drift from
        # the rules the policy engine applies.
        from ..policy import allowed, host

        if profile.networking_type == "limited" and not allowed(
            host(self.mcp_url), profile.allowed_hosts
        ):
            return f"MCP host not in allowed_hosts: {host(self.mcp_url)}"
        return None

    @asynccontextmanager
    async def connect(self, context: ExecutionContext) -> AsyncIterator[Any]:
        """Open an MCP session and yield a SkillsProvider over it."""

        blocked = self.check_mcp_egress(context)
        if blocked is not None:
            raise PermissionError(blocked)

        from agent_framework import MCPSkillsSource, SkillsProvider
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with streamable_http_client(url=self.mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield SkillsProvider(MCPSkillsSource(client=session))

    async def run(
        self,
        context: ExecutionContext,
        capabilities: list[Capability],
        gate: CapabilityApprovalGate,
    ) -> ExecutionResult:
        from agent_framework import Agent
        from agent_framework.foundry import FoundryChatClient

        client = FoundryChatClient(
            project_endpoint=self.project_endpoint,
            credential=self.credential(),
            model=self._model,
        )

        async with self.connect(context) as skills:
            async with Agent(
                client=client,
                # Assembled by the ContextAssembler from constitution,
                # identity, runtime mode, policies, and intent -- not hardcoded.
                instructions=context.system_prompt,
                context_providers=[skills, context],
                middleware=[self.approval_middleware(gate)],
            ) as agent:
                response = await agent.run(context.prompt)

        return self._to_result(response, gate)

    def approval_middleware(self, gate: CapabilityApprovalGate) -> Any:
        """ToolApprovalMiddleware bound to the kernel's policy gate.

        Deliberately not `all_tools_auto_approval_rule`: every tool call is
        put to `gate.approve`, which evaluates it against the policy engine
        and records the outcome.
        """

        from agent_framework import ToolApprovalMiddleware

        def approve(tool_call: Any) -> bool:
            return gate.approve(
                CapabilityCall(
                    capability=getattr(tool_call, "name", str(tool_call)),
                    target=self.mcp_url or "mcp://unknown",
                    arguments=dict(getattr(tool_call, "arguments", {}) or {}),
                )
            )

        return ToolApprovalMiddleware(approval_callback=approve)

    def _to_result(
        self, response: Any, gate: CapabilityApprovalGate
    ) -> ExecutionResult:
        usage = getattr(response, "usage", None)
        return ExecutionResult(
            output=str(getattr(response, "text", response) or ""),
            tokens=int(getattr(usage, "total_tokens", 0) or 0),
            latency_ms=float(getattr(response, "latency", 0.0) or 0.0),
            capability_calls=list(gate.approved),
            success=True,
            model=self._model,
        )
