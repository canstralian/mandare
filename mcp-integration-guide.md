# MCP Integration Guide

## Scope

Integrating RIF Runtime with Model Context Protocol servers.

## Architecture

```text
Runtime -> MCP Client -> MCP Server -> Tool
```

## Connection

- stdio
- websocket
- http

## Registration

```yaml
mcp:
  servers:
    - id: osint
      transport: stdio
      command: python
      args: ["server.py"]
```

## Capability Mapping

- MCP tool -> runtime capability
- MCP resource -> context source
- MCP prompt -> planning asset

## Security

- allowlisted servers
- signed binaries where possible
- isolated working directories

## Evidence

Record:

- server id
- tool name
- parameters
- result hash
- latency

## Failure Handling

- unavailable
- timeout
- invalid schema
- authorization failure
