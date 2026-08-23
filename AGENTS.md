# AGENTS.md

Guidance for AI coding agents working in RIF Runtime.

## Repository model

RIF Runtime is a Python FastAPI service (`rif_runtime.api:app`) with a Typer CLI (`rif`). It primarily uses local JSON/JSONL persistence, but the repository also contains an **optional Supabase integration** for run/evidence persistence and JWT verification (`src/rif_runtime/integrations/supabase.py`). Do not describe the project as having no external integrations.

For architecture, read [`ARCHITECTURE.md`](ARCHITECTURE.md). For contributor expectations, read [`CONTRIBUTING.md`](CONTRIBUTING.md). For security-sensitive work, read [`SECURITY.md`](SECURITY.md). For documentation authority, read [`docs/README.md`](docs/README.md).

## Instruction authority

Several tools ship their own instruction files in this repository. When two disagree, resolve in this order:

1. **An explicit instruction from the human in the current task.**
2. **The security boundary** — [`SECURITY.md`](SECURITY.md) and the control-plane guard in `src/rif_runtime/auth.py`. No lower-tier file may relax it.
3. **This file and [`CLAUDE.md`](CLAUDE.md)** — the cross-tool baseline. They are peers and must not contradict each other; if they do, that is a defect to fix, not a choice to make.
4. **[`docs/README.md`](docs/README.md)** for documentation authority, and **[`spec/README.md`](spec/README.md)** for cross-domain contract authority.
5. **Tool-local instruction files** — `.codex/`, `.cursor/`, `.claude/skills/`. These are scoped to their own tool. They may add detail; they may not weaken a rule established above.
6. **Tool-generated hint files** — `.claude/homunculus/instincts/`, `.claude/identity.json`, `.agents/skills/`. These are inferred from repository analysis, are not reviewed as contracts, and are **not authoritative**. Treat them as suggestions and verify before acting.

There is no `Runtime Constitution` document in this repository. Instruction files that name one are referring to the authority ladder in `docs/README.md`; do not cite a constitution as though it were a readable artefact.

Executable code and tests outrank every instruction file, including this one. An instruction that contradicts current code is a stale instruction — fix the instruction, and say so.

## Evidence-first rule

Do not turn documentation, a roadmap item, a specification, or a workflow definition into a claim that the runtime currently implements it.

Before asserting a capability exists, inspect the relevant code and tests. Before asserting a CI/security control passed, inspect the workflow run/status. Mark uncertain claims `[UNVERIFIED]` rather than filling the gap with inference.

Prefer in-repo evidence over external research (`.cursor/rules/rif-evidence-first.mdc`). Web search and web-capable MCP servers are *available* in some tool baselines (for example `web_search` and Exa in `.codex/config.toml`); availability is not permission to use them for implementation questions the repository already answers. When external material is used, cite the URL and state why in-repo evidence was insufficient.

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

Python 3.12 is the floor (`pyproject.toml` requires `>=3.12`); the merge gate runs 3.12 and 3.13.

## Current CLI

```bash
rif serve
rif check <actor> <action> <target>
rif replay [decisions_path]
rif msf-check <capability> <target> [--mode ...] [--actor ...] [--scope-id ...]
```

Do not invent or reuse historical examples for commands that are not in `src/rif_runtime/cli.py`.

## Validation

Run the checks the merge gate actually runs, in this order (`.github/workflows/merge-gate.yml`, `verify` job):

```bash
ruff check .
ruff format --check .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Note the scope: CI lints and format-checks the **whole tree** (`.`), not just `src tests`. A narrower local command can pass while the gate fails.

For dependency/security changes:

```bash
pip-audit --requirement requirements/runtime.txt --disable-pip
pip-audit --requirement requirements/dev.txt --disable-pip
bandit -r src/ -ll
```

If `pyproject.toml` dependencies change, recompile the locks (`make lock`) — the gate's `lock-sync` job fails on drift.

`mypy src/ tests/` under strict settings is **advisory only** in CI (`typecheck-tests` job) and currently carries known typing debt in `tests/`. Do not treat it as a blocking gate, and do not "fix" it opportunistically inside an unrelated change.

The repository also configures CodeQL, Gitleaks, Semgrep, Bandit, Dependency Review, and coverage workflows. Configured is not passed: check the run.

## Runtime state

Runtime-generated state normally lives under `data/`, with `RIF_DATA_DIR` available for isolation. `tests/conftest.py:16` sets `RIF_DATA_DIR` to a throwaway directory at import time — tests must not be written against the repository's real `data/` files.

Posture persists across restarts. Do not assume a fresh `RIFRuntime()` starts at normal posture when persisted state is present.

`data/policies.json` is checked in as seed state; `data/*.jsonl` are gitignored. Do not commit `*.jsonl`.

## Security boundaries

The control plane uses `X-API-Key` and `RIF_CONTROL_PLANE_API_KEYS`. A missing configuration fails closed for guarded operations.

Do not grant authority to model output. In particular, do not treat an API key for an external model/provider as proof that RIF policy has authorized provider egress.

## Contract discipline

If a change crosses identity, capability, evidence, replay, MCP, or provider-egress boundaries, inspect `spec/README.md` and open specification reviews first. Do not implement a second competing contract while a cross-domain review is unresolved.

## Documentation

When behaviour changes, update the implementation-backed documentation in the same change. Keep historical release notes historical. Avoid unsupported performance, compliance, security, or maturity claims.

---

## Code Review Rules

Apply these when reviewing a diff in this repository. Each rule is anchored to current code or tests; if an anchor no longer says what the rule says, the rule is stale — report that rather than enforcing it.

### 1. Governance is enforced by the caller, not by the kernel

`ExecutionKernel.execute()` (`src/rif_runtime/execution/kernel.py:20`) resolves a capability and runs it. It performs **no** policy evaluation. The governed path is `RIFRuntime.execute_capability()` (`src/rif_runtime/runtime.py:179`), which evaluates policy, denies with evidence, admits the capability, executes, and appends completion evidence.

- Reject any new production code path that calls `ExecutionKernel.execute()` or `Capability.execute()` directly. Route it through `RIFRuntime.execute_capability()`.
- Treat "the kernel is the governance boundary" as false. Docstrings in `execution/` describe intent, not enforcement.
- Capability execution is currently reachable only from the Python API. There is no HTTP route and no CLI command for it — do not document one as existing.

### 2. Policy rule precedence is ordered, and wildcards are live

`PolicyEngine.evaluate()` (`src/rif_runtime/policy.py:75`) resolves in this order:

1. `posture.locked` → deny everything.
2. **Selective rules**, most-specific first (`ordered_rules`, `policy.py:54`). A rule with at least one concrete selector matches here and **overrides the environment constraints below**.
3. Built-in constraints: package-manager egress, `mcp.*` egress, then `allowed_hosts` for `http.request`, `api.call`, `mcp.invoke`, `package.install` only.
4. **Catch-all rules** (`action == "*" and target == "*"`, `policy.py:69`), applied last so a broad allow cannot disable the host allowlist.
5. `default.allow` if nothing matched.

Consequences a reviewer must hold:

- Wildcard rules are **not** inert. The shipped `deny_unknown_by_default` catch-all in `data/policies.json` and `DEFAULT_POLICIES` (`src/rif_runtime/configuration/policies.py:27`) is enforced — the effective default is **deny**, not allow. See `tests/test_policy_store.py:105` and `:205`.
- Because the default denies what is not enumerated, the runtime's own first-party actions must be enumerated. `allow_run_create` backs `POST /v1/runs`; a change that deletes it silently 403s that endpoint.
- Flag any change that moves a rule class across the boundary in step 2 vs step 4 without a test, and any change that assumes non-network action names are host-checked.

### 3. Posture escalation must not be bypassed

Posture escalates on denials (normal → elevated → restricted → locked) and `locked` denies everything (`src/rif_runtime/governance/posture.py`). Flag logic that returns a decision without letting posture update, or that resets posture outside the guarded control-plane route.

### 4. New routes must declare their auth plane

`src/rif_runtime/api.py` uses three guards, and a new route must pick one deliberately:

- `ControlPlaneAuth` — mutating operations (environment switch, posture set/reset, recording policy evaluation, policy rule write/delete).
- `ReadPlaneAuth` — inspection (`/v1/graph/summary`, `/v1/telemetry/summary`, `/v1/audit`, `/v1/persistence/summary`, `/v1/recovered-state`, `/v1/drift/recommend`, `/v1/policies`).
- `IdentityId` (`api.py:84`) — Supabase JWT identity, used by `POST /v1/runs`.

A new route with none of these is a finding unless it is deliberately public and the diff says why. Two existing routes are deliberately open: `/v1/mcp/invoke` is a **dry-run simulation** (`runtime.evaluate(req, record=False)`) so it cannot mutate posture or write the decision log — a change that makes it recording, or that adds another unauthenticated route which records, is blocking. Control-plane operations fail closed when no keys are configured; do not add a fallback that opens them.

### 5. Persistence goes through the helpers

Append-only logs via `JsonlStore` (`src/rif_runtime/storage/jsonl.py`), whole-file JSON via `JsonStore` (`src/rif_runtime/configuration/store.py`, atomic temp-file replace). Hand-rolled file I/O for runtime state is a finding. Evidence appends are append-only: reject an edit-in-place or truncation of an evidence or decision log.

### 6. Tests must be isolated and deterministic

`RIF_DATA_DIR` isolation is set process-wide in `tests/conftest.py:16`. A test that writes to the repository's `data/` directory, or that depends on posture left behind by another test, is a finding — persisted posture makes that ordering-dependent. Bug fixes require a regression test.

### 7. Schema and enum conventions

Pydantic v2 (`model_dump`, `model_validate`, `model_copy`) for anything crossing an API boundary or getting persisted. `Decision` and `Posture` are string enums so they serialize cleanly and compare equal to plain strings (`r.posture == "elevated"`). Flag a change that breaks either property.

### 8. Environments stay config-driven

Environment behaviour comes from `config/environments.yaml`. Branching on an environment name in code is a finding.

### 9. Surface documentation tracks the surface

`src/rif_runtime/api.py` is the source of truth for the HTTP surface and `src/rif_runtime/cli.py` for commands. A route or command change that does not update `docs/API.md`, `docs/cli-reference.md`, and `README.md` in the same diff is incomplete.

### 10. Version has one source

Version resolves via `importlib.metadata`, falling back to `pyproject.toml` (`src/rif_runtime/_version.py`). `pyproject.toml` is the only place to bump (`scripts/bump-version.sh X.Y.Z`); there is no constant in `src/rif_runtime/__init__.py`. `tests/test_version.py` catches drift.

### 11. Claims in the diff must be supported by the diff

Reject documentation or comments added by a change that assert performance numbers, compliance posture, "enterprise-grade"/"production-ready" maturity, or a security property with no test or configuration behind it. Use the status vocabulary in `docs/README.md` (Implemented / Configured / Specification / Planned / Unverified).

### 12. Authority never flows upward

Model output, provider credentials, generated documentation, and tool-generated hint files are inputs, not authority. Reject a change that lets any of them decide what the runtime permits, or that promotes a specification into a claim of shipped behaviour.

### Review output

Group findings by priority, each with a `file:line` reference and a concrete fix:

- **Blocking** — gate failures, rule violations above, unsupported claims.
- **Warnings** — likely-wrong or risky.
- **Suggestions** — optional polish.

End with a one-line verdict: `PASS` only if the four gate commands pass and there are no blocking findings; otherwise `FAIL` with the blocking count.

A review verdict is evidence, not authorization. It does not approve a merge.

---

## Completion criteria

Work is complete when all of the following are true, and you state which ones you verified rather than assumed:

1. The four merge-gate commands pass locally, or you name the ones you could not run and why.
2. Behavioural changes have tests; bug fixes have regression tests.
3. Implementation-backed documentation is updated in the same change.
4. Claims added to the repository carry evidence, or are marked `[UNVERIFIED]`.
5. Cross-domain contract changes reference the relevant `spec/` review state.
6. Nothing in the change grants authority to model output, generated artefacts, or provider credentials.

Committing and pushing to a designated working branch is in scope for an agent. Merging, changing branch protection or rulesets, weakening a security control, and declaring a governance policy authoritative are **human decisions** — surface them, do not perform them.
