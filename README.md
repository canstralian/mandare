# RIF Runtime MVP

[![CI](https://github.com/canstralian/rif-runtime/actions/workflows/ci.yml/badge.svg)](https://github.com/canstralian/rif-runtime/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/canstralian/rif-runtime?label=release)](https://github.com/canstralian/rif-runtime/releases)
[![Tag](https://img.shields.io/github/v/tag/canstralian/rif-runtime?label=tag)](https://github.com/canstralian/rif-runtime/tags)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://github.com/canstralian/rif-runtime/actions/workflows/ci.yml)
[![Issues](https://img.shields.io/github/issues/canstralian/rif-runtime)](https://github.com/canstralian/rif-runtime/issues)
[![Last Commit](https://img.shields.io/github/last-commit/canstralian/rif-runtime)](https://github.com/canstralian/rif-runtime/commits/main)
[![Tests](https://img.shields.io/badge/tests-26%20passing-brightgreen)](https://github.com/canstralian/rif-runtime/actions)
[![Type Checked](https://img.shields.io/badge/mypy-clean-blue)](https://github.com/canstralian/rif-runtime)
[![Lint](https://img.shields.io/badge/ruff-clean-success)](https://github.com/canstralian/rif-runtime)
[![License](https://img.shields.io/github/license/canstralian/rif-runtime)](LICENSE)

RIF Runtime is a governed execution substrate for agents and tools. It compiles intent into visible, policy-evaluated command objects before a capability is invoked, then records the evidence and posture needed to explain the outcome.

- [Roadmap](docs/ROADMAP.md)
- [Reflexive Evolution Pipeline](docs/REFLEXIVE_EVOLUTION.md)

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
rif serve
```

## Try it

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/policy/evaluate \
  -H 'content-type: application/json' \
  -d '{"actor":"agent:orchestrator","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'
```

## RIF Governance Layer

Endpoints:

- `GET /health`
- `GET /docs`
- `GET /v1/environments`
- `POST /v1/policy/evaluate`
- `GET /v1/graph/summary`
- `GET /v1/telemetry/summary`
- `GET /v1/audit`
- `POST /v1/mcp/invoke`

Persistence:

- `data/decisions.jsonl`
- `data/posture_history.jsonl`

Architecture:

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

## License

MIT. See `LICENSE`.
