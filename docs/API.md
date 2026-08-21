# HTTP API Reference

The HTTP route definitions in `src/rif_runtime/api.py` are the source of truth. This document is a concise human-readable index; the running service's `/docs` and `/openapi.json` provide the generated schema.

## Public/runtime inspection

| Method | Route | Purpose | Auth |
|---|---|---|---|
| `GET` | `/` | Service/root metadata | None |
| `GET` | `/health` | Health/status information | None |
| `GET` | `/v1/environments` | List configured environments | None |
| `GET` | `/v1/graph/summary` | Governance graph summary | None |
| `GET` | `/v1/telemetry/summary` | Telemetry summary | None |
| `GET` | `/v1/persistence/summary` | Persistence summary | None |
| `GET` | `/v1/recovered-state` | Recovered runtime state | None |
| `GET` | `/v1/audit` | Audit/decision view | None |

## Governance operations

| Method | Route | Purpose | Auth |
|---|---|---|---|
| `POST` | `/v1/policy/evaluate` | Evaluate a policy request | None |
| `POST` | `/v1/mcp/invoke` | Evaluate/invoke the governed MCP path | None |
| `POST` | `/v1/mcp/metasploit/evaluate` | Evaluate a Metasploit capability request | None |
| `GET` | `/v1/mcp/metasploit/capabilities` | Inspect governed Metasploit capability metadata | None |

## Mutable control-plane operations

These routes are guarded by `X-API-Key` through `RIF_CONTROL_PLANE_API_KEYS`.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/v1/environment/{name}` | Change the active environment |
| `POST` | `/v1/posture/{posture}` | Set runtime posture |
| `POST` | `/v1/posture/reset` | Reset posture |
| `GET` | `/v1/policies` | List policy rules |
| `PUT` | `/v1/policies/{rule_id}` | Create/update a policy rule |
| `DELETE` | `/v1/policies/{rule_id}` | Delete a policy rule |
| `POST` | `/v1/mcp/metasploit/token` | Mint a governed capability token |

## Authentication

Configure one or more control-plane keys:

```bash
export RIF_CONTROL_PLANE_API_KEYS='replace-with-a-secret-key'
```

Supply the selected key as:

```http
X-API-Key: replace-with-a-secret-key
```

If no control-plane key is configured, guarded operations return `503` rather than silently becoming unauthenticated.

## Example

Evaluate a policy request:

```bash
curl -X POST http://127.0.0.1:8000/v1/policy/evaluate \
  -H 'content-type: application/json' \
  -d '{"actor":"agent:test","action":"http.request","target":"https://example.com"}'
```

The exact response schema is defined by the Pydantic models in `src/rif_runtime/schemas.py` and exposed through the generated OpenAPI document.

## Important boundary

A successful policy evaluation is not equivalent to an unrestricted external side effect. The current runtime contains governance and capability surfaces, while broader execution/evidence contracts remain under active development. In particular, remote model/provider access must not be treated as authorized merely because credentials are configured.

## Compatibility

The API is currently versioned under `/v1`, but the repository is still a release-candidate project. Consumers should pin a known release/tag and test compatibility rather than assuming enterprise-level backward-compatibility guarantees.
