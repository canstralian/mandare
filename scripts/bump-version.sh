#!/usr/bin/env bash
# Bump version in pyproject.toml and src/rif_runtime/__init__.py atomically.
# Usage: ./scripts/bump-version.sh X.Y.Z
set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version>  (e.g. 0.2.3)" >&2
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

sed -i "s/^version=.*/version='${VERSION}'/" "$ROOT/pyproject.toml"
sed -i "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" "$ROOT/src/rif_runtime/__init__.py"

echo "Bumped to $VERSION in pyproject.toml and __init__.py"
echo "Now run: pip install -e . && pytest -q"
