# RIF Runtime API

Source of truth: `src/rif_runtime/api.py`. Update this file when routes change.

Routes marked **[auth]** require the control-plane API key (`ControlPlaneAuth`,
`src/rif_runtime/auth.py`).

## Runtime

```text
GET  /
GET  /health
GET  /v1/environments
POST /v1/environment/{name}          [auth]
POST /v1/policy/evaluate             [auth]
```

## Posture

```text
POST /v1/posture/{posture}           [auth]
POST /v1/posture/reset               [auth]
```

## Observability

```text
GET  /v1/graph/summary
GET  /v1/telemetry/summary
GET  /v1/persistence/summary
GET  /v1/recovered-state
GET  /v1/audit
```

## MCP

```text
POST /v1/mcp/invoke
GET  /v1/mcp/metasploit/capabilities
POST /v1/mcp/metasploit/evaluate
POST /v1/mcp/metasploit/token        [auth]
```

## Policies

```text
GET    /v1/policies
PUT    /v1/policies/{rule_id}        [auth]
DELETE /v1/policies/{rule_id}        [auth]
```

## Runs

```text
POST /v1/runs
```

Authenticated by Supabase JWT identity (`IdentityId`), **not** by
`ControlPlaneAuth` — it is the one route on the user-facing identity path rather
than the control plane. Deny-safe: a policy denial still writes evidence before
returning 403, and the run id is returned in the `X-RIF-Run-Id` header.

## Notes

- `POST /v1/posture/reset` — earlier revisions of this file listed this as
  `POST /v1/runtime/reset-posture`, which has never existed.
- `GET /docs` is FastAPI's generated OpenAPI UI, not a runtime route.
