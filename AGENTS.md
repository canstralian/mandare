# AGENTS.md

RIF Runtime is a pure-Python FastAPI service (`rif_runtime.api:app`) plus a Typer
CLI (`rif`). There is no database or external service. For architecture, layout,
conventions, and gotchas see `CLAUDE.md`; for how to build/run/test/drive the
service see `.claude/skills/run-rif-runtime/SKILL.md`.

## Cursor Cloud specific instructions

- Dependencies are installed into a virtualenv at `.venv` (gitignored). Activate
  it before running anything: `source .venv/bin/activate`. The startup update
  script keeps it in sync with `pip install -e .` + `requirements-dev.txt`.
- `python3 -m venv` requires the `python3.12-venv` system package. It is already
  present in the VM image; only reinstall it (`apt-get install -y python3.12-venv`)
  if venv creation ever fails on a fresh machine.
- CI (`.github/workflows/ci.yml`) gates on three commands, run in this order:
  `ruff check src tests`, `mypy src/rif_runtime --ignore-missing-imports`,
  `pytest -q`. `quality.yml` also enforces `ruff format .` — run all four before
  considering a change done. All 86 tests pass on a clean install.
- To run the server for agent-driven testing, launch uvicorn directly, NOT
  `rif serve`: `python -m uvicorn rif_runtime.api:app --host 127.0.0.1 --port 8000`.
  `rif serve` uses `--reload`, whose WatchFiles worker cannot be stopped with
  `kill $!` or `pkill -f` — the reload worker's PID and cmdline don't match the
  launch invocation, so those signals never reach it (see SKILL.md). The direct
  uvicorn process is a single PID that `kill` stops cleanly. Interactive Swagger
  UI is at `/docs`.
- Quick end-to-end check once the server is up:
  `BASE=http://127.0.0.1:8000 bash scripts/smoke.sh` (exercises an allow + a deny
  decision; the deny escalates posture to `elevated`). No server needed for a
  single decision: `rif check "agent:test" "http.request" "https://blocked.example.com"`
  for a deny, or substitute a real host (e.g. `https://api.anthropic.com/v1/messages`)
  to exercise the allow path when the active environment permits it.
- Only the four network actions — `http.request`, `api.call`, `mcp.invoke`,
  `package.install` (see `NETWORK_ACTIONS` in `src/rif_runtime/policy.py`) —
  trigger the `allowed_hosts` check. Any other action name (e.g. `fs.read`,
  `custom.thing`) skips the host check entirely, though other policy constraints
  (posture, wildcard rules, package/MCP gates) still apply. Pick the action name
  deliberately when writing checks or tests.
- Running any real `RIFRuntime()` (server, CLI, or most tests) appends to
  `data/decisions.jsonl` / `data/posture_history.jsonl` (both gitignored) —
  expected and harmless for `self.posture`, which always starts at `normal` on
  every new process (`RIFRuntime.__init__` does not replay history). What *does*
  accumulate across runs on a reused workspace is `decisions.jsonl` itself, and
  therefore anything derived from it: `/v1/audit`, `/v1/recovered-state`, and
  `rif replay` will reflect the full historical denial count and can show a
  `restricted` / `locked` "last posture" that has no bearing on the live
  runtime. If a test asserts on those endpoints, truncate the two files (or
  point them elsewhere) before the run.
