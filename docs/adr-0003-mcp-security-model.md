# ADR-0003: MCP Security Model

## Status
Proposed (captured 2026-07-09)

## Context
MCP servers expose high-privilege capabilities (databases, workspaces, cloud
consoles) behind a uniform tool-call interface. An unmediated, over-scoped
connector gives an agent workspace-wide write access.

## Decision
All MCP tool invocations are governed actions and pass through the same policy
circuit as HTTP requests and package installs: `PolicyEngine.evaluate()` ->
`PolicyDecision` -> `GovernanceGraph.record_decision()` ->
`ReflexiveLoop.observe()` -> JSONL audit log (`/v1/mcp/invoke` today).

## Consequences
- Every MCP call yields an auditable allow/deny decision
- Denials feed posture escalation; a locked posture denies all MCP activity
- MCP servers are registered as tools with declared risk level and scopes
- The runtime is the trust boundary, never the connector itself
