# Compatibility, versioning, and support

Normative for public releases of RIF Runtime. Release process: [RELEASE.md](../RELEASE.md).

## Semantic versioning rules

We follow [SemVer 2.0.0](https://semver.org/): `MAJOR.MINOR.PATCH` with optional
pre-release (`rcN`) and build metadata.

| Bump | When |
| --- | --- |
| **MAJOR** | Breaking change to a **compatibility-guaranteed** surface (below) |
| **MINOR** | Backward-compatible features; new optional fields/events/CLI commands |
| **PATCH** | Bug fixes, security patches, docs, non-behavioral refactors |

Pre-`1.0.0` (`0.y.z`): MINOR may include breaks; still document them in CHANGELOG.
**From `1.0.0` onward:** breaks require MAJOR.

### Compatibility-guaranteed surfaces (v1.x)

Once `1.0.0` is tagged, these are covered:

1. **HTTP API** routes and JSON shapes documented as stable in the release notes
   (baseline: evaluate, health, posture, policies, graph/telemetry summaries —
   exact freeze list ships in the `1.0.0` notes).
2. **Event envelope** `rif.runtime.event/v1` ([spec/events](../spec/events/SPEC.md)).
3. **Policy pack** `rif.runtime.policy/v1` and explanation schema.
4. **Replay report** `rif.runtime.replay-report/v1`.
5. **CLI exit codes** `0–5` as defined in [docs/cli-v1-spec.md](cli-v1-spec.md)
   for implemented v1 commands.
6. **Python** `requires-python` lower bound in `pyproject.toml` for that tag.

### Explicitly not guaranteed

- On-disk layout of legacy `data/decisions.jsonl` beyond a documented migration window.
- Unstable / experimental routes marked in docs.
- Optional extras (`supabase`) behavior when unset.
- Library modules not imported by `api` / published CLI (orphaned packages may move).
- Performance SLAs.

## Compatibility guarantees (runtime behavior)

| Guarantee | Meaning |
| --- | --- |
| Append-only audit | Supported event/decision logs are not updated in place by the runtime |
| Deterministic verify | Same canonical event JSONL + evidence store ⇒ same verify result on supported platforms |
| Fail-closed control plane | Missing API keys ⇒ guarded routes unavailable (503), not open |
| Schema versioning | Writers emit a `schema_version`; unknown **major** ⇒ readers reject |

Posture reconstruction for v1.0+ must follow the replay/event contracts (not
divergent live vs forensic algorithms). Until engines ship, `0.3.x` may still
exhibit the legacy divergence — called out in SECURITY/CHANGELOG.

## Deprecation policy

1. **Announce** in CHANGELOG under `### Deprecated` and, for public API/CLI, in
   release notes.
2. **Minimum window:** one MINOR release of warnings/docs before removal, or
   **90 days**, whichever is longer (after `1.0.0`).
3. **Removal** happens in the next **MAJOR** (or in MINOR only before `1.0.0`
   with loud notes).
4. Prefer adapters (e.g. legacy `rif replay <file>` beside `rif replay <run_id>`)
   during the window.
5. Spec supersession: new `schema_version` major; dual-read when feasible.

## Breaking-change process

1. Open a Track B issue/PR amending the relevant `spec/` (or ADR).
2. Land the spec before or with the implementation.
3. Bump **MAJOR**, update COMPATIBILITY if surfaces change, CHANGELOG `### Removed` / `### Changed`.
4. Provide migration notes (and tools when practical).
5. Tag only from `main` with CI green ([RELEASE.md](../RELEASE.md)).

Emergency security breaks may ship in a patch with a follow-up MAJOR if an API
must change; document clearly.

## Supported platforms

| Platform | Support |
| --- | --- |
| Python **3.12**, **3.13** | Supported (CI matrix intent) |
| Linux x86_64 (Ubuntu runners) | Primary CI / release verify |
| macOS, Windows | Best-effort for CLI/dev; CI may not cover every OS |
| PyPI package | Supported when published for that tag |
| Docker image | Best-effort; pin digests for production |

No guarantee for PyPy, Python ≤3.11, or end-of-life OS distros.

## Support window

| Line | Window |
| --- | --- |
| Current MAJOR (`1.x` after release) | Security + critical fixes for **at least 12 months** from `1.0.0`, or until `2.0.0` + 90 days — whichever is later |
| Previous MAJOR (`N-1.x`) | Security fixes for **90 days** after `N.0.0` (optional extended LTS announced per release) |
| Pre-1.0 (`0.x`) | Best-effort; no SLA |

Support means: accepted security reports and patch tags for the listed lines —
not free consulting or feature backports.
