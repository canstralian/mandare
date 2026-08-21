# Documentation Guide

This directory contains implementation documentation, specifications, architecture proposals, and working notes. They do not all have the same authority.

## Source-of-truth hierarchy

When two documents disagree, use this order:

1. **Executable implementation and tests** — what the current release actually does.
2. **Repository configuration/workflows** — what is configured, with run status verified separately.
3. **Normative specifications** — intended contracts that have been approved for implementation.
4. **Architecture/design documents** — proposals and target structures.
5. **Roadmaps and notes** — plans, hypotheses, and future work.

A documentation page must not promote a lower-tier statement into a higher-tier guarantee.

## Core documents

| Document | Role | Status |
|---|---|---|
| `API.md` | Current HTTP route index | Implementation-backed |
| `cli-reference.md` | Current CLI commands | Implementation-backed |
| `contributor-handbook.md` | Review and contribution reasoning | Maintained guidance |
| `ROADMAP.md` | Planned work | Planning |
| `REFLEXIVE_EVOLUTION.md` | Reflexive architecture/design | Design; verify status labels inside |
| `DATA_MODEL.md` | Data-contract design | Specification/design |
| `RIF_RUNTIME_MVP.md` | MVP implementation summary | Maintained summary |
| `api-reference.md` | Historical planned API pointer | Legacy pointer |

## Specifications

The [`../spec/`](../spec/) tree contains versioned contract material. Read [`../spec/README.md`](../spec/README.md) before changing cross-domain contracts.

Specification reviews under this directory are intentionally separate from implementation. An open review is not permission to implement a second interpretation concurrently.

## Evidence language

Use precise status language:

- **Implemented** — present in executable code and supported by tests or direct inspection.
- **Configured** — present in repository configuration; successful execution still requires run evidence.
- **Specification** — contract/design, not necessarily implemented.
- **Planned** — intended future work.
- **Unverified** — insufficient evidence for a stronger statement.

Avoid words such as *complete*, *immutable*, *tamper-proof*, *enterprise-grade*, *production-ready*, *deterministic*, or *zero-trust* unless the specific claim is narrowly defined and supported by repository evidence.

## Keeping documentation current

When code changes:

- update the closest implementation-backed document in the same change;
- remove obsolete command/API examples;
- distinguish new controls from proposed controls;
- avoid rewriting historical release notes;
- add a regression test when the documentation is describing a security or governance property that could otherwise drift.

## Contributor entry points

Start with:

1. [`../README.md`](../README.md)
2. [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
3. [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
4. [`../SECURITY.md`](../SECURITY.md)
5. [`../DEVELOPMENT.md`](../DEVELOPMENT.md)

Then follow the specific API, CLI, specification, or roadmap document relevant to the change.
