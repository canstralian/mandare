# Release Engineering Guide

This guide describes the release process that exists in the repository. It deliberately does not describe signing, SBOM, provenance, or reproducible-build controls as if they were already implemented.

## Versioning

The package declares its version in `pyproject.toml`. The release workflow verifies that a pushed `vX.Y.Z` tag matches the installed package version before building.

Release candidates use tags such as `v0.3.0rc2` and are published as GitHub prereleases by the current workflow.

## Current release flow

The repository's `.github/workflows/release.yml` performs:

1. checkout;
2. locked development dependency installation;
3. tag/package version consistency check;
4. Ruff, mypy, pytest, and replay verification;
5. Python package build;
6. GitHub Release publication with generated release notes.

That is the current release automation. It is not a complete software-supply-chain attestation system.

## Current artefacts

The release workflow publishes the files produced by `python -m build`.

The repository does not currently claim that release artefacts are:

- cryptographically signed;
- accompanied by an SBOM;
- reproducibly rebuilt from independent environments;
- covered by a verified SLSA-style provenance chain.

Those are future hardening items.

## Release checklist

Before tagging:

```text
- [ ] Version in pyproject.toml is intentional
- [ ] Relevant tests and security checks are green
- [ ] Documentation reflects the intended release state
- [ ] Breaking changes are documented
- [ ] Persistence/replay compatibility has been considered
- [ ] Open specification reviews do not conflict with the release
- [ ] Release notes distinguish implemented controls from planned work
```

After tagging, verify the exact GitHub Actions run and the resulting release assets. Do not infer a successful release from the existence of the workflow file alone.

## Rollback

For an application deployment, retain the previous known-good version and persistent-state backup before upgrading. Test the rollback path in the deployment environment rather than assuming package rollback also reverses state migrations.

RIF currently has local JSON/JSONL persistence and does not ship a general database migration framework. Any future schema migration must therefore define compatibility and recovery explicitly.

## Compatibility

At minimum, release review should consider:

- Python/runtime compatibility;
- HTTP API compatibility;
- CLI compatibility;
- persisted decision/posture format;
- replay semantics;
- policy configuration;
- specification contracts.

## Future release assurance

The enterprise release-hardening backlog should add:

1. SBOM generation and publication;
2. signed release artefacts;
3. verifiable build provenance;
4. reproducible-build checks;
5. documented cryptographic verification for consumers.

Until those controls exist and are verified, release documentation should remain conservative.
