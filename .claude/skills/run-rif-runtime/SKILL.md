---
name: run-rif-runtime
description: Build, run, and drive RIF Runtime. Use when asked to start RIF Runtime, run its tests, build it, evaluate a policy decision, interact with the running API, or drive/exercise the Capability Layer (registering and executing a capability, e.g. before adding a new provider adapter like Hugging Face).
---

RIF Runtime is a FastAPI service (`rif_runtime.api:app`) plus a Typer CLI
(`rif`). Drive it either over HTTP with `curl`/`scripts/smoke.sh` against a
running server, or directly via the `rif check` CLI subcommand, which
evaluates one policy request without needing a server at all.

## Prerequisites

No system packages are required — this is a pure-Python FastAPI + Typer
project with no native deps. **Python 3.12+ is mandatory**, not just
recommended: `pyproject.toml` sets `requires-python = ">=3.12"`, and if the
active `python3` resolves to 3.11 or older, `pip install -e .` fails to
resolve the package and **silently skips it** — no traceback if you're not
watching the output. Verified in this container: on Python 3.11.15,
`pip install -e .` completed with only a `pip` upgrade notice, and
`import rif_runtime` then raised `ModuleNotFoundError`. Check first if
unsure which `python3` you have:

```bash
python3 --version   # must print 3.12.x or 3.13.x
```

If it doesn't, use an explicit interpreter (this container also has
`python3.12` and `python3.13` on PATH) in the setup step below.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

(Substitute `python3.12` or `python3.13` here if the `python3 --version` check
above showed something older.)

No build step — it's a plain installable Python package.

## Run (agent path)

Launch the server **without** `rif serve`. `rif serve` hardcodes
`uvicorn.run(..., reload=True)`, which makes WatchFiles fork a separate
worker process under `multiprocessing.spawn`. The worker's PID is not the
PID captured by `$!`, and its cmdline no longer contains the original
launch string — so both `kill $!` and `pkill -f "rif serve"` silently fail
to stop it (verified: curl to `/health` kept succeeding after both). Launch
uvicorn directly instead, which runs as a single process you can `kill`
cleanly.

`POST /v1/policy/evaluate` is a control-plane-authenticated route
(`ControlPlaneAuth` in `auth.py`) and **fails closed**: with no
`RIF_CONTROL_PLANE_API_KEYS` configured, every request to it returns `503`,
not merely "unauthenticated". Set a key before starting the server — any
non-empty value works for local/agent use:

```bash
export RIF_CONTROL_PLANE_API_KEYS="local-dev-key"
python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000 > /tmp/rif.log 2>&1 &
PID=$!

for i in {1..30}; do curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 0.5; done
curl -sf http://127.0.0.1:8000/health; echo
```

Then drive it with the project's own smoke script for the unauthenticated
routes — health, environment listing, and audit. Append `|| true`: the
script's own two `POST /v1/policy/evaluate` calls will fail with `401` and
abort it under its own `set -euo pipefail` (see below), and without `|| true`
that nonzero exit will look like a launch failure to any caller/script
checking `$?`, when the three preceding checks actually succeeded:

```bash
BASE=http://127.0.0.1:8000 bash scripts/smoke.sh || true
```

**`scripts/smoke.sh`'s own two `POST /v1/policy/evaluate` calls will fail
with `401`** (verified: `curl: (22) The requested URL returned error: 401`,
then the script aborts under its own `set -euo pipefail`) — the committed
script never sends an `X-API-Key` header, so it cannot authenticate against
this route regardless of environment setup. This is a real gap in
`scripts/smoke.sh` itself, not something fixable from the agent-launch side;
treat the script as good for the first three unauthenticated calls only.
To see the actual allow/deny decision pair, call the authenticated route
directly:

```bash
curl -sf -X POST http://127.0.0.1:8000/v1/policy/evaluate \
  -H 'content-type: application/json' -H "X-API-Key: $RIF_CONTROL_PLANE_API_KEYS" \
  -d '{"actor":"agent:smoke","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'; echo

curl -sf -X POST http://127.0.0.1:8000/v1/policy/evaluate \
  -H 'content-type: application/json' -H "X-API-Key: $RIF_CONTROL_PLANE_API_KEYS" \
  -d '{"actor":"agent:smoke","action":"http.request","target":"https://blocked.example.com"}'; echo
```

Expected output:

```text
{"status":"ok","environment":"RIF_Runtime","posture":"normal"}
{"current":"RIF_Runtime","environments":{...}}
{"agent":"agent:auditor",...}
{"decision":"allow",...,"matched_rule":"policy.allow_known_model_hosts",...}
{"decision":"deny",...,"posture":"elevated","matched_rule":"network.host.denied",...}
```

Stop the server:

```bash
kill "$PID"
```

For a single policy evaluation without running a server at all, use the CLI
directly — this is the lighter-weight path most PRs touching `policy.py`
actually want:

```bash
rif check "agent:test" "http.request" "https://api.anthropic.com/v1/messages"   # → decision: allow
rif check "agent:test" "http.request" "https://blocked.example.com"             # → decision: deny, posture: elevated
```

Both print the full `PolicyDecision` as JSON to stdout.

Note: every run against a real `RIFRuntime()` (server or CLI) appends to
`data/decisions.jsonl` and `data/posture_history.jsonl` as a side effect —
these are gitignored, so this is expected and harmless.

## Capability Layer (direct invocation)

`src/rif_runtime/execution/` (`ExecutionKernel`, `ExecutionManifest`,
`ExecutionResult`) plus `src/rif_runtime/capabilities/` (`Capability`,
`CapabilityRegistry`, the built-in `EchoCapability`) is a second, **separate**
execution path from the one above. It is not reachable through `rif serve` or
the `rif` CLI today — `ExecutionKernel`/`ExecutionManifest`/`CapabilityRegistry`
are not imported anywhere in `api.py`, `runtime.py`, or `cli.py`. The only way
to drive it is direct Python invocation, which is what this section documents.
This is the seam any future capability adapter (e.g. a Hugging Face inference
provider) registers into — see `.claude/skills/run-rif-runtime/drive_capability_layer.py`.

```bash
python .claude/skills/run-rif-runtime/drive_capability_layer.py
```

Expected output:

```text
policy decision: allow (allowed by constraints)
execution status: succeeded
execution output: {"actor": "agent:demo", "action": "ping", "parameters": {"payload": "hello from the run-skill driver"}}
---
policy decision: deny (runtime locked)
execution skipped: policy denied
---
CapabilityNotFoundError (expected): Unknown capability: huggingface.infer
```

The script does three things, all worth reading before extending this layer:

1. **Policy-then-execute, wired manually.** `PolicyEngine.evaluate()` and
   `ExecutionKernel.execute()` are two independent calls in the script, not
   one governed call — `ExecutionKernel.execute()` on its own does **not**
   consult the policy engine; it only resolves the named capability from the
   registry and calls `.execute()` on it (`execution/kernel.py:20`). Skipping
   the `PolicyEngine.evaluate()` call and going straight to
   `kernel.execute()` will run an unauthorized capability with no gate at
   all. Always call `evaluate()` first and check `decision.decision ==
   Decision.allow` yourself, as the script does.
2. **Both policy outcomes are exercised, not just the happy path.**
   `run_allowed_echo()` raises if `Posture.normal` ever unexpectedly denies,
   and `run_locked_posture_denial()` demonstrates the deny path explicitly
   with `Posture.locked` — which `PolicyEngine.evaluate()` denies
   unconditionally as its first check, before any capability is resolved.
   Either function raising means the driver's own assumptions about the
   policy engine's behavior broke, not just that a demo printed the wrong
   line.
3. **What an unregistered capability looks like.** The third block shows
   `CapabilityNotFoundError: Unknown capability: huggingface.infer` — this is
   the exact, real error you get today for any capability that doesn't exist
   yet. Building an HF (or any other) provider adapter means writing a class
   satisfying `Capability` (`capabilities/capability.py`: a `name` property
   and an `execute(manifest) -> ExecutionResult` method) and passing an
   instance of it into `CapabilityRegistry([...])` — see `EchoCapability`
   (`capabilities/echo.py`) as the minimal working example. `register()`
   raises `ValueError: Capability already registered: <name>` on a duplicate
   name (registration is explicit and one-shot, not upsert).

## Run (human path)

```bash
rif serve   # → uvicorn with --reload, http://127.0.0.1:8000. Ctrl-C to stop.
```

Fine for interactive development; avoid it for scripted/agent-driven runs
because of the reload-worker stop issue described above.

## Test

```bash
pytest -q
```

`pytest -q` is the merge-gate test command; do not hard-code a passing count in this file — it drifts. On a clean install use Python 3.12+ (`pip install -e .` + `requirements-dev.txt`).

## Gotchas

- **`pip install -e .` silently no-ops on Python < 3.12.** `pyproject.toml`
  requires `>=3.12`. On Python 3.11.15 (this container's default `python3`),
  `pip install -e .` completes with no error — pip just doesn't resolve the
  package — and a subsequent `import rif_runtime` raises `ModuleNotFoundError`.
  Always check `python3 --version` first, or use `python3.12` explicitly.
- **`POST /v1/policy/evaluate` returns `503` (not `401`) if no control-plane
  key is configured at all**, and `401` if a key is configured but not
  supplied — `auth.py`'s `require_api_key` fails closed. `scripts/smoke.sh`
  never sends `X-API-Key`, so its policy-evaluate calls always fail
  (`401` once `RIF_CONTROL_PLANE_API_KEYS` is set, `503` before that) and the
  script aborts under `set -euo pipefail`. `.env.example` does not document
  `RIF_CONTROL_PLANE_API_KEYS` at all. Set the env var before launching the
  server, and call the authenticated route with `curl -H "X-API-Key: ..."`
  directly rather than via `smoke.sh` — see Run (agent path).
- **`rif serve`'s worker process evades `kill $!` and `pkill -f`.** Its
  `reload=True` spawns a child worker via WatchFiles/`multiprocessing.spawn`
  whose PID and cmdline don't match the parent launch invocation. Use
  `python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000`
  (no `--reload`) for any agent-driven launch instead — it runs as one
  process, and `kill $PID` actually stops it (confirmed via `curl` exit
  code 7 immediately after, and no leftover process in `ps aux`).
- **Action names matter for policy evaluation, not just hosts.** `rif check`
  and `/v1/policy/evaluate` require a real action string (e.g.
  `http.request`, `api.call`, `mcp.invoke`, `package.install`) — only these
  are treated as network actions and checked against `allowed_hosts`; other
  actions match on the literal target string instead of the parsed host.
