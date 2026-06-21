# RIF Runtime MVP

Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
rif serve
```

Test:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/policy/evaluate -H 'content-type: application/json' -d '{"actor":"agent:orchestrator","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'
```

## RIF Governance Layer

Endpoints:

GET /health
GET /docs
GET /v1/environments
POST /v1/policy/evaluate
GET /v1/graph/summary
GET /v1/telemetry/summary
GET /v1/audit
POST /v1/mcp/invoke

Persistence:

data/decisions.jsonl
data/posture_history.jsonl

Architecture:

Agent
  ↓
Policy Engine
  ↓
Reflexive Loop
  ↓
Governance Graph
  ↓
Persistent Memory
