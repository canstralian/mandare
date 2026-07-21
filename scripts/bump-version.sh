#!/usr/bin/env bash
# Bump the package version in pyproject.toml (the single source of truth).
# Uses Python for the substitution (avoids GNU vs BSD sed -i incompatibility).
# Usage: ./scripts/bump-version.sh X.Y.Z
set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version>  (e.g. 0.2.3)" >&2
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 - "$ROOT" "$VERSION" <<'PYEOF'
import re
import sys
from pathlib import Path

root, version = Path(sys.argv[1]), sys.argv[2]

p = root / "pyproject.toml"
p.write_text(re.sub(r"version='[^']*'", f"version='{version}'", p.read_text()))
PYEOF

echo "Bumped to $VERSION in pyproject.toml"
echo "Now run: pip install -e . && pytest -q"
