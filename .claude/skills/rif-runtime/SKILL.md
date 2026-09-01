---
name: rif-runtime
description: Development patterns and conventions for the Mandare repository (Python package `rif_runtime`). Use when writing or reviewing code under `src/` or `tests/`, naming files, or preparing a commit.
---

# Mandare Development Patterns

Conventions for the Mandare repository. Every rule below is grounded in a file
in this repository; the reference is named so it can be re-checked rather than
trusted.

## What this codebase is

A **Python 3.12+** project — a FastAPI service (`rif_runtime.api:app`) and a
Typer CLI (`rif`), backed by local JSON/JSONL files. There is no TypeScript,
no Node toolchain, and no database.

| Layer | Value | Source |
|---|---|---|
| Product | Mandare | `README.md` |
| Distribution (PyPI) | `mandare` | `pyproject.toml` `[project].name` |
| Python package | `rif_runtime` | `src/rif_runtime/` |
| CLI | `rif` | `pyproject.toml` `[project.scripts]` |
| Environment variables | `RIF_*` | `.env.example` |

The distribution name is the only one the rename changed. Do not rename
`rif_runtime`, `rif`, or `RIF_*` because the product is called Mandare.

## Coding conventions

### File naming

`snake_case` modules under `src/rif_runtime/`, e.g. `policy.py`, `replay.py`,
`_version.py`. Subpackages are plain directories with an `__init__.py`
(`governance/`, `storage/`, `capabilities/`).

### Imports

Absolute imports from the package root, sorted by ruff's isort rules
(`select = ["E", "F", "I", "UP", "B"]` in `pyproject.toml`):

```python
from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import Decision
```

`from __future__ import annotations` at the top of modules using deferred
annotations.

### Formatting

`ruff format` decides — double quotes, spaced operators and keyword arguments,
trailing commas on multi-line calls, `line-length = 88`. Do not hand-roll a
denser style, even in modules that used to be terser (e.g. `policy.py`).

### Typing

Public functions are annotated; `mypy src/rif_runtime --ignore-missing-imports`
must pass. Pydantic v2 (`model_dump`, `model_validate`, `model_copy`) for
anything crossing an API boundary or getting persisted.

### Commit messages

Concise imperative subject in conventional form (`CONTRIBUTING.md`):

```text
docs: clarify replay limitations
fix(policy): preserve deny precedence
feat(mcp): add governed capability evaluation
```

## Testing patterns

- **pytest**, configured in `pyproject.toml`: `testpaths = ["tests"]`,
  `python_files = ["test_*.py"]`.
- Tests live in `tests/`, named `test_*.py` — mirroring the module under test
  (`tests/test_policy_store.py`, `tests/test_replay.py`). Not alongside the
  source, and never `*.test.*`.
- Persistence tests use temporary directories; `RIF_DATA_DIR` isolates runtime
  state. Posture can survive restart, so a fresh `RIFRuntime()` does not imply
  a clean posture when persisted state exists.
- `RIFRuntime` is constructed fresh per process/test (`RIFRuntime()`), not a
  singleton with dependency injection.

## Validation

Run the same gate CI runs (`.github/workflows/merge-gate.yml`):

```bash
ruff check .
ruff format --check .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Security and dependency checks:

```bash
bandit -r src/ -ll
pip-audit --requirement requirements/runtime.txt --disable-pip
pip-audit --requirement requirements/dev.txt --disable-pip
```

Dependency locks are generated, never hand-edited. After changing dependencies
in `pyproject.toml`, run `make lock`; the `lock-sync` job fails on any drift.

## Bug-fix workflow

1. Branch from `main`.
2. Make the smallest change that fixes the cause.
3. Add or update a regression test under `tests/`.
4. Run the four gate commands above.
5. Commit with a `fix:` subject, push, and open a pull request.

When an API or CLI changes, update `docs/API.md` and `docs/cli-reference.md`
in the same change — `src/rif_runtime/api.py` and `src/rif_runtime/cli.py` are
the source of truth for those surfaces.
