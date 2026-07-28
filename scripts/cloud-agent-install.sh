#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for RIF Runtime.
#
# Why this exists: `python3 -m venv` requires the `python3.12-venv` / ensurepip
# system packages. Some Cursor Cloud images omit them, and restricted egress
# can block `apt-get` from archive.ubuntu.com — leaving a broken `.venv`
# skeleton (python symlinks only, no pip/activate). Prefer stdlib venv when
# ensurepip works; otherwise fall back to PyPI `virtualenv` (pypi.org is
# typically allowlisted).
set -euo pipefail

cd "$(dirname "$0")/.."

need_venv=0
if [[ ! -x .venv/bin/python || ! -x .venv/bin/pip ]]; then
  need_venv=1
fi

if [[ "$need_venv" -eq 1 ]]; then
  rm -rf .venv
  if python3 -c 'import ensurepip' 2>/dev/null; then
    python3 -m venv .venv
  else
    python3 -m pip install --user --upgrade virtualenv
    export PATH="${HOME}/.local/bin:${PATH}"
    virtualenv .venv
  fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
