#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for RIF Runtime.
#
# Why this exists: `python3 -m venv` requires the `python3.12-venv` / ensurepip
# system packages. Some Cursor Cloud images omit them, and restricted egress
# blocks `apt-get` from archive.ubuntu.com — so a bare `python3 -m venv` leaves
# a broken `.venv` skeleton (python symlinks only, no pip/activate).
#
# Strategy (allowlisted sources only — no apt):
#   1. Reuse a healthy `.venv` (python + pip present)
#   2. Stdlib `venv` if ensurepip works
#   3. Already-installed `virtualenv` (module or CLI)
#   4. Bootstrap `virtualenv` via system pip (`python3 -m pip install --user`)
#      then create `.venv`
set -euo pipefail

cd "$(dirname "$0")/.."

# Prefer the system interpreter for bootstrap so a broken/partial `.venv` on
# PATH cannot shadow pip/virtualenv during recovery.
SYS_PYTHON="${RIF_SYS_PYTHON:-/usr/bin/python3}"
if [[ ! -x "$SYS_PYTHON" ]]; then
  SYS_PYTHON="$(command -v python3)"
fi

venv_healthy() {
  [[ -x .venv/bin/python && -x .venv/bin/pip ]]
}

create_with_stdlib_venv() {
  "$SYS_PYTHON" -c 'import ensurepip' 2>/dev/null || return 1
  "$SYS_PYTHON" -m venv .venv
  venv_healthy
}

create_with_existing_virtualenv() {
  if "$SYS_PYTHON" -c 'import virtualenv' 2>/dev/null; then
    "$SYS_PYTHON" -m virtualenv .venv
  elif command -v virtualenv >/dev/null 2>&1; then
    virtualenv .venv
  else
    return 1
  fi
  venv_healthy
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
  venv_healthy
}

ensure_venv() {
  if venv_healthy; then
    echo "cloud-agent-install: reusing healthy .venv"
    return 0
  fi

  echo "cloud-agent-install: creating .venv (broken or missing)"
  rm -rf .venv

  if create_with_stdlib_venv; then
    echo "cloud-agent-install: created .venv via stdlib venv"
    return 0
  fi

  if create_with_existing_virtualenv; then
    echo "cloud-agent-install: created .venv via existing virtualenv"
    return 0
  fi

  if bootstrap_virtualenv_via_pip; then
    echo "cloud-agent-install: created .venv via PyPI virtualenv (pip --user)"
    return 0
  fi

  echo "error: failed to create a usable .venv" >&2
  return 1
}

ensure_venv

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
