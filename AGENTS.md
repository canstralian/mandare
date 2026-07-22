# AGENTS.md

## Cursor Cloud specific instructions

RIF Runtime is a pure-Python FastAPI service (`rif_runtime.api:app`) plus a Typer
CLI (`rif`). There is no build step, no database, and no external services — state
is JSONL/JSON files under `data/`.

Standard setup, run, test, lint, and type-check commands are already documented in
`CLAUDE.md` ("Development workflow") and `.claude/skills/run-rif-runtime/SKILL.md`.
Follow those; only the cloud-specific caveats below are worth repeating.

- A virtualenv already exists at `.venv/` and the update script keeps it in sync.
  Activate it before running anything: `source .venv/bin/activate`. The `rif`
  console script and all dev tools (`ruff`, `mypy`, `pytest`) live there.
- CI enforces three checks in order — run all before considering a change done:
  `ruff check src tests`, `mypy src/rif_runtime --ignore-missing-imports`,
  `pytest -q`. `ruff format .` is separately enforced; run `ruff format --check .`.
- To run the server for agent/scripted use, launch uvicorn directly, NOT `rif serve`:
  `python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000`. `rif serve`
  hardcodes `--reload`, which spawns a WatchFiles worker whose PID/cmdline don't
  match the launch invocation, so `kill $!` and `pkill -f` fail to stop it. The
  direct uvicorn process is a single PID that `kill` stops cleanly.
- Smoke test against a running server: `BASE=http://127.0.0.1:8000 bash scripts/smoke.sh`.
  It exercises health, environment listing, audit, and an allow/deny policy pair
  (the deny escalates posture to `elevated`).
- For a single policy decision without a server, use the CLI, e.g.
  `rif check "agent:test" "http.request" "https://api.anthropic.com/v1/messages"`.
  Action names matter: only real network actions (`http.request`, `api.call`,
  `mcp.invoke`, `package.install`) are checked against `allowed_hosts`.
- Every run against a real `RIFRuntime()` (server or CLI) appends to
  `data/decisions.jsonl` and `data/posture_history.jsonl` (both gitignored). This
  is expected; posture accumulates across runs, so a fresh checkout may already
  show non-`normal` posture from prior runs.
