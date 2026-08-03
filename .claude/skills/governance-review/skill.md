---
name: governance-review
description: Review capabilities, providers, execution paths, and policy enforcement to ensure every effectful operation remains governed, auditable, and replayable.
---

# Governance Review

## Mission

Protect the Governance Plane.

Every effectful operation performed by the runtime must pass through explicit governance before execution.

No execution path may bypass policy evaluation.

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

Intent

↓

Planner

↓

Capability Resolution

↓

Policy Evaluation

↓

Execution

↓

Evidence

↓

Replay

↓

Receipts

Every execution must follow this sequence.

---

## Required Capability Properties

Every capability must define:

- unique name
- resource kind
- effect type
- replayable status
- description

Capabilities must be deterministic.

---

## Policy Rules

Policy evaluates.

Providers execute.

Execution never performs policy decisions.

Policy decisions must be explicit.

---

## Effect Classification

Every operation must declare an effect.

Supported effects include:

- READ
- WRITE
- SNAPSHOT
- INVENTORY
- PROJECT
- RENDER

Adding a new effect requires architectural review.

---

## Provider Review

Providers:

- perform work
- return results
- emit receipts

Providers never:

- own policy
- mutate evidence
- bypass governance

---

## Evidence Requirements

Every governed effect records:

- execution identifier
- capability
- provider
- resource
- timestamp
- policy decision
- outcome

Evidence is immutable.

---

## Replay Requirements

Replay must reproduce:

- capability
- policy decision
- inputs
- outputs
- receipts

Replay must never modify historical evidence.

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

Approve only implementations that preserve explicit governance, deterministic execution, immutable evidence, and replayability.

Every governed effect must be explainable, auditable, and reproducible.
