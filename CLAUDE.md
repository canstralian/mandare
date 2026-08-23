# CLAUDE.md

Guidance for AI coding assistants working in RIF Runtime.

## What this repository is

RIF Runtime is a governed Python runtime with a FastAPI HTTP surface and Typer CLI. The default persistence model is local JSON/JSONL, with an optional Supabase integration for run/evidence persistence and JWT verification.

The central trust model is:

```text
request
  -> policy evaluation
  -> decision
  -> posture / graph / telemetry
  -> persistence
  -> replay / inspection
```

Do not describe provider-inference or autonomous-evolution architecture as shipped behaviour.

Capability execution *is* shipped, but narrowly. `RIFRuntime.execute_capability` (`src/rif_runtime/runtime.py:179`) evaluates policy, records evidence on both the denied and completed paths, admits the capability, and executes it. It is reachable from the Python API only — there is no HTTP route and no CLI command for it. Planner and receipt stages appear in design material and do not exist in `src/`.

Note where the boundary actually sits: `ExecutionKernel.execute` (`src/rif_runtime/execution/kernel.py:20`) performs no policy evaluation. Governance is enforced by the caller, so route new execution paths through `execute_capability`.

## Instruction authority

[`AGENTS.md`](AGENTS.md) carries the cross-tool instruction-precedence ladder; this file and `AGENTS.md` are peers and must not contradict each other. Tool-local files (`.codex/`, `.cursor/`, `.claude/skills/`) may add detail but may not weaken a rule set here. Tool-generated hint files (`.claude/homunculus/instincts/`, `.claude/identity.json`, `.agents/skills/`) are not authoritative.

Executable code and tests outrank every instruction file, including this one. An instruction that contradicts current code is stale — fix the instruction and say so.

There is no `Runtime Constitution` document in this repository; the authority ladder in `docs/README.md` is the real one.

## Important source-of-truth files

- `src/rif_runtime/api.py` — current HTTP route definitions
- `src/rif_runtime/cli.py` — current CLI commands
- `src/rif_runtime/runtime.py` — runtime orchestration
- `src/rif_runtime/policy.py` — policy decision logic
- `src/rif_runtime/schemas.py` — API/domain schemas
- `src/rif_runtime/replay.py` — local state reconstruction
- `src/rif_runtime/auth.py` — control-plane API-key guard
- `src/rif_runtime/security.py` — cryptographic/redaction utilities
- `src/rif_runtime/audit.py` — audit hash-chain primitives
- `src/rif_runtime/integrations/supabase.py` — optional remote persistence/JWT integration

For architecture interpretation, read `ARCHITECTURE.md`. For security work, read `SECURITY.md`. For specification boundaries, read `spec/README.md` and open specification reviews.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

Locked environment:

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pip install -e . --no-deps
```

Current CLI:

```bash
rif serve
rif check <actor> <action> <target>
rif replay [decisions_path]
rif msf-check <capability> <target> [--mode ...] [--actor ...] [--scope-id ...]
```

## Validation

```bash
ruff check .
ruff format --check .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

This is the merge gate's `verify` job order and scope. CI lints the whole tree (`.`), so a narrower `ruff check src tests` can pass while the gate fails. `mypy src/ tests/` under strict settings is the separate advisory `typecheck-tests` job — it carries known typing debt and does not block a merge.

Security/dependency checks:

```bash
bandit -r src/ -ll
pip-audit --requirement requirements/runtime.txt --disable-pip
pip-audit --requirement requirements/dev.txt --disable-pip
```

The repository also configures CodeQL, Gitleaks, Dependency Review, and the merge gate. Check the actual workflow run before claiming that a check passed.

## State and tests

Runtime state is normally under `data/`, with `RIF_DATA_DIR` available for isolation. Tests should use temporary directories for persistence.

Posture can survive restart. Do not assume a new runtime instance means a clean posture when persisted state exists.

## Security boundary

Mutable control-plane operations use `X-API-Key` and `RIF_CONTROL_PLANE_API_KEYS` and fail closed when no control-plane keys are configured. Inspection routes use `ReadPlaneAuth`; `POST /v1/runs` uses Supabase JWT identity. `POST /v1/mcp/invoke` is deliberately unauthenticated *and* dry-run (`runtime.evaluate(req, record=False)`) — making it recording, or adding another unauthenticated route that records, is a security-boundary change.

The shipped default policy is deny-by-default: the `deny_unknown_by_default` catch-all in `data/policies.json` is enforced (`tests/test_policy_store.py:105`). Wildcard rules are not inert. First-party actions must stay enumerated — deleting `allow_run_create` silently 403s `POST /v1/runs`.

Never promote model output into authority. An external provider credential is configuration, not a RIF authorization decision.

## Documentation discipline

Use `docs/README.md` for documentation authority and status conventions. Keep claims tied to code, tests, configuration, or verified workflow results. Mark unsupported status `[UNVERIFIED]`.

Do not introduce performance numbers, compliance claims, "enterprise-grade" guarantees, or security properties without current evidence.

When changing a cross-domain contract, stop and inspect the specification-review state before implementing a competing interpretation.
