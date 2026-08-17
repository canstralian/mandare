# RIF Runtime

[![CI](https://github.com/canstralian/rif-runtime/actions/workflows/ci.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/ci.yml)
[![Quality](https://github.com/canstralian/rif-runtime/actions/workflows/quality.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/quality.yml)
[![Release](https://github.com/canstralian/rif-runtime/actions/workflows/release.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/release.yml)
[![CodeQL](https://github.com/canstralian/rif-runtime/actions/workflows/codeql.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/codeql.yml)
[![Bandit](https://github.com/canstralian/rif-runtime/actions/workflows/bandit.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/bandit.yml)
[![Gitleaks](https://github.com/canstralian/rif-runtime/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/gitleaks.yml)


[![Latest Release](https://img.shields.io/github/v/release/canstralian/rif-runtime)](https://github.com/canstralian/rif-runtime/releases)
[![License](https://img.shields.io/github/license/canstralian/rif-runtime)](LICENSE)
[![Issues](https://img.shields.io/github/issues/canstralian/rif-runtime)](https://github.com/canstralian/rif-runtime/issues)
[![Last Commit](https://img.shields.io/github/last-commit/canstralian/rif-runtime)](https://github.com/canstralian/rif-runtime/commits)
![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)

RIF Runtime is a governed execution substrate for agents and tools. It compiles intent into visible, policy-evaluated command objects before a capability is invoked, then records the evidence and posture needed to explain the outcome.

**Non-goal:** RIF is not an autonomous agent framework. RIF is a governance and execution substrate for agents.

- [Roadmap](docs/ROADMAP.md)
- [Reflexive Evolution Pipeline](docs/REFLEXIVE_EVOLUTION.md)

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export RIF_CONTROL_PLANE_API_KEYS=dev-key
rif serve
```

## Try it

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/policy/evaluate \
  -H 'content-type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{"actor":"agent:orchestrator","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'
```

## RIF Governance Layer

Endpoints (see [docs/API.md](docs/API.md) for the full reference):

- `GET /` — root / route index
- `GET /health` — liveness; returns environment and posture
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

Persistence:

- `data/decisions.jsonl`
- `data/posture_history.jsonl`

### Current implementation

```text
Agent
  ↓
Intent Compiler
  ↓
Policy Engine
  ↓
Reflexive Loop
  ↓
Governance Graph
  ↓
Persistent Memory
```

### Target architecture

The diagram below is the architecture the [roadmap](docs/ROADMAP.md) milestones build toward. Stages beyond Policy Engine — Capability Router, Adapter Layer, Execution, and EvidenceRecord — do not exist in the runtime yet; see the roadmap for sequencing.

```text
Agent / User
      ↓
Intent Compiler
      ↓
Policy Gate
      ↓
Capability Router
      ↓
Adapter Layer
      ↓
Execution
      ↓
EvidenceRecord
      ↓
Reflexive Review
      ↓
Governance Graph
      ↓
Persistent Memory
```

## License

MIT. See `LICENSE`.
