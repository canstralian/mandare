# spec/mcp/

Governance contract for the **MCP server framework**: how RIF Runtime admits,
classifies, and gates Model Context Protocol tool invocations. Per ADR-0008
(`docs/adr-0008-agentos-rif-v1-architecture.md`), MCP is a *governed
integration* — the framework exposes governed capabilities, never raw tool
access.

| Artifact | Status | Contents |
| --- | --- | --- |
| `SPEC.md` | drafted | The framework spec: authority model, threat model, ordered decision procedure, destructive-action hard gate, conformance, evaluation scorecard, open decisions |

## Grounding in the reference implementation

This contract generalizes the already-shipped, single-server
`MetasploitGovernor` (`src/rif_runtime/mcp/metasploit.py`) into a
server-agnostic framework. Where behaviour already exists in the runtime, the
spec **references** it as the normative source rather than restating it (see
`SPEC.md` §7 and the OD log). Current runtime surface the framework builds on:

- `POST /v1/mcp/invoke`, `GET /v1/mcp/metasploit/capabilities`,
  `POST /v1/mcp/metasploit/evaluate`, `POST /v1/mcp/metasploit/token`
  (`src/rif_runtime/api.py`).
- `mcp.invoke` ∈ `NETWORK_ACTIONS` and the `allow_mcp_server_network_access`
  profile flag (`src/rif_runtime/policy.py`, `src/rif_runtime/schemas.py`).
- The signed `CapabilityToken` / `EvidenceEvent` machinery
  (`src/rif_runtime/mcp/metasploit.py`).

The runtime under `src/rif_runtime/` implements this contract; it does not
define it. Contract changes land here first, then flow into the implementation.
