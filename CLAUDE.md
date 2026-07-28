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

The kernel pipeline (`kernel.py`) wraps that circuit for model-backed
execution — the agent is a managed capability, not the orchestrator:

```
Intent -> Context -> Governance -> State -> Budget -> Capability Router
      -> Execution -> Evidence -> Telemetry -> Evolution
```

See `docs/adr-0009-execution-kernel.md`. Governance runs twice: once as
pre-flight admission on the intent, and once per tool call through
`CapabilityApprovalGate` — a model chooses its tool calls *after* admission,
so approving the intent is not approving the actions.

## Layout

```
src/rif_runtime/
  api.py                  FastAPI app, all HTTP routes (source of truth for the API surface)
  cli.py                  Typer CLI: `rif serve`, `rif check`, `rif replay`, `rif kernel`
  kernel.py               RIFKernel — the pipeline orchestrator
  intent.py               Intent (stage 1); digest pins it into the ledger
  identity.py             IdentityResolver, TrustTier — unknown actors are untrusted
  context.py              ContextAssembler — assembles instructions, fences untrusted text
  budget.py               BudgetManager — per-intent ceilings by trust tier
  capabilities.py         CapabilityRouter — narrows the offer; never authorises
  execution.py            ExecutionEngine protocol, CapabilityApprovalGate, echo engine
  evidence.py             EvidenceLedger — hash-chained, wraps audit.py
  telemetry.py            Telemetry — execution metrics (distinct from governance/telemetry.py)
  evolution.py            EvolutionQueue — proposals for an operator, never self-applied
  paths.py                RIF_DATA_DIR resolution for every persisted store
  adapters/               Execution engines per provider; SDKs imported lazily (extras)
  governance/engine.py    GovernanceEngine — wraps PolicyEngine for the kernel
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
push/PR. `ruff format .` is also enforced (by `quality.yml`'s
`ruff-mypy-pytest` job, separate from `ci.yml`); run it before committing so
the repo stays uniformly formatted.

Manual smoke test against a running server. `/v1/policy/evaluate` is
auth-guarded, so the server and the script need the same key:

```bash
RIF_CONTROL_PLANE_API_KEYS=smoke-key rif serve &
RIF_API_KEY=smoke-key BASE=http://127.0.0.1:8000 ./scripts/smoke.sh
```

## Conventions

- Python 3.12, Pydantic v2 models (`model_dump`, `model_validate`, `model_copy`)
  for everything that crosses an API boundary or gets persisted.
- The codebase is formatted with `ruff format .`; run it before committing.
  Double quotes, spaced operators/keyword args, and trailing commas on
  multi-line calls are the enforced style — don't hand-roll a denser style
  even in modules that used to be terser (e.g. `policy.py`).
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
- **Docs lag the code.** `docs/API.md` has been reconciled with the real route
  table (it previously listed a `POST /v1/runtime/reset-posture` that never
  existed; the route is `POST /v1/posture/reset`). `README.md` and
  `docs/RIF_RUNTIME_MVP.md` still describe the project with overlapping but
  not identical endpoint lists. Treat `src/rif_runtime/api.py` as the source
  of truth for the API surface, and update the docs when you change routes.
- **Posture escalation is one-way.** `governance/posture.py` is the single
  source of the ladder and its denial thresholds; `ReflexiveLoop` and
  `ReplayEngine` both derive posture from it, so a replayed runtime lands on
  the same rung as the live one. `next_posture` takes the max of the current
  posture and the denial-derived floor — it must never return a lower rung,
  or ordinary denial traffic would unlock a `locked` runtime. Standing a
  posture down is an explicit operator act (`POST /v1/posture/reset`).
- **Capability names must be mapped into the `mcp.` action namespace.**
  `governance/engine.py:capability_action` does this before every per-call
  evaluation. Skip it and a capability like `exploit.run` reaches
  `PolicyEngine` as an action matching no rule and no built-in constraint, so
  it falls through to `default.allow` — silently ungoverned. Covered by
  `tests/test_kernel.py::test_every_capability_lands_in_the_governed_action_namespace`.
- **The kernel's governance runs twice, deliberately.** `evaluate(context)` is
  pre-flight admission on the intent; `CapabilityApprovalGate` calls
  `evaluate_capability` once per tool invocation during execution. Never
  replace the gate with an auto-approval rule — the model picks its tool calls
  after admission, from text that may be adversarial, so admitting the intent
  is not authorising the actions.
- **`rif_runtime` depends on no model vendor.** `execution.ExecutionEngine` is
  a Protocol; provider SDKs live in `adapters/` behind lazy imports and extras
  (`pip install -e '.[foundry]'`). `EchoExecutionEngine` exercises the whole
  pipeline in CI without a provider. Don't add a vendor SDK to the core deps.
- **Two telemetry modules, different jobs.** `governance/telemetry.py` tracks
  *decisions* in a rolling window to drive posture; `telemetry.py` tracks
  *executions* (tokens, latency, calls). They are not interchangeable.
- **Version bump checklist.** `__version__` is derived from installed package
  metadata via `importlib.metadata.version("rif-runtime")` (single source of
  truth: `pyproject.toml`). When cutting a release, **only `pyproject.toml`
  needs the version bump** — `src/rif_runtime/__init__.py` has no hardcoded
  version string to sync. Use `scripts/bump-version.sh X.Y.Z` to update
  `pyproject.toml`, then run `pip install -e .` to refresh the installed
  metadata before committing. The version consistency test
  (`tests/test_version.py`) will catch any drift when the package is
  installed (as CI always does via `pip install -e .` before `pytest`).
- **State directory is relocatable.** Every persisted store resolves its path
  through `rif_runtime.paths` (`RIF_DATA_DIR`, default `data/`). `tests/conftest.py`
  points it at a tmp dir before any `rif_runtime` module is imported — module-level
  `RIFRuntime()` construction in `api.py` means a fixture would be too late.
  A full `pytest -q` therefore leaves the working tree clean; it previously
  appended to the JSONL logs and rewrote the checked-in `data/policies.json`
  through the `/v1/policies` routes. Prefer `tmp_path` (see
  `tests/test_policy_store.py`) when a single test needs its own store.
- `data/policies.json` is checked into git (it's the seed/default state);
  `data/*.jsonl` files are gitignored. Don't flip that.

## API surface (from `src/rif_runtime/api.py`)

Routes marked **auth** require `X-API-Key` (see `auth.py`). Full table with
request shapes: `docs/API.md`.

```
GET    /
GET    /health
GET    /v1/environments
POST   /v1/environment/{name}            auth
POST   /v1/policy/evaluate               auth
POST   /v1/posture/reset                 auth
POST   /v1/posture/{posture}             auth
GET    /v1/graph/summary
GET    /v1/telemetry/summary
GET    /v1/persistence/summary
GET    /v1/recovered-state
GET    /v1/audit
POST   /v1/mcp/invoke
GET    /v1/mcp/metasploit/capabilities
POST   /v1/mcp/metasploit/evaluate
POST   /v1/mcp/metasploit/token          auth
GET    /v1/policies
PUT    /v1/policies/{rule_id}            auth
DELETE /v1/policies/{rule_id}            auth
```
