# Contributing

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

## Checks

Run the same checks CI runs before opening a pull request:

```bash
ruff check src tests
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

## Branches

- `main` is the only long-lived branch; develop every change on a short-lived
  branch (`feature/*`, `fix/*`, `docs/*`, …) and merge via pull request.
- Delete your branch after merge. See
  [docs/BRANCH_CLEANUP.md](docs/BRANCH_CLEANUP.md) for the post-release
  cleanup procedure and `scripts/cleanup_branches.sh` for the scripted path.

## Pull Requests

- Keep changes focused; unrelated cleanup belongs in a separate PR.
- Fill out the PR template, including the Governance Impact section if your
  change affects policy evaluation, allow/deny decisions, or audit behavior.
- Add or update tests for any behavior change.

## Reporting Security Issues

Do not open a public issue. See [SECURITY.md](SECURITY.md) for how to report
vulnerabilities privately.
