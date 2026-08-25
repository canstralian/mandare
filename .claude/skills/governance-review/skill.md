---
name: governance-review
description: Review capabilities, providers, execution paths, and policy enforcement to ensure every effectful operation remains governed, auditable, and replayable.
---

# Governance Review

## Mission

Protect the Governance Plane.

Every effectful operation performed by the runtime must pass through explicit governance before execution.

"No execution path may bypass policy evaluation" is the **standard this review enforces**, not a structural property of the code. `RIFRuntime.execute_capability` (`src/rif_runtime/runtime.py:179`) is the governed path; `ExecutionKernel.execute` (`src/rif_runtime/execution/kernel.py:20`) and `Capability.execute` perform no policy evaluation and can be called directly. Treat a new production caller of either as a blocking finding.

---

## Responsibilities

Review:

- Capability descriptors
- Policy decisions
- Provider integrations
- Execution plans
- Effect classification
- Evidence generation
- Replay compatibility

---

## Governance Pipeline

### Implemented today

Policy request

↓

Policy evaluation (`policy.py:75`)

↓

Decision (deny → evidence → return `DENIED`)

↓

Capability admission (`capabilities/registry.py`)

↓

Execution (`execution/kernel.py`)

↓

Evidence append (`capability_evidence_store`)

↓

Replay / inspection (`replay.py`)

This is the sequence in `RIFRuntime.execute_capability`. It is reachable from the Python API only — there is no HTTP route and no CLI command for capability execution. Do not document one as existing.

### Not implemented

**Planner** and **Receipts** appear in design material but have no implementation in `src/` and no tests. Do not review a change as though either stage exists, and do not describe them as shipped behaviour.

---

## Required Capability Properties

The executable interface (`capabilities/capability.py`) requires a unique `name` and an `execute(manifest)`. The governance identity travels alongside it as a `CapabilityRecord` (`capabilities/models.py`): id, name, description, provenance, integrity, permissions, dependencies, lifecycle, evaluations, metadata. `RIFRuntime.register_capability` takes both.

Resource kind, effect type, and replayable status are **design** fields in specification material, not fields on `CapabilityRecord` today. Review against the schema that exists; flag a change that persists a field the schema does not define.

Prefer capabilities whose output depends only on the manifest. Where that does not hold, the change must say so.

---

## Policy Rules

Policy evaluates.

Providers execute.

Execution never performs policy decisions.

Policy decisions must be explicit.

---

## Effect Classification — Design

Effect classification (READ, WRITE, SNAPSHOT, INVENTORY, PROJECT, RENDER) is specification material under `spec/capability/`. It is **not** enforced by `CapabilityRecord` or by `PolicyEngine.evaluate` today.

What policy actually keys on is the request's `action` string, with `NETWORK_ACTIONS` (`http.request`, `api.call`, `mcp.invoke`, `package.install`) receiving host-allowlist treatment (`policy.py:13`). Review effect-classification changes as contract work under `spec/README.md`, not as a live enforcement path, and do not assume non-network action names are host-checked.

---

## Provider Review

Providers:

- perform work
- return results

Receipt emission appears in provider design material but is **not implemented**
(see *Not implemented* above). Do not review a provider change as though it
emits receipts today.

Providers never:

- own policy
- mutate evidence
- bypass governance

---

## Evidence Requirements

`execute_capability` records, on both the denied and completed paths: `event`, `manifest_id`, `capability`, and the full `policy_decision`; the completed path adds `capability_status` and the execution result with `completed_at`.

Evidence is written **append-only** through `JsonlStore` (`storage/jsonl.py`), and `audit.py` provides hash-chain primitives that make tampering *detectable*. Nothing makes it immutable on disk. Do not write "immutable" or "tamper-proof" into documentation — `docs/README.md` bars both without a narrowly defined, supported claim.

Reject changes that edit, truncate, or rewrite an evidence or decision log.

---

## Replay Requirements

`replay.py` reconstructs runtime state from `decisions.jsonl` without writing back, and posture restoration across restart is covered by `tests/test_runtime_restart.py` and `tests/test_runtime_restore.py`.

Replay must never modify historical evidence. Receipt replay does not exist — do not review against it.

---

## Review Checklist

Reject changes that:

- bypass Governance
- perform writes without policy
- hide provider behaviour
- omit evidence
- weaken replay
- duplicate capability names
- introduce implicit permissions

---

## Required Outputs

Produce:

Governance Summary

Capability Review

Policy Review

Evidence Review

Replay Review

Risk Assessment

---

## Success Criteria

Approve only implementations that preserve explicit governance, append-only evidence, and replayability, and that keep the policy decision recorded alongside every governed effect.

Distinguish what the change *implements* from what it *specifies*, and use the status vocabulary in `docs/README.md`.

A governance review is evidence, not authorization. It does not approve a merge.
