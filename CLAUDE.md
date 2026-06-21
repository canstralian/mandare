# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.

## What this is

RIF Runtime is a governed agent runtime: a policy engine that mediates actions
taken by AI agents (HTTP requests, MCP tool invocations, package installs) and
produces an auditable trail of allow/deny decisions. It is a small FastAPI
service plus a Typer CLI, backed by JSONL/JSON files for persistence — no
database, no external services.

Core execution circuit:

```
Agent request
  -> PolicyEngine.evaluate()      (src/rif_runtime/policy.py)
  -> PolicyDecision
  -> GovernanceGraph.record_decision()   (src/rif_runtime/graph/memory.py)
  -> ReflexiveLoop.observe() -> new Posture   (src/rif_runtime/governance/reflexive.py)
  -> JsonlStore.append() (decisions + posture transitions)   (src/rif_runtime/storage/jsonl.py)
  -> Audit / telemetry / graph summary APIs
```

Trust model: deny by default, environment-scoped allowed hosts, and a
"posture" that escalates automatically as denials accumulate (normal ->
elevated -> restricted -> locked). A locked posture denies everything
regardless of other rules.

## Layout

```
src/rif_runtime/
  api.py                  FastAPI app, all HTTP routes (source of truth for the API surface)
  cli.py                  Typer CLI: `rif serve`, `rif check`, `rif replay`
  runtime.py              RIFRuntime — wires config, policy engine, reflexive loop,
                           graph, and persistence together; one instance per process
  config.py               Loads config/environments.yaml into RuntimeConfig
  policy.py               PolicyEngine — the actual allow/deny decision logic
  schemas.py               Pydantic models: PolicyRequest, PolicyDecision, Decision,
                           Posture, EnvironmentProfile, RuntimeConfig
  replay.py                ReplayEngine — rebuilds graph + posture from decisions.jsonl
                           (forensic recovery after restart)
  agents/                 Thin example agents (orchestrator, auditor, deputy) —
                           illustrate how an agent would construct PolicyRequests
                           and consume decisions; not a framework
  governance/
    posture.py            PostureManager — denial-count thresholds -> Posture
    reflexive.py          ReflexiveLoop — glues TelemetryStore + PostureManager
    telemetry.py          TelemetryStore — in-memory rolling window of decisions
  graph/
    memory.py             GovernanceGraph — networkx MultiDiGraph of actor->target edges
    relationships.py      Query helpers over the graph (actor_targets, denied_edges)
  configuration/
    policies.py           PolicyRule + PolicyStore — JSON-backed CRUD for declarative
                           policy rules, exposed via /v1/policies (NOTE: see Gotchas)
    store.py               JsonStore — generic atomic-write JSON file helper
  storage/
    jsonl.py               JsonlStore — append-only JSONL log with count()/count_by()

config/environments.yaml  Environment profiles: RIF_Runtime, RIF_Research, RIF_CI
data/                      Runtime state: decisions.jsonl, posture_history.jsonl
                           (gitignored), policies.json (checked in, seeds via PolicyStore)
docs/                      ARCHITECTURE.md, API.md, RIF_RUNTIME_MVP.md, ROADMAP.md
tests/                     pytest suite, mirrors src/ modules being exercised
scripts/smoke.sh           Curl-based smoke test against a running `rif serve`
```

## Development workflow

Setup:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

Run the API:

```bash
rif serve              # uvicorn with --reload, http://127.0.0.1:8000
```

CLI usage:

```bash
rif check <actor> <action> <target>     # evaluate one request, print the decision
rif replay [decisions_path]             # rebuild graph/posture from a decisions.jsonl
```

Test, lint, type-check (this is exactly what `.github/workflows/ci.yml` runs, in order):

```bash
ruff check src tests
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Run all three before considering a change done — CI enforces all three on every
push/PR and there is no separate formatting step (no black/isort configured).

Manual smoke test against a running server:

```bash
rif serve &
BASE=http://127.0.0.1:8000 ./scripts/smoke.sh
```

## Conventions

- Python 3.12, Pydantic v2 models (`model_dump`, `model_validate`, `model_copy`)
  for everything that crosses an API boundary or gets persisted.
- Existing source files use a dense style (no spaces around `=` in keyword
  args in some modules, e.g. `policy.py`). Match the style of the file you're
  editing rather than reformatting wholesale; ruff is the enforced linter, not
  black.
- New persisted state goes through `JsonlStore` (append-only logs, e.g.
  decisions) or `JsonStore` (whole-file JSON with atomic temp-file replace,
  e.g. policies). Don't hand-roll file I/O elsewhere.
- `RIFRuntime` is constructed fresh per process/test (`RIFRuntime()`), not a
  singleton with DI — tests instantiate it directly and rely on real files
  under `data/`.
- Enums (`Decision`, `Posture`) are `str, Enum` so they serialize cleanly and
  compare equal to plain strings (tests assert `r.posture == "elevated"`).
- Environment profiles are config-driven (`config/environments.yaml`), not
  hardcoded; add new environments there rather than branching in code.

## Gotchas / known inconsistencies

- **PolicyStore rule matching is exact-match only.** `RIFRuntime` owns a
  shared `PolicyStore` (`self.policy_store`) and passes its rules into
  `PolicyEngine.evaluate()`. Only fully-specific rules (non-`"*"` `action`
  and `target`) are consulted as overrides, checked right after the
  `posture.locked` check and before the built-in package/MCP/network
  constraints — see `policy.py:rule_matches`. Wildcard rules (like the
  seeded `deny_unknown_by_default`) are intentionally skipped so they don't
  blanket-deny everything; they're inert placeholders until rule precedence
  for partial wildcards is designed.
- **Docs lag the code.** `docs/API.md` lists `POST /v1/runtime/reset-posture`,
  but the actual route in `api.py` is `POST /v1/posture/reset`. `README.md`
  and `docs/RIF_RUNTIME_MVP.md` both describe the project with overlapping
  but not identical endpoint lists. Treat `src/rif_runtime/api.py` as the
  source of truth for the API surface, and update the docs when you change
  routes.
- **Version drift.** `pyproject.toml` still says `version = "0.1.0"` and
  `src/rif_runtime/__init__.py` says `__version__='0.1.0'`, while recent
  commits are tagged v0.2.0/v0.2.1 in their messages. Bump both files
  together if you're asked to cut a release.
- Tests that instantiate `RIFRuntime()` write real records into
  `data/decisions.jsonl` and `data/posture_history.jsonl` (gitignored) as a
  side effect — there's no fixture isolating this. `tests/test_policy_store.py`
  is the one place that uses `tmp_path` correctly; follow that pattern for new
  tests that touch persistent storage where isolation matters.
- `data/policies.json` is checked into git (it's the seed/default state);
  `data/*.jsonl` files are gitignored. Don't flip that.

## API surface (from `src/rif_runtime/api.py`)

```
GET  /
GET  /\nGET  /health\nGET  /v1/environments\nPOST /v1/environment/{name}\nPOST /v1/policy/evaluate\nPOST /v1/posture/{posture}\nPOST /v1/posture/reset\nGET  /v1/graph/summary\nGET  /v1/telemetry/summary\nGET  /v1/persistence/summary\nGET  /v1/recovered-state\nGET  /v1/audit\nPOST /v1/mcp/invoke\nGET  /v1/policies\nPUT  /v1/policies/{rule_id}\nDELETE /v1/policies/{rule_id}
```
