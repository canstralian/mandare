---
name: run-rif-runtime
description: Build, run, and drive RIF Runtime. Use when asked to start RIF Runtime, run its tests, build it, evaluate a policy decision, or interact with the running API.
---

RIF Runtime is a FastAPI service (`rif_runtime.api:app`) plus a Typer CLI
(`rif`). Drive it either over HTTP with `curl`/`scripts/smoke.sh` against a
running server, or directly via the `rif check` CLI subcommand, which
evaluates one policy request without needing a server at all.

## Prerequisites

No system packages beyond Python 3.11+ are required — this is a pure-Python
FastAPI + Typer project with no native deps.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

No build step — it's a plain installable Python package.

## Run (agent path)

Launch the server **without** `rif serve`. `rif serve` hardcodes
`uvicorn.run(..., reload=True)`, which makes WatchFiles fork a separate
worker process under `multiprocessing.spawn`. The worker's PID is not the
PID captured by `$!`, and its cmdline no longer contains the original
launch string — so both `kill $!` and `pkill -f "rif serve"` silently fail
to stop it (verified: curl to `/health` kept succeeding after both). Launch
uvicorn directly instead, which runs as a single process you can `kill`
cleanly:

```bash
python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000 > /tmp/rif.log 2>&1 &
PID=$!

for i in $(seq 1 30); do curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 0.5; done
curl -sf http://127.0.0.1:8000/health; echo
```

Then drive it with the project's own smoke script — it exercises health,
environment listing, audit, and both an allow and a deny policy decision
(the deny also escalates posture to `elevated`):

```bash
BASE=http://127.0.0.1:8000 bash scripts/smoke.sh
```

Expected output (last two lines show the allow/deny pair):

```
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

27 tests pass on a clean install.

## Gotchas

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
