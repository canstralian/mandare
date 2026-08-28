# Documentation Guide

This directory contains implementation documentation, specifications, architecture proposals, operational runbooks, research, and historical decisions. They do not all have the same authority.

## Source-of-truth hierarchy

When two documents disagree, use this order:

1. **Executable implementation and tests** — what the current release actually does.
2. **Repository configuration/workflows** — what is configured, with run status verified separately.
3. **Normative specifications** — intended contracts that have been approved for implementation.
4. **Architecture/design documents** — proposals and target structures.
5. **Roadmaps, research, and notes** — plans, hypotheses, and future work.
6. **Historical ADRs/release notes** — records of past decisions or releases; they should not be silently rewritten to describe today's implementation.

A documentation page must not promote a lower-tier statement into a higher-tier guarantee.

## Core documents

| Document | Role | Status |
|---|---|---|
| `API.md` | Current HTTP route index | Implementation-backed |
| `cli-reference.md` | Current CLI commands | Implementation-backed |
| `contributor-handbook.md` | Review and contribution reasoning | Maintained guidance |
| `ROADMAP.md` | Planned work | Planning |
| `REFLEXIVE_EVOLUTION.md` | Reflexive architecture/design | Design |
| `DATA_MODEL.md` | Future persistence model | Specification/design |
| `MANDARE_MVP.md` | Current runtime summary | Maintained summary |
| `METASPLOIT_GOVERNANCE.md` | Metasploit governance boundary | Implementation-backed with deployment limitations |
| `mcp-integration-guide.md` | Generic MCP integration proposal | Planned/design |
| `plugin-capability-sdk-guide.md` | Future plugin SDK | Planned/design |
| `api-reference.md` | Historical planned API pointer | Legacy pointer |

## Architecture decisions and reviews

`docs/adr-*.md` and `docs/adr/` contain decision records. They preserve architectural history and should not be treated as a live feature list.

`spec-review-*.md` files are active contract-review material. Their status must be checked before implementing changes that cross the relevant boundary.

## Specifications

The [`../spec/`](../spec/) tree contains versioned contract material. Read [`../spec/README.md`](../spec/README.md) before changing cross-domain contracts.

## Research and evaluations

Research under `docs/research/` and evaluation material under `rif-evals/` are evidence inputs, not product guarantees. Experimental results should identify the task set, version, environment, and run when used to support a claim.

## Evidence language

Use precise status language:

- **Implemented** — present in executable code and supported by tests or direct inspection.
- **Configured** — present in repository configuration; successful execution still requires run evidence.
- **Specification** — contract/design, not necessarily implemented.
- **Planned** — intended future work.
- **Unverified** — insufficient evidence for a stronger statement.

Avoid words such as *complete*, *immutable*, *tamper-proof*, *enterprise-grade*, *production-ready*, *deterministic*, or *zero-trust* unless the specific claim is narrowly defined and supported by repository evidence.

## Generated material

`notebooklm/` is a non-canonical research/export area. Stale duplicate documentation snapshots have been removed; future generated material should either be regenerated from canonical sources or clearly marked as a snapshot.

Generated documentation bundles should not be committed unless their generation and refresh process is defined.

## Keeping documentation current

When code changes:

- update the closest implementation-backed document in the same change;
- remove obsolete command/API examples;
- distinguish new controls from proposed controls;
- avoid rewriting historical release notes;
- add a regression test when the documentation describes a security or governance property that could otherwise drift.

## Contributor entry points

Start with:

1. [`../README.md`](../README.md)
2. [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
3. [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
4. [`../SECURITY.md`](../SECURITY.md)
5. [`../DEVELOPMENT.md`](../DEVELOPMENT.md)
6. [`../SUPPORT.md`](../SUPPORT.md)
7. [`../CHANGELOG.md`](../CHANGELOG.md)

Then follow the specific API, CLI, specification, or roadmap document relevant to the change.
