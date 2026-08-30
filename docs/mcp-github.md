# GitHub MCP Gateway

Mandare treats GitHub MCP as a downstream capability, not as an authority source.

```text
Endeavour
   |
   | MCP / stdio
   v
mandare-mcp-github
   |
   | policy: mcp.invoke
   | environment + posture
   | pinned read-only tool contract
   v
GitHub MCP Server
   |
   v
GitHub API
```

The first vertical slice is deliberately read-only. The gateway starts the
official GitHub MCP server with `GITHUB_READ_ONLY=1` and an explicit allow-list
of read tools. Mandare then evaluates every invocation before forwarding it.
GitHub's own read-only mode removes write tools even when they are requested,
and its tool configuration supports an explicit `GITHUB_TOOLS` allow-list.

## Prerequisites

- Docker running locally.
- A GitHub Personal Access Token supplied through the environment; do not put
  it in this repository.
- Python 3.12+.

Install the optional MCP dependency:

```bash
python -m pip install -e '.[mcp]'
```

Set the gateway environment:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN='...'
export RIF_ENVIRONMENT='RIF_GitHub_ReadOnly'
export RIF_MCP_ACTOR='agent:endeavour'
```

`RIF_Runtime` intentionally denies MCP egress by default. `RIF_GitHub_ReadOnly`
is the constrained environment that explicitly permits GitHub MCP traffic only
to `api.github.com` / `github.com`.

## Endeavour connection

Configure Endeavour to connect to **Mandare's gateway**, not directly to the
GitHub MCP server. The exact outer JSON key depends on the MCP host, but the
stdio server definition is:

```json
{
  "command": "mandare-mcp-github",
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}",
    "RIF_ENVIRONMENT": "RIF_GitHub_ReadOnly",
    "RIF_MCP_ACTOR": "agent:endeavour"
  }
}
```

The gateway itself launches:

```text
ghcr.io/github/github-mcp-server
```

with:

```text
GITHUB_READ_ONLY=1
GITHUB_TOOLS=<pinned read-only tool set>
```

## Security boundary

There are currently two independent write barriers:

1. **GitHub MCP server:** read-only mode disables write tools.
2. **Mandare gateway:** only the pinned read-only tool set is exposed to
   Endeavour, and every call must pass Mandare's `mcp.invoke` policy path.

A locked Mandare posture or an environment with MCP egress disabled prevents
forwarding before the downstream server is called.

Unknown GitHub MCP tools are denied rather than dynamically admitted. This is
intentional: a new upstream tool must be explicitly reviewed and added to the
pinned contract before it becomes visible to Endeavour.

## Current limitation

This is the **read-only first vertical slice**, not the final generic MCP
framework. Consequential and destructive GitHub operations remain unavailable.
The existing MCP governance specification requires stronger controls for those
operations, including scoped capability tokens, single-use enforcement,
write-time argument-hash verification, and signed evidence. Those controls
must be implemented before GitHub write access is exposed.
