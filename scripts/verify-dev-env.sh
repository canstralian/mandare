#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv-test

source .venv-test/bin/activate

python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt

python -m compileall src

pytest -q

mypy src
