# RIF Runtime API

The API is the integration surface for agents, automation workers, local tools, and edge/cloud deployments. Treat it as a governance boundary: call it before executing risky actions, persist the returned decision, and only proceed when the decision is `allow`.

Interactive OpenAPI docs are available at `GET /docs` when the server is running.

## Health and environment

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Basic service entrypoint. |
| `GET` | `/health` | Liveness check with current environment and posture. |
| `GET` | `/v1/environments` | List configured runtime environments. |
| `POST` | `/v1/environment/{name}` | Switch the active environment profile. |

## Policy and posture

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/policy/evaluate` | Evaluate one proposed action and return an allow/deny decision. |
| `POST` | `/v1/posture/{posture}` | Set posture explicitly. |
| `POST` | `/v1/posture/reset` | Reset posture to the normal operating state. |

Minimal policy request:

```json
{
  "actor": "agent:orchestrator",
  "action": "http.request",
  "target": "https://api.anthropic.com/v1/messages"
}
```

Action names matter. Host allowlists are applied to network-like actions such as `http.request`, `api.call`, `mcp.invoke`, and `package.install`; other action names are matched more literally.

## Observability and recovery

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/graph/summary` | Summarize actor-target relationships recorded by the governance graph. |
| `GET` | `/v1/telemetry/summary` | Summarize recent decisions and posture signals. |
| `GET` | `/v1/persistence/summary` | Report persisted decision and posture history counts. |
| `GET` | `/v1/recovered-state` | Show state reconstructed from persisted records. |
| `GET` | `/v1/audit` | Return auditable decision history. |

## MCP and security-tool workflows

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/mcp/invoke` | Evaluate and route an MCP invocation through the governance boundary. |
| `GET` | `/v1/mcp/metasploit/capabilities` | List governed Metasploit capability metadata. |
| `POST` | `/v1/mcp/metasploit/evaluate` | Evaluate a Metasploit-oriented action. |
| `POST` | `/v1/mcp/metasploit/token` | Issue a scoped token for governed Metasploit workflows. |

## Policy rule management

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/policies` | List persisted policy rules. |
| `PUT` | `/v1/policies/{rule_id}` | Create or replace a policy rule. |
| `DELETE` | `/v1/policies/{rule_id}` | Delete a policy rule. |

## Terminal-first smoke path

```bash
python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000
BASE=http://127.0.0.1:8000 bash scripts/smoke.sh
```

For a single decision without running the API:

```bash
rif check "agent:test" "http.request" "https://blocked.example.com"
```
