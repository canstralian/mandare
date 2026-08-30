"""Governed read-only gateway for GitHub's official MCP server.

Endeavour connects to this process, not directly to GitHub MCP. The gateway
owns the policy decision and only forwards calls that Mandare authorises.

The first vertical slice is intentionally read-only. GitHub's server is also
started with ``GITHUB_READ_ONLY=1`` and an explicit tool allow-list, giving us
two independent write barriers while the generic MCP framework is completed.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, TypedDict

import mcp.server.stdio
import mcp.types as types
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.lowlevel import Server

from ..runtime import RIFRuntime
from ..schemas import Decision, PolicyRequest

GITHUB_IMAGE = os.getenv("GITHUB_MCP_IMAGE", "ghcr.io/github/github-mcp-server")
GITHUB_READ_ONLY_TOOLS = (
    "get_me",
    "get_file_contents",
    "get_repository_tree",
    "get_commit",
    "get_latest_release",
    "get_release_by_tag",
    "get_tag",
    "get_label",
    "list_label",
    "list_branches",
    "list_commits",
    "list_releases",
    "list_tags",
    "list_issues",
    "list_issue_types",
    "list_pull_requests",
    "search_code",
    "search_commits",
    "search_issues",
    "search_pull_requests",
    "search_repositories",
    "issue_read",
    "pull_request_read",
)


class GatewayState(TypedDict):
    runtime: RIFRuntime
    client: Client
    tools: list[types.Tool]
    actor: str


@dataclass(frozen=True)
class GatewayConfig:
    actor: str = "agent:endeavour"
    environment: str | None = None
    token: str | None = None

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_PERSONAL_ACCESS_TOKEN is required")
        return cls(
            actor=os.environ.get("RIF_MCP_ACTOR", "agent:endeavour"),
            environment=os.environ.get("RIF_ENVIRONMENT"),
            token=token,
        )


def _target(arguments: dict[str, Any]) -> str:
    owner = arguments.get("owner")
    repo = arguments.get("repo")
    if isinstance(owner, str) and isinstance(repo, str) and owner and repo:
        return f"https://api.github.com/repos/{owner}/{repo}"
    return "https://api.github.com"


def _blocked(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        is_error=True,
        content=[types.TextContent(type="text", text=message)],
    )


@asynccontextmanager
async def gateway_lifespan(_: Server[GatewayState]) -> AsyncIterator[GatewayState]:
    config = GatewayConfig.from_env()
    runtime = RIFRuntime()
    if config.environment is not None:
        runtime.set_environment(config.environment)

    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "-e",
            "GITHUB_READ_ONLY",
            "-e",
            "GITHUB_TOOLS",
            GITHUB_IMAGE,
        ],
        env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": config.token or "",
            "GITHUB_READ_ONLY": "1",
            "GITHUB_TOOLS": ",".join(GITHUB_READ_ONLY_TOOLS),
        },
    )

    async with Client(stdio_client(server_params)) as client:
        discovered = await client.list_tools()
        tools = [
            tool for tool in discovered.tools if tool.name in GITHUB_READ_ONLY_TOOLS
        ]
        missing = sorted(set(GITHUB_READ_ONLY_TOOLS) - {tool.name for tool in tools})
        if missing:
            raise RuntimeError(
                "GitHub MCP server did not expose the pinned read-only tool set: "
                + ", ".join(missing)
            )
        yield {
            "runtime": runtime,
            "client": client,
            "tools": tools,
            "actor": config.actor,
        }


async def list_tools(
    ctx: Any, _params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    state: GatewayState = ctx.lifespan_context
    return types.ListToolsResult(tools=state["tools"])


async def call_tool(
    ctx: Any, params: types.CallToolRequestParams
) -> types.CallToolResult:
    state: GatewayState = ctx.lifespan_context
    tool_name = params.name
    arguments = dict(params.arguments or {})
    exposed_tools = {tool.name for tool in state["tools"]}

    if tool_name not in exposed_tools:
        return _blocked(f"Mandare denied unknown GitHub MCP tool: {tool_name}")

    # Tool descriptions and arguments are data, never authority. The current
    # read-only slice keeps authority entirely in Mandare's policy decision.
    decision = state["runtime"].evaluate(
        PolicyRequest(
            actor=state["actor"],
            action="mcp.invoke",
            target=_target(arguments),
            reason=f"GitHub MCP read-only tool: {tool_name}",
            context={
                "server": "github-mcp-server",
                "tool": tool_name,
                "arguments": arguments,
            },
        )
    )
    if decision.decision != Decision.allow:
        return _blocked(
            f"Mandare denied GitHub MCP call: "
            f"{decision.matched_rule}: {decision.reason}"
        )

    return await state["client"].call_tool(tool_name, arguments)


server: Server[GatewayState] = Server(
    "mandare-github-gateway",
    version="0.1.0",
    instructions=(
        "GitHub access is governed by Mandare. This gateway exposes a pinned "
        "read-only tool set and never grants GitHub write authority."
    ),
    lifespan=gateway_lifespan,
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


async def run() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
