# Contributing to RIF Runtime

Thanks for contributing. By participating you agree to follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## What this project is

RIF Runtime is a **governed agent runtime**: policy evaluation, posture,
audit/replay-oriented persistence, and a FastAPI + Typer surface. It is **not**
a general agent framework. See [README.md](README.md) and
[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

Architecture and contracts under `spec/` are authoritative for v1.0 direction.
If an implementation conflicts with a frozen spec, **stop** and open a Track B
discussion — do not silently diverge.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
pip install -r requirements-dev.txt
# or: pip install -e ".[dev]"
```

Optional: `make setup` if your environment has Make and the target matches this
repo’s Makefile.

## Quality gate (required before PR)

Same order as CI (`.github/workflows/ci.yml` / `quality.yml`):

```bash
ruff check src tests
ruff format .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Do not claim tests passed unless you ran them.

## Branching

```bash
git checkout -b feature/short-description
# fix/…  docs/…  security/…  also fine
```

Prefer small PRs. Do not mix unrelated refactors with behavior changes.

## Coding conventions

- Python 3.12+, Pydantic v2, Ruff format (double quotes, trailing commas).
- Persist via `JsonlStore` / `JsonStore` — no ad-hoc file IO for runtime state.
- New tests that touch storage use `tmp_path` (see `tests/test_policy_store.py`).
- Enums: `StrEnum` where applicable.
- Prefer repository evidence over web search for RIF internals.

## Contracts and Track classification

| Track | Examples | Expectation |
| --- | --- | --- |
| A | Bugfix, docs honesty, CLI help | Preserve contracts |
| B | Event schema, replay semantics, policy DSL | Spec first under `spec/`, then code |
| C | Implementing an approved spec | Follow the frozen document |

Significant identity/replay/aggregate changes need an ADR or spec amendment.

## CLI and API

- **Implemented CLI today:** see [docs/cli-reference.md](docs/cli-reference.md).
- **v1.0 demo CLI design:** [docs/cli-v1-spec.md](docs/cli-v1-spec.md).
- **API source of truth:** `src/rif_runtime/api.py` (docs may lag — update docs when you change routes).

## Pull requests

1. Description: what / why; link issues.
2. Note contract impact (none / Track B with spec path).
3. Ensure quality gate is green.
4. Do not commit secrets, `.env`, or `data/*.jsonl` (except seeded `data/policies.json`).

## Security

See [SECURITY.md](SECURITY.md). Do not file public issues for undisclosed vulns.

## Release process

Maintainers: [RELEASE.md](RELEASE.md). Version bumps: `pyproject.toml` only
(`scripts/bump-version.sh`), then refresh editable install.
