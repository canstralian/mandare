# spec/skill

Contract for the skill package format — the self-contained, versioned, testable
unit that packages a declarative procedure from existing governed capabilities.
The package surface remains `SKILL.md` + `skill.yaml` + `scripts/` +
`references/` + `tests/`, per ADR-0008.

**Draft — implementation-backed, not yet normative.** The first machine-readable
contract is `contracts/skill_manifest.schema.json` and the executable planning
surface is `src/rif_runtime/skills/`. The runtime does not introduce a second
policy engine, admission model, evidence ledger, or replay store.

## Contract boundary

```text
skill.yaml / manifest
        |
        v
canonical JSON Schema validation
        |
        v
SkillManifest / SkillStep
        |
        v
deterministic planner
        |
        v
existing ExecutionManifest
        |
        v
existing RIFRuntime.execute_capability()
```

A Skill describes **procedure and composition**. A Capability describes an
**effect the runtime may permit**. Policy and admission remain owned by the
existing runtime path. Manifest membership never implies authorization.

## Type and collection rules

- `dataclass(frozen=True, slots=True)` defines immutable domain records.
- `tuple` represents replay-relevant ordered collections.
- `Mapping` is the read-only interface for keyed payloads.
- `dict` and `list` may be used while constructing or crossing an existing
  execution boundary; Skill-owned payloads are recursively frozen first.
- `set` is internal to dependency resolution only and must not define observable
  ordering.
- `Any` is restricted to extension payloads such as `parameters` and
  `metadata`; it is not permitted for identity, version, dependency, ordering,
  or authorization fields.

## Identifier grammar

Skill IDs:

```regex
^[a-z0-9][a-z0-9-]{0,63}$
```

Step IDs:

```regex
^[a-z][a-z0-9_]{0,63}$
```

These expressions provide lexical checks only. Semantic contract validation is
owned by the canonical schema and existing contract test machinery.

## Deterministic planning

The planner must reject duplicate step IDs, self-dependencies, missing
dependencies, and cycles. When multiple steps are ready, it uses stable lexical
`(step_id, capability_id)` ordering. The result is a tuple, making the planned
order explicit and replay-stable.

## Validation ownership

There is one validation regime:

```text
canonical JSON Schema / existing contract validation
                 |
                 +--> implementation data classes
                 |
                 +--> conformance fixtures
```

The Python regex predicates are lexical helpers, not a competing schema
validator. No Skill-specific policy or admission validator is introduced.

The schema is fail-closed: `additionalProperties: false` rejects undeclared
contract fields and `schema_version` is fixed to `rif.skill-manifest/v0.1`.

## Promotion gate

This draft becomes normative only after schema conformance, planner edge-case,
execution delegation, deterministic replay, and contract-hash checks pass and
the specification is ratified under the repository's existing review process.
