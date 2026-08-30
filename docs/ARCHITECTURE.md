# RIF Runtime Architecture

```text
Intent
  ↓
Skill Manifest
  ↓
Deterministic Skill Planner
  ↓
Existing ExecutionManifest
  ↓
Policy Engine
  ↓
Capability Registry / Admission
  ↓
Execution Kernel
  ↓
Existing Evidence + Audit Stores
  ↓
Replay / Evaluation
```

The Skill layer is an orchestration layer, not a second governance plane.

## Trust Model

- Deny by default
- Environment governed execution
- Reflexive posture adaptation
- Persistent audit trail
- Skill exposure is not authorization
- Skill planning does not replace capability admission
- Skill execution delegates policy and evidence to the existing runtime

## Contract Ownership

```text
Canonical JSON Schema / existing contract validation
                    ↓
            Skill Manifest
                    ↓
        typed implementation models
                    ↓
       deterministic skill planner
                    ↓
       existing capability gate
```

There is intentionally no parallel Skill-specific policy or validation regime.
The Skill contract adds procedure composition while preserving the existing
runtime authority boundaries.

## Determinism Boundary

Skill dependencies are represented as tuples at the domain boundary. The
planner may use mutable dictionaries, lists, and sets internally, but converts
the final execution order to a tuple. Ready-node tie-breaking uses stable
lexical ordering, preventing insertion order or scheduler timing from becoming
part of replay semantics.

## Runtime Data Flow

For each step:

```text
SkillStep
  → ExecutionManifest
  → RIFRuntime.execute_capability()
  → PolicyEngine
  → CapabilityRegistry.admit()
  → ExecutionKernel
  → existing evidence/audit path
```

A denied or failed capability stops the Skill. No later step is dispatched.
