#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for RIF Runtime.
#
# Why this exists: `python3 -m venv` requires the `python3.12-venv` / ensurepip
# system packages. Some Cursor Cloud images omit them, and restricted egress
# blocks `apt-get` from archive.ubuntu.com — so a bare `python3 -m venv` leaves
# a broken `.venv` skeleton (python symlinks only, no pip/activate).
#
# Strategy (allowlisted sources only — no apt):
#   1. Reuse a structurally valid `.venv` (see venv_structurally_ok)
#   2. Stdlib `venv` if ensurepip works
#   3. Already-installed `virtualenv` (module or CLI)
#   4. Bootstrap `virtualenv` via system pip (`python3 -m pip install --user`)
#      then create `.venv`
#   5. Install project + deps, then acceptance gate (imports + marker)
#
# "Healthy" for reuse means structurally valid only; dependency completeness is
# enforced by the acceptance gate after pip installs (and by re-running pip on
# every bootstrap). A prior successful bootstrap is recorded in
# `.venv/.rif-bootstrap-ok`.
set -euo pipefail

cd "$(dirname "$0")/.."

MARKER=".venv/.rif-bootstrap-ok"
CREATE_PATH="unknown"

# Prefer the system interpreter for bootstrap so a broken/partial `.venv` on
# PATH cannot shadow pip/virtualenv during recovery.
SYS_PYTHON="${RIF_SYS_PYTHON:-/usr/bin/python3}"
if [[ ! -x "$SYS_PYTHON" ]]; then
  SYS_PYTHON="$(command -v python3)"
fi

# Structural readiness: enough to activate and run pip. Does NOT imply deps.
venv_structurally_ok() {
  [[ -x .venv/bin/python && -x .venv/bin/pip && -f .venv/bin/activate ]] || return 1
  # Interpreter must be the venv's, and pip must run (catches truncated envs).
  .venv/bin/python -c 'import sys; assert ".venv" in sys.prefix, sys.prefix'
  .venv/bin/pip --version >/dev/null
}

# Full acceptance: project and runtime deps importable.
venv_acceptance_ok() {
  .venv/bin/python -c 'import fastapi, uvicorn, pydantic, yaml, networkx, typer, rif_runtime'
}

write_bootstrap_marker() {
  local ensurepip_state path_state
  if "$SYS_PYTHON" -c 'import ensurepip' 2>/dev/null; then
    ensurepip_state="yes"
  else
    ensurepip_state="no"
  fi
  path_state="$CREATE_PATH"
  {
    echo "ok=1"
    echo "created_via=${path_state}"
    echo "ensurepip=${ensurepip_state}"
    echo "python=$("$SYS_PYTHON" -c 'import sys; print(sys.version.split()[0])')"
    echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$MARKER"
}

ensure_venv() {
  if venv_structurally_ok; then
    CREATE_PATH="reuse"
    echo "cloud-agent-install: reusing structurally valid .venv"
    return 0
  fi

  echo "cloud-agent-install: creating .venv (broken or missing)"
  rm -rf .venv

  if create_with_stdlib_venv; then
    CREATE_PATH="stdlib-venv"
    echo "cloud-agent-install: created .venv via stdlib venv"
    return 0
  fi

  if create_with_existing_virtualenv; then
    CREATE_PATH="existing-virtualenv"
    echo "cloud-agent-install: created .venv via existing virtualenv"
    return 0
  fi

  if bootstrap_virtualenv_via_pip; then
    CREATE_PATH="pypi-virtualenv"
    echo "cloud-agent-install: created .venv via PyPI virtualenv (pip --user)"
    return 0
  fi

  echo "error: failed to create a usable .venv" >&2
  return 1
}

create_with_stdlib_venv() {
  "$SYS_PYTHON" -c 'import ensurepip' 2>/dev/null || return 1
  "$SYS_PYTHON" -m venv .venv
  venv_structurally_ok
}

create_with_existing_virtualenv() {
  if "$SYS_PYTHON" -c 'import virtualenv' 2>/dev/null; then
    "$SYS_PYTHON" -m virtualenv .venv
  elif command -v virtualenv >/dev/null 2>&1; then
    virtualenv .venv
  else
    return 1
  fi
  venv_structurally_ok
}

bootstrap_virtualenv_via_pip() {
  if ! "$SYS_PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "error: system pip is unavailable at ${SYS_PYTHON}; cannot bootstrap virtualenv" >&2
    echo "error: image needs either ensurepip/python3-venv or a working system pip" >&2
    return 1
  fi
  "$SYS_PYTHON" -m pip install --user --upgrade virtualenv
  export PATH="${HOME}/.local/bin:${PATH}"
  "$SYS_PYTHON" -m virtualenv .venv
  venv_structurally_ok
}

ensure_venv

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
# Install runtime deps and the package (non-editable) first, then switch the
# package to editable so the source-tree path in _version.py resolves correctly.
# requirements.txt includes `.` so pip installs the package from the local tree;
# the follow-up `pip install -e . --no-deps` upgrades that to an editable link
# without reinstalling deps that are already satisfied.
pip install -r requirements.txt
pip install -e . --no-deps
pip install -r requirements-dev.txt

if ! venv_acceptance_ok; then
  rm -f "$MARKER"
  echo "error: bootstrap acceptance failed (runtime imports)" >&2
  exit 1
fi

write_bootstrap_marker
echo "cloud-agent-install: summary created_via=${CREATE_PATH} ensurepip=$("$SYS_PYTHON" -c 'import ensurepip' 2>/dev/null && echo yes || echo no) marker=${MARKER}"
