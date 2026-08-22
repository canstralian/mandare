# Changelog

This changelog records user- and contributor-relevant changes. It does not replace the detailed release notes under `docs/releases/`.

## Unreleased

### Documentation and governance

- Reworked the project overview to distinguish implemented behaviour from specification and planned work.
- Added a documentation source-of-truth hierarchy and evidence-language standard.
- Reconciled architecture, API, CLI, development, deployment, testing, release, dependency, security, and contributor documentation with the current repository.
- Replaced the placeholder security reporting contact with a private mailto reporting link.
- Added contributor support guidance and stronger issue/PR templates.
- Removed stale NotebookLM documentation snapshots and generated documentation bundles to reduce documentation drift.
- Removed orphaned duplicate ADR files.

### Security documentation

- Explicitly separated cryptographic primitives from claims about persisted evidence integrity.
- Documented current control-plane API-key authentication and its limitations.
- Documented dependency-lock and CI security controls without implying that workflow configuration proves successful execution.
- Documented remaining supply-chain gaps: SBOM, signed artefacts/provenance, and reproducible builds.

### Architecture

- Clarified that remote provider authorization remains specification work and that provider credentials are not RIF authority.
- Clarified the boundary between replay/reconstruction and proof of external side effects.

## Release history

See [`docs/releases/`](docs/releases/) for historical release notes.
