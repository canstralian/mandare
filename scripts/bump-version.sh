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
text = p.read_text()
new_text, n = re.subn(r"^version='[^']*'", f"version='{version}'", text, flags=re.MULTILINE)
if n != 1:
    raise SystemExit(f"Expected exactly 1 version= line in {p}, found {n}")
p.write_text(new_text)
PYEOF

pip install -e "$ROOT" -q
echo "Bumped to $VERSION, metadata refreshed."
echo "Now run: pytest -q"
