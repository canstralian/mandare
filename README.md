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

RIF Runtime is a governed execution substrate for builders who want agents and automation to do real work without turning into a black box. It sits between intent and action, evaluates each request against policy and runtime posture, then writes an auditable trail you can inspect when something gets denied, escalates, or behaves strangely at 2 a.m.

Use RIF when you need a small, local-first control plane for AI agents, scripts, MCP tools, package installs, and HTTP/API calls. It is intentionally boring infrastructure: FastAPI, Typer, JSON/JSONL persistence, deterministic tests, and no database or external service.

**Non-goal:** RIF is not an autonomous agent framework. Bring your own agent, workflow engine, or cron job; RIF provides the governance boundary around the actions they try to take.

- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [Roadmap](docs/ROADMAP.md)
- [Reflexive Evolution Pipeline](docs/REFLEXIVE_EVOLUTION.md)

## What you get

- **Policy gate:** deny-by-default evaluation for network-like actions such as `http.request`, `api.call`, `mcp.invoke`, and `package.install`.
- **Runtime posture:** automatic escalation from `normal` through `elevated`, `restricted`, and `locked` as denials accumulate.
- **Audit trail:** append-only JSONL decisions and posture transitions that can be replayed or inspected with normal shell tools.
- **Graph memory:** actor-to-target relationships that make repeated behavior visible instead of trapped in logs.
- **Two control surfaces:** a FastAPI service for systems integration and a `rif` CLI for terminal-first checks.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
rif serve
```

For scripted testing, run uvicorn directly so the process is easy to stop:

```bash
python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000
```

## Try a decision

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/policy/evaluate \
  -H 'content-type: application/json' \
  -d '{"actor":"agent:orchestrator","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'
```

No server needed for a one-off terminal check:

```bash
rif check "agent:test" "http.request" "https://blocked.example.com"
```

## Control surfaces

Core endpoints:

- `GET /health`
- `GET /docs`
- `GET /v1/environments`
- `POST /v1/environment/{name}`
- `POST /v1/policy/evaluate`
- `POST /v1/posture/{posture}`
- `POST /v1/posture/reset`
- `GET /v1/graph/summary`
- `GET /v1/telemetry/summary`
- `GET /v1/persistence/summary`
- `GET /v1/recovered-state`
- `GET /v1/audit`
- `POST /v1/mcp/invoke`
- `GET /v1/policies`
- `PUT /v1/policies/{rule_id}`
- `DELETE /v1/policies/{rule_id}`

Runtime persistence:

- `data/decisions.jsonl`
- `data/posture_history.jsonl`
- `data/policies.json`

## Current implementation

```text
Agent / automation
  ↓
PolicyRequest
  ↓
PolicyEngine.evaluate()
  ↓
PolicyDecision
  ↓
ReflexiveLoop.observe()
  ↓
Posture update
  ↓
GovernanceGraph.record_decision()
  ↓
JSONL persistence + audit/telemetry APIs
```

## Target architecture

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

## Operating model

RIF is designed for builders who care about fast iteration and post-incident debuggability:

1. Define environments and allowed hosts in `config/environments.yaml`.
2. Send every risky action through `/v1/policy/evaluate` or `rif check` before execution.
3. Inspect `/v1/audit`, `/v1/graph/summary`, and `data/*.jsonl` when behavior changes.
4. Replay persisted decisions to recover governance state after restart.
5. Keep policy mutation explicit and reviewable instead of hidden inside agent prompts.

## License

MIT. See `LICENSE`.
