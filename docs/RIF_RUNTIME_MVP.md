# RIF Runtime MVP

RIF is a governed agent runtime.

Current execution circuit:

Agent request
→ Policy engine
→ Decision
→ Reflexive loop
→ Posture update
→ Governance graph
→ Persistent JSONL memory
→ Audit API

## Core endpoints

- `GET /`
- `GET /health`
- `GET /v1/environments`
- `POST /v1/environment/{name}`
- `POST /v1/policy/evaluate`
- `POST /v1/posture/reset`
- `POST /v1/posture/{posture}`
- `GET /v1/graph/summary`
- `GET /v1/telemetry/summary`
- `GET /v1/persistence/summary`
- `GET /v1/recovered-state`
- `GET /v1/audit`
- `POST /v1/mcp/invoke`
- `GET /v1/mcp/metasploit/capabilities`
- `POST /v1/mcp/metasploit/evaluate`
- `POST /v1/mcp/metasploit/token`
- `GET /v1/policies`
- `PUT /v1/policies/{rule_id}`
- `DELETE /v1/policies/{rule_id}`
- `POST /v1/runs`

## Memory files

- `data/decisions.jsonl`
- `data/posture_history.jsonl`

## Design principle

Live memory is fast and reflexive.
Persistent memory is forensic and survives restart.
