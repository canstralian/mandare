# Specification and Contract Tree

`spec/` contains versioned contract material for RIF/AgentOS. Specifications are **not automatically implementation guarantees**. A schema may be seeded, drafted, placeholder, approved, or implemented only in part.

The Python runtime under `src/rif_runtime/` is the source of truth for shipped behaviour. A specification becomes an implementation contract only when its status, tests, and integration path make that relationship explicit.

## Contract domains

| Domain | Current status | Meaning |
|---|---|---|
| `capability/` | Seeded | Capability contract material; verify implementation coverage before relying on it |
| `governance/` | Seeded | Governance/posture contract material |
| `evidence/` | Seeded | Evidence/observation contract material |
| `replay/` | Placeholder | Replay contract not yet fully extracted as a normative schema |
| `skill/` | Placeholder | Skill package format not yet formalized |
| `state/` | Placeholder | Structured runtime-state contract not yet formalized |
| `mcp/` | Drafted | MCP governance contract material |

> **Known gap — the seeded domains are duplicates, not migrations.** ADR-0008 calls
> for the `contracts/rif_familiar/` schemas to be *migrated rather than duplicated*.
> What is in the tree today is duplication: the three schemas are byte-identical
> between `contracts/rif_familiar/` and `spec/`, and
> `tests/test_rif_familiar_contracts.py` validates only the `contracts/` copies — so
> the `spec/` copies carry no test coverage and can drift silently. Until the
> re-export-vs-retire question is settled, treat `contracts/rif_familiar/` as the
> tested copy. See `docs/SPECS_DOCS_AUDIT.md` (H3).

## Specification-review rule

Cross-domain contract changes should be reviewed before implementation when they affect authority, identity, capability scope, evidence, replay, provider egress, or another shared boundary.

The purpose is to avoid two individually plausible implementations that disagree at the seam.

## Open reviews

| Review | Governs | Status |
|---|---|---|
| `docs/spec-review-identity-spine-migration.md` | Identity hierarchy and run/aggregate semantics | Check document for current approval state |
| `docs/spec-review-capability-snapshot-authority.md` | Capability observation, replay, MCP authority | Draft / review required before conflicting implementation |

The review documents themselves are authoritative for their review status; this index should not be treated as a substitute for reading them.

## Contract-change checklist

Before changing a contract:

- identify all current consumers;
- inventory fixtures and persisted examples;
- define compatibility and migration semantics;
- define replay/recovery impact;
- define security/authority impact;
- update tests;
- update implementation-backed documentation;
- close or supersede conflicting specification reviews.

## Vocabulary discipline

Use **specification** for an intended contract, **implementation** for shipped code, and **evidence** for a verified observation. Do not use one as a synonym for another.
