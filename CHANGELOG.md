# Changelog

This changelog records user- and contributor-relevant changes. It does not replace the detailed release notes under `docs/releases/`.

## Unreleased

### Fixed

- **Breaking (governance): wildcard policy rules are now evaluated.**
  `PolicyEngine.evaluate()` previously skipped every rule with
  `action: "*"` or `target: "*"`, which meant the shipped
  `deny_unknown_by_default` rule was loaded, returned by `GET /v1/policies`,
  and never applied — an unconfigured action fell through to `default.allow`.
  Wildcard rules now apply, so the default policy denies by default as it has
  always claimed to. Rules are evaluated most-specific-first, and catch-all
  (`"*"`/`"*"`) rules run after the environment constraints so a broad `allow`
  cannot disable the `allowed_hosts` allowlist. Actions that relied on the old
  fallthrough must now be permitted by an explicit rule; the MST eval harness
  is one such consumer and now declares an `allow` rule for `code.refine`.
  See "Policy evaluation order" in `docs/API.md`.

- **The OpenAPI document reports the real package version.** `api.py`
  hardcoded `version="0.3.0"` while the package was `0.3.0rc2`, so
  `/openapi.json` advertised a release the installed distribution was not. It
  now uses `__version__`, and a test fails if a literal is reintroduced.

- **`rif serve` no longer forces auto-reload.** Reload was hardcoded on, so the
  start command documented in the README quick start spawned uvicorn's
  file-watching supervisor even when serving for real. It is now `--reload`,
  off by default.
- **The production image installs the hash-pinned lock.** `Dockerfile` built
  from the deliberately unpinned `requirements.txt`, so the locked-toolchain
  discipline stopped at the image. It now installs
  `requirements/runtime.txt` with `--require-hashes` (which carries every
  `uvicorn[standard]` extra), adds a `HEALTHCHECK` against `/health`, and runs
  the installed `rif_runtime.api:app` rather than the `src.`-prefixed path that
  only resolved via implicit namespace packages.
- **Fixed the production compose healthcheck**, which invoked `curl` in a
  `python:slim` image that has no curl and could therefore only fail. Its
  environment block also set four variables nothing reads, including
  `RIF_SECURITY_SANDBOX_MODE: "strict"`.

- **The decision log is now hash-chained.** `audit.py` implemented the chain
  primitives from the start, but nothing in `src/` used them, so
  `decisions.jsonl` was append-only rather than tamper-evident. Decisions are
  now written through `HashChainedJsonlStore`; edits, deletions, reorderings and
  hand-spliced rows are detected. `GET /v1/audit` reports the result under
  `decision_chain`. Rows written before this change are reported as
  `unchained_leading`, never counted as verified. `SECURITY.md` documents what
  the property does and does not cover — notably that truncation can be
  rewritten into a shorter valid chain.

- **`.env.example` no longer documents configuration that does not exist.**
  It listed 58 variables, of which the runtime read 3. The 55 inert names
  included `RIF_SECURITY_SANDBOX_ENABLED`, `RIF_SECURITY_NETWORK_ISOLATION`,
  `RIF_SECURITY_CAPABILITY_DROP`, `RIF_AUTH_ENABLED` and `RIF_AUDIT_ENABLED` —
  settings that read as security controls while doing nothing — and it omitted
  the real `RIF_DATA_DIR`. The file now documents exactly what the code reads,
  and a test fails on any name nothing in `src/` references.

- **Security: governance-state read endpoints can now require authentication.**
  `/v1/audit`, `/v1/policies` (GET), `/v1/recovered-state`,
  `/v1/persistence/summary`, `/v1/telemetry/summary` and `/v1/graph/summary`
  return decision history and configured rules and were unauthenticated with no
  way to change that. Setting `RIF_REQUIRE_READ_AUTH=true` now guards them with
  the existing `X-API-Key` check. The flag defaults to off so existing read
  clients keep working; it is intended to become the default. `docs/API.md` also
  no longer claims `GET /v1/policies` is a guarded mutable operation.
- **A route-inventory test now fails CI on any new unguarded endpoint**, so the
  public surface has to be declared rather than defaulted into.

- **Governance: the configured posture now reaches the runtime.**
  `RIF_POSTURE` / `[runtime] posture` was parsed, validated, and never read, so
  a runtime configured `locked` started up allowing everything. It is now
  applied as a floor on the restored posture: configuration can tighten a
  runtime but never relax one. `POST /v1/posture/reset` still relaxes the
  running process, but the floor is re-applied on restart. Defaults are
  unchanged (`normal` is a no-op floor). `config.PostureLevel` is now
  `schemas.Posture` rather than a second identical enum.

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
