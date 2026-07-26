# AGENTS.md

RIF Runtime is a pure-Python FastAPI service (`rif_runtime.api:app`) plus a Typer
CLI (`rif`). There is no database or external service. For architecture, layout,
conventions, and gotchas see `CLAUDE.md`; for how to build/run/test/drive the
service see `.claude/skills/run-rif-runtime/SKILL.md`.

## Cursor Cloud specific instructions

- Dependencies are installed into a virtualenv at `.venv` (gitignored). Activate
  it before running anything: `source .venv/bin/activate`. The startup update
  script keeps it in sync with `pip install -e .` + `requirements-dev.txt`.
- That bootstrap is defined in `.cursor/environment.json` (repo-owned), so setup
  uses `python3` explicitly and does not depend on the base image providing a
  bare `python` alias.
- `python3 -m venv` requires the `python3.12-venv` system package. It is already
  present in the VM image; only reinstall it (`apt-get install -y python3.12-venv`)
  if venv creation ever fails on a fresh machine.
- CI (`.github/workflows/ci.yml`) gates on three commands, run in this order:
  `ruff check src tests`, `mypy src/rif_runtime --ignore-missing-imports`,
  `pytest -q`. `quality.yml` also enforces `ruff format .` — run all four before
  considering a change done. All 86 tests pass on a clean install.
- To run the server for agent-driven testing, launch uvicorn directly, NOT
  `rif serve`: `python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000`.
  `rif serve` uses `--reload`, which spawns a WatchFiles worker whose PID/cmdline
  don't match the launch invocation, so `kill $!` and `pkill -f` fail to stop it;
  the direct uvicorn process is a single PID that `kill` stops cleanly (see
  SKILL.md). Interactive Swagger UI is at `/docs`.
- Quick end-to-end check once the server is up:
  `BASE=http://127.0.0.1:8000 bash scripts/smoke.sh` (exercises an allow + a deny
  decision; the deny escalates posture to `elevated`). No server needed for a
  single decision: `rif check "agent:test" "http.request" "https://blocked.example.com"`.
  Action names matter: only real network actions (`http.request`, `api.call`,
  `mcp.invoke`, `package.install`) are checked against `allowed_hosts`.
- Running any real `RIFRuntime()` (server, CLI, or most tests) appends to
  `data/decisions.jsonl` / `data/posture_history.jsonl` (gitignored) — expected
  and harmless. Posture accumulates across runs, so a fresh checkout may already
  show non-`normal` posture from prior runs.
