# Reflexive Evolution Pipeline

> **Status: design proposal.** This document describes a target governance model. The current runtime does not implement the full repair/evolution pipeline described below.

## Purpose

The proposal is to make adaptation explicit without allowing a model, diagnosis, or learned record to silently become authority.

The invariant is:

> **Observation can inform a proposal; only a governed decision can authorize a change.**

## Proposed loops

1. **Observation** — collect a failure or state signal.
2. **Diagnosis** — classify the signal and form a testable hypothesis.
3. **Proposal** — describe a bounded repair without applying it.
4. **Verification** — test the proposal under explicit policy constraints.
5. **Promotion** — apply an approved change only through an external governance path.

Learning may improve future proposals, but learned content is not policy authority.

## Proposed pipeline

```text
Observe
  -> Diagnose
  -> Classify
  -> Propose
  -> Policy gate
  -> Isolated verification
  -> Verify
  -> Record evidence
  -> Review / promote
```

The following names are **proposed contract vocabulary**, not a claim that every type currently exists in the runtime:

```text
Intent
PolicyDecision
FailureEvent
EvidenceRecord
Diagnosis
RepairProposal
SandboxResult
VerificationResult
LearningRecord
EvolutionProposal
```

## Proposed autonomy levels

| Level | Meaning | Proposed authority |
|---|---|---|
| L0 | Observe and record | No mutation |
| L1 | Diagnose/classify | No mutation |
| L2 | Propose a repair | No mutation |
| L3 | Test a repair in isolation | No production mutation |
| L4 | Open a change proposal | External review required |
| L5 | Apply an approved change | Human/governed approval required |
| L6 | Autonomous promotion | Explicitly out of scope for the current MVP |

These levels are a design vocabulary, not an enabled runtime capability matrix.

## Repair constraints

A future `RepairProposal` should declare at least:

- target and scope;
- expected effect;
- reversibility;
- verification criteria;
- fallback/rollback;
- required authority.

Protected-branch mutation, policy suppression, secret handling, evidence deletion, and disabling security controls should require explicit policy and human-controlled promotion.

## Evidence

A future evidence contract should distinguish:

- what was observed;
- what was inferred;
- what was proposed;
- what was actually changed;
- what verification established;
- who/what authorized promotion.

That distinction prevents a plausible model explanation from being mistaken for an observed fact.

## Evolution gate

A future `EvolutionProposal` should carry:

1. problem statement;
2. affected boundary;
3. threat model;
4. proposed change;
5. evaluation plan;
6. rollback plan;
7. approval requirement;
8. observation/promotion criteria.

## Current implementation boundary

The current repository already provides policy, posture, persistence, replay, audit primitives, and governed MCP surfaces. It does **not** currently implement the complete autonomous repair/evolution pipeline specified on this page.

Implementation should proceed only after the relevant contracts and fixture inventory are settled through the repository's specification-review process.
