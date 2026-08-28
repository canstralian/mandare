# AGENTS.md

Guidance for AI coding agents working in Mandare.

## Repository model

Mandare is a Python FastAPI service (`mandare.api:app`) with a Typer CLI (`rif`). It primarily uses local JSON/JSONL persistence, but the repository also contains an **optional Supabase integration** for run/evidence persistence and JWT verification. Do not describe the project as having no external integrations.

For architecture, read [`ARCHITECTURE.md`](ARCHITECTURE.md). For contributor expectations, read [`CONTRIBUTING.md`](CONTRIBUTING.md). For security-sensitive work, read [`SECURITY.md`](SECURITY.md). For documentation authority, read [`docs/README.md`](docs/README.md).

## Evidence-first rule

Do not turn documentation, a roadmap item, a specification, or a workflow definition into a claim that the runtime currently implements it.

Before asserting a capability exists, inspect the relevant code and tests. Before asserting a CI/security control passed, inspect the workflow run/status. Mark uncertain claims `[UNVERIFIED]` rather than filling the gap with inference.

## Current development path

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

Locked dependency path:

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pip install -e . --no-deps
```

## Current CLI

```bash
rif serve
rif check <actor> <action> <target>
rif replay [decisions_path]
rif msf-check <capability> <target> [--mode ...] [--actor ...] [--scope-id ...]
```

Do not invent or reuse historical examples for commands that are not in `src/mandare/cli.py`.

## Validation

Run the relevant checks before declaring work complete:

```bash
ruff check src tests
ruff format --check src tests
mypy src/mandare --ignore-missing-imports
pytest -q
```

For dependency/security changes:

```bash
pip-audit --requirement requirements/runtime.txt --disable-pip
pip-audit --requirement requirements/dev.txt --disable-pip
bandit -r src/ -ll
```

The repository also configures CodeQL, Gitleaks, Dependency Review, and a merge gate in GitHub Actions.

## Runtime state

Runtime-generated state normally lives under `data/`, with `RIF_DATA_DIR` available for isolation. Tests should use isolated temporary directories rather than shared repository state.

Posture can persist across restarts. Do not assume a fresh `MandareRuntime()` starts at normal posture when persisted state is present.

## Security boundaries

The control plane uses `X-API-Key` and `RIF_CONTROL_PLANE_API_KEYS`. A missing configuration fails closed for guarded operations.

Do not grant authority to model output. In particular, do not treat an API key for an external model/provider as proof that Mandare policy has authorized provider egress.

## Contract discipline

If a change crosses identity, capability, evidence, replay, MCP, or provider-egress boundaries, inspect `spec/README.md` and open specification reviews first. Do not implement a second competing contract while a cross-domain review is unresolved.

## Documentation

When behaviour changes, update the implementation-backed documentation in the same change. Keep historical release notes historical. Avoid unsupported performance, compliance, security, or maturity claims.
