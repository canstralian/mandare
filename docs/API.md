# RIF Runtime API

Authoritative API surface — derived from `src/rif_runtime/api.py`, which is
the single source of truth. Update this file whenever routes are added,
renamed, or removed in `api.py`.

## Routes

```
GET    /
GET    /health
GET    /v1/environments
POST   /v1/environment/{name}
POST   /v1/policy/evaluate
POST   /v1/posture/reset
POST   /v1/posture/{posture}
GET    /v1/graph/summary
GET    /v1/telemetry/summary
GET    /v1/persistence/summary
GET    /v1/recovered-state
GET    /v1/audit
POST   /v1/mcp/invoke
GET    /v1/mcp/metasploit/capabilities
POST   /v1/mcp/metasploit/evaluate
POST   /v1/mcp/metasploit/token
GET    /v1/policies
PUT    /v1/policies/{rule_id}
DELETE /v1/policies/{rule_id}
POST   /v1/runs
```

FastAPI also auto-generates `/docs` (Swagger UI) and `/redoc` (ReDoc) from
the OpenAPI schema — these are not declared in `api.py` but are live on every
running instance.

## Authentication notes

- Routes guarded by `ControlPlaneAuth` require a control-plane Bearer token
  (`RIF_CONTROL_KEY` env var). These include `/v1/environment/{name}`,
  `/v1/policy/evaluate`, `/v1/posture/reset`, `/v1/posture/{posture}`,
  `/v1/mcp/metasploit/token`, `/v1/policies/{rule_id}` (PUT/DELETE).
- `POST /v1/runs` requires a Supabase JWT Bearer token (end-user identity).
- All other routes are unauthenticated.

## Route descriptions

| Route | Description |
|---|---|
| `GET /` | Root; returns name, status, and a short route index. |
| `GET /health` | Liveness check; returns current environment and posture. |
| `GET /v1/environments` | List all configured environment profiles and the active one. |
| `POST /v1/environment/{name}` | Switch the active environment profile. |
| `POST /v1/policy/evaluate` | Evaluate a `PolicyRequest`; records the decision and may advance posture. |
| `POST /v1/posture/reset` | Reset posture to `normal`. Must be registered before `/{posture}` to avoid path-param capture. |
| `POST /v1/posture/{posture}` | Force-set posture to a specific `Posture` value. |
| `GET /v1/graph/summary` | Summary of the live governance graph (actor→target edges). |
| `GET /v1/telemetry/summary` | Rolling-window decision telemetry. |
| `GET /v1/persistence/summary` | Counts and metadata from the persisted JSONL stores. |
| `GET /v1/recovered-state` | Forensic replay of posture and graph rebuilt from `decisions.jsonl`. |
| `GET /v1/audit` | Full audit report produced by `AuditorAgent`. |
| `POST /v1/mcp/invoke` | Unauthenticated dry-run simulation of an MCP tool invocation (does not record). |
| `GET /v1/mcp/metasploit/capabilities` | Catalog of governed Metasploit capabilities. |
| `POST /v1/mcp/metasploit/evaluate` | Unauthenticated dry-run governance check for a Metasploit intent (does not record). |
| `POST /v1/mcp/metasploit/token` | Mint a signed capability token for an approved Metasploit intent. |
| `GET /v1/policies` | List all declarative policy rules from `PolicyStore`. |
| `PUT /v1/policies/{rule_id}` | Upsert a policy rule by ID. |
| `DELETE /v1/policies/{rule_id}` | Delete a policy rule by ID. |
| `POST /v1/runs` | Create a governed execution run (Supabase-authenticated; records policy evidence). |
