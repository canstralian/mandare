# Release Engineering — RIF Runtime

How we cut public releases. Companion docs:
[CHANGELOG.md](CHANGELOG.md), [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md),
[SECURITY.md](SECURITY.md).

## Current package version

Source of truth: `pyproject.toml` → `project.version` (today: **`0.3.0rc1`**).  
Runtime exposes it via `importlib.metadata` / `rif_runtime.__version__`.

**v1.0.0 is not tagged until** the release checklist below is green and
compatibility guarantees in `docs/COMPATIBILITY.md` are honest for what ships
in the tag (not only frozen specs).

## Release train (v1.0)

| Gate | Requirement |
| --- | --- |
| Contracts | `spec/events`, `spec/replay`, `spec/governance` GaC frozen and linked from README |
| Implementation | Event writer + deterministic replay + GaC evaluator **or** explicit “contracts-only / MVP subset” note in the tag notes |
| CLI | Either v1.0 demo CLI (`docs/cli-v1-spec.md`) or documented MVP CLI with migration map |
| Quality | `ruff check`, `ruff format --check`, `mypy`, `pytest` green on CI |
| Security | SECURITY.md matches real controls; no aspirational sandbox claims |
| Changelog | `CHANGELOG.md` `[Unreleased]` moved under `[1.0.0]` |
| Version | `scripts/bump-version.sh 1.0.0` (or equivalent) + `pip install -e .` |
| Classifier | `Development Status :: 5 - Production/Stable` only if support window applies |

## Tag and GitHub Release

1. Merge to `main`.
2. Bump version in `pyproject.toml` only (see CLAUDE.md version checklist).
3. Update `CHANGELOG.md` and `docs/releases/vX.Y.Z.md`.
4. Tag: `git tag -a v1.0.0 -m "v1.0.0"` and push tags.
5. `.github/workflows/release.yml` runs verify (`ruff`, `mypy`, `pytest`, `rif replay`) and creates a GitHub Release (rc tags → prerelease).

## Pre-release (rc) policy

- Use `X.Y.ZrcN` for candidates.
- rc builds may ship incomplete v1.0 CLI/engines **only if** release notes list non-goals.
- Breaking changes still require a major bump once `1.0.0` is published (see COMPATIBILITY.md).

## Artifacts

| Artifact | Producer |
| --- | --- |
| GitHub Release notes | `release.yml` + CHANGELOG |
| sdist/wheel | `python -m build` in release job (if enabled) |
| Container image | Optional; see `Dockerfile` / `README.Docker.md` — pin digest for production |

PyPI publish is **optional** and must be an explicit workflow addition with trusted publishing — not assumed for the first v1.0 GitHub tag.

## Rollback

1. Do not delete tags that others may have pinned; publish `1.0.1` fix or document “use `0.3.0rc1`”.
2. For bad images: retag previous known-good digest; never force-push `main` for release rollback.
3. Data: JSONL is append-only — restore from backup; do not rewrite history in place.

## Owner checklist (copy into PR)

- [ ] CHANGELOG updated
- [ ] COMPATIBILITY.md still accurate
- [ ] SECURITY.md claims verified against `src/`
- [ ] CI green on the release commit
- [ ] Tag message references CHANGELOG section
- [ ] Post-release: bump to next `.dev` / patch planning only if needed
