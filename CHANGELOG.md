# Changelog

All notable changes to RIF Runtime are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
as defined in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## [Unreleased]

### Added

- Frozen v1.0 contracts: runtime event model (`spec/events`), deterministic replay
  (`spec/replay`), governance-as-code (`spec/governance/GOVERNANCE_AS_CODE.md`),
  and demo CLI design (`docs/cli-v1-spec.md`).
- CLI UX: help/epilogs, `--reload/--no-reload`, clearer errors, `rif status`,
  CliRunner tests.

### Changed

- Documentation honesty pass for release engineering (SECURITY, CONTRIBUTING,
  RELEASE, architecture diagram, compatibility guarantees).

### Deprecated

- Bare `PolicyDecision` JSONL as the long-term audit format (migrate to
  `rif.runtime.event/v1` envelopes for v1.0+).
- Inert wildcard policy rules skipped by the engine (express deny-default in GaC packs).

## [0.3.0rc1] - 2026-03-XX

### Added

- Control-plane API key auth (`X-API-Key` / `RIF_CONTROL_PLANE_API_KEYS`), fail-closed.
- Dry-run simulation for unauthenticated MCP evaluate/invoke (`record=False`).
- Metasploit MCP governance modes, capability tokens, evidence JSONL.
- Policy store CRUD (`/v1/policies`), environments, posture, graph/telemetry/audit summaries.
- Typer CLI: `serve`, `check`, `replay`, `msf-check`, `status`.
- Optional Supabase integration for `POST /v1/runs`.
- ADR-0008 AgentOS/RIF v1 architecture direction; resource contracts (ADR-0026).

### Fixed

- `POST /v1/posture/reset` no longer shadowed by `{posture}` path param.
- Replay JSONL decode errors report path and line.

### Security

- Constant-time API key compare; simulation routes cannot escalate posture anonymously.

## [0.2.2] - prior

See [docs/releases/v0.2.2.md](docs/releases/v0.2.2.md).

## [0.2.1] - prior

See [docs/releases/v0.2.1.md](docs/releases/v0.2.1.md).

## [0.2.0] - prior

See [docs/releases/v0.2.0.md](docs/releases/v0.2.0.md).

[Unreleased]: https://github.com/canstralian/rif-runtime/compare/v0.3.0rc1...HEAD
[0.3.0rc1]: https://github.com/canstralian/rif-runtime/releases/tag/v0.3.0rc1
