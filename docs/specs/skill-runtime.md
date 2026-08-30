# Skill Runtime Contract

**Status:** Draft — additive implementation contract.

## 1. Boundary

A Skill is a versioned declarative procedure composed from existing governed
capabilities. A Skill does not introduce a second policy engine, admission
model, evidence ledger, or replay store.

The execution boundary remains:

```text
Skill Manifest
  -> deterministic planner
  -> existing ExecutionManifest
  -> existing PolicyEngine
  -> existing CapabilityRegistry admission
  -> existing ExecutionKernel
  -> existing evidence/audit stores
```

Manifest exposure is never authorization. Capability resolution/admission is
never implied by a Skill step.

## 2. Canonical data model

```python
@dataclass(frozen=True, slots=True)
class SkillStep:
    step_id: str
    capability_id: str
    depends_on: tuple[str, ...] = ()
    kind: SkillStepKind = SkillStepKind.capability
    parameters: Mapping[str, Any] = ...
    metadata: Mapping[str, Any] = ...

@dataclass(frozen=True, slots=True)
class SkillManifest:
    schema_version: str
    skill_id: str
    version: str
    description: str
    steps: tuple[SkillStep, ...]
    metadata: Mapping[str, Any] = ...
```

### Collection rules

- `tuple` is used for immutable ordered collections that participate in replay.
- `Mapping` is the public read-only interface for keyed payloads.
- `dict` is permitted at existing execution boundaries; Skill payloads are
  frozen internally and thawed only when handed to the existing executor.
- `list` is permitted as a local mutable accumulation buffer; replay-relevant
  ordered results are converted to tuples.
- `set` is internal to dependency resolution and must never become a source of
  externally observable ordering.
- `Any` is restricted to extension payloads (`parameters` and `metadata`). It
  must not be used for identifiers, versions, dependencies, ordering, or
  authorization fields.

## 3. Identifier grammar

Skill identifiers use:

```regex
^[a-z0-9][a-z0-9-]{0,63}$
```

Step identifiers use:

```regex
^[a-z][a-z0-9_]{0,63}$
```

Regex performs lexical validation only. Semantic validation remains owned by
the canonical schema and existing contract machinery.

## 4. Deterministic planning

`topological_order()` is the sole planning primitive in this draft. It:

1. rejects duplicate step identifiers;
2. rejects self-dependencies;
3. rejects missing dependencies;
4. resolves dependency edges using sets internally;
5. uses lexical `(step_id, capability_id)` ordering as a stable tie-breaker;
6. returns a tuple;
7. rejects cycles.

This prevents Python mapping insertion order, scheduler timing, or incidental
collection ordering from becoming replay semantics.

## 5. Execution semantics

For each planned step:

```text
construct ExecutionManifest
        |
        v
existing RIFRuntime.execute_capability()
        |
        +--> existing PolicyEngine
        |
        +--> existing CapabilityRegistry admission
        |
        +--> existing ExecutionKernel
        |
        +--> existing evidence/audit path
```

A failed or denied step terminates the Skill. Later steps are not dispatched.
No Skill-specific authorization shortcut exists.

## 6. Replay

The Skill layer contributes only deterministic planning inputs and stable step
metadata. The existing persisted decision and execution records remain the
source of truth for replay.

A future normative Skill replay contract must define canonical serialization and
hash boundaries before Skill manifests themselves become replay fixtures.
Until then, this implementation is deliberately additive and does not alter
the existing replay algorithm.

## 7. Validation ownership

There is one validation regime:

```text
canonical JSON Schema / existing contract validation
                 |
                 +--> implementation data classes
                 |
                 +--> conformance fixtures
```

The Python regex helpers are lexical predicates, not a competing schema
validator. Runtime orchestration does not duplicate canonical contract
validation.

Unknown top-level or step fields are rejected by
`contracts/skill_manifest.schema.json` via `additionalProperties: false`.
The schema also fixes `schema_version` to `rif.skill-manifest/v0.1`, so an
unknown version fails closed instead of being interpreted optimistically.

## 8. Promotion gate

This draft becomes normative only after:

- schema conformance tests pass;
- planner tests cover duplicate, missing, self, and cyclic dependencies;
- execution tests prove delegation to the existing capability path;
- replay fixtures prove deterministic ordering;
- contract hashes are regenerated;
- the specification is ratified under the repository's existing Track B
  process.
