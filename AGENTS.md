# AGENTS.md

RIF Runtime is a pure-Python FastAPI service (`rif_runtime.api:app`) plus a Typer
CLI (`rif`). There is no database or external service. For architecture, layout,
conventions, and gotchas see `CLAUDE.md`; for how to build/run/test/drive the
service see `.claude/skills/run-rif-runtime/SKILL.md`.

## Cursor Cloud specific instructions

- Dependencies are installed into a virtualenv at `.venv` (gitignored). Activate
  it before running anything: `source .venv/bin/activate`. The startup update
  script keeps it in sync with `pip install -e .` + `requirements.txt` +
  `requirements-dev.txt` (`pyproject.toml` currently has empty `dependencies`).
- That bootstrap is defined in `.cursor/environment.json` (repo-owned) and runs
  `scripts/cloud-agent-install.sh` — the only supported install entrypoint.
  Flow: reuse a structurally valid `.venv` (python + pip + activate) → stdlib
  `venv` if `ensurepip` works → already-installed `virtualenv` → else
  `/usr/bin/python3 -m pip install --user virtualenv` and create `.venv` →
  install deps → acceptance gate (`import fastapi` / `rif_runtime`) and write
  `.venv/.rif-bootstrap-ok`. Do not rely on `apt-get install python3.12-venv`:
  many Cloud images omit `ensurepip`, and restricted egress blocks Ubuntu
  archives. PyPI is allowlisted; system pip is present even when `ensurepip`
  is not. Prefer linking docs to this script over copying shell snippets.
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
