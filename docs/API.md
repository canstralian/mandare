# RIF Runtime API

Source of truth: `src/rif_runtime/api.py`. Routes marked **auth** require an
`X-API-Key` header matching one of the comma-separated keys in
`RIF_CONTROL_PLANE_API_KEYS`. Control-plane auth fails closed: with no keys
configured a guarded route answers `503`, with a wrong key `401`.

## Read-only

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service banner, version, route hints |
| GET | `/health` | Status, current environment, current posture |
| GET | `/v1/environments` | All environment profiles and the active one |
| GET | `/v1/graph/summary` | Governance graph node/edge counts |
| GET | `/v1/telemetry/summary` | Rolling 60-minute denial count and event total |
| GET | `/v1/persistence/summary` | Decision totals, tallied by result and by rule |
| GET | `/v1/recovered-state` | Graph and posture replayed from `decisions.jsonl` |
| GET | `/v1/audit` | Combined live + persisted audit view |
| GET | `/v1/policies` | Configured policy rules |
| GET | `/v1/mcp/metasploit/capabilities` | Capability taxonomy and contract hash |

## Simulation (unauthenticated, side-effect free)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/mcp/invoke` | Dry-run an `mcp.invoke` policy evaluation |
| POST | `/v1/mcp/metasploit/evaluate` | Dry-run a Metasploit intent through the governor |

Both are dry runs: they return the decision without mutating posture or
appending to the stores. `/v1/policy/evaluate` is the recording path.

Request body for `/v1/mcp/metasploit/evaluate`:

```json
{
  "intent": {"capability": "module.search", "target": "cve-2017-0144"},
  "mode": "read_only_firewall",
  "token": null
}
```

`intent` is required; `mode` is one of `read_only_firewall`, `shadow`,
`lab_broker`. A malformed body returns `422`.

## Control plane (auth)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/policy/evaluate` | Evaluate a request and record the decision |
| POST | `/v1/environment/{name}` | Switch the active environment profile |
| POST | `/v1/posture/reset` | Reset posture to `normal` |
| POST | `/v1/posture/{posture}` | Set posture explicitly |
| PUT | `/v1/policies/{rule_id}` | Create or replace a policy rule |
| DELETE | `/v1/policies/{rule_id}` | Delete a policy rule |
| POST | `/v1/mcp/metasploit/token` | Mint a capability token |

`/v1/posture/reset` is registered before `/v1/posture/{posture}`; reversing
that order makes FastAPI parse `reset` as a `Posture` and return `422`.

`/v1/mcp/metasploit/token` accepts `intent` (required), `approver`, and
`ttl_seconds` (1..3600, default 600). Token lifetime is capped so a single
approval cannot mint a long-lived execution grant.

## Posture

Posture escalates automatically as denials accumulate in the rolling
60-minute window: 3 denials → `elevated`, 10 → `restricted`, 20 → `locked`.
A `locked` runtime denies everything.

Escalation is one-way. Denial volume can only raise posture; nothing in the
reflexive loop lowers it, so a runtime driven to `locked` stays there until an
operator calls `POST /v1/posture/reset`.

## State directory

All persisted state lives under `data/` by default. Set `RIF_DATA_DIR` to
relocate the decision log, posture history, evidence log, and policy rules as
a set — the test suite uses this to keep its writes out of the repository.
