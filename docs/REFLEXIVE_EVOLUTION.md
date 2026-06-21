# Reflexive Evolution Pipeline

## Purpose

RIF Runtime is designed to govern intelligent action, not merely execute it. The Reflexive Evolution Pipeline defines how the runtime observes failures, proposes bounded repair, verifies changes, and accumulates evidence without allowing ungoverned self-modification.

## Control loops

RIF separates adaptation into three loops:

1. **Self-healing** restores an expected operating state through bounded, reversible actions.
2. **Learning** captures diagnosis, evidence, repair outcomes, and confidence for future retrieval.
3. **Evolution** changes policies, adapters, workflows, or architecture only through explicit review and promotion controls.

These loops must remain independently inspectable. A model error must not be able to silently become a policy change.

## Pipeline

```text
Observe
  -> Diagnose
  -> Classify
  -> Plan repair
  -> Policy gate
  -> Sandbox test
  -> Apply or propose
  -> Verify
  -> Record evidence
  -> Learn
  -> Promote evolution only when thresholds pass
```

Every stage emits a typed, durable record.

```text
FailureEvent
  -> EvidencePacket
  -> Diagnosis
  -> RepairProposal
  -> PolicyDecision
  -> SandboxResult
  -> VerificationResult
  -> LearningRecord
  -> EvolutionProposal
```

## Autonomy levels

| Level | Capability | Default disposition |
| --- | --- | --- |
| L0 | Observe and record | Allowed |
| L1 | Diagnose and classify | Allowed |
| L2 | Propose a repair | Allowed |
| L3 | Test a repair in an isolated sandbox | Allowed for low-risk scopes |
| L4 | Open a pull request | Requires policy approval |
| L5 | Merge after review | Requires human approval |
| L6 | Autonomous merge | Not enabled in the MVP |

The MVP target is L0-L3.

## Repair constraints

A repair proposal must declare its target, scope, reversibility, expected verification, and fallback. Direct mutation of protected branches, policy suppression, secret handling, evidence deletion, and workflow disablement are denied by default.

```json
{
  "intent": "repair.workflow.bandit",
  "risk": "medium",
  "scope": [".github/workflows/bandit.yml"],
  "reversible": true,
  "verification": ["bandit -r src", "github_actions_run"],
  "fallback": "open_issue",
  "requires_human_approval": true
}
```

## Evidence and learning

Learning records are evidence, not authority. They may improve retrieval, triage, and proposal quality, but they do not alter policy automatically.

A minimum learning record includes:

- event type and source;
- normalized evidence references;
- root-cause hypothesis and confidence;
- proposed and applied repair;
- verification outcome;
- rollback outcome when applicable;
- reviewer approval or rejection.

## Evolution gate

An evolution proposal changes a policy, adapter, model, workflow, or evaluation baseline. It must include:

1. problem statement;
2. threat model;
3. proposed change;
4. test and evaluation plan;
5. rollback plan;
6. human approval requirement;
7. observation period and promotion criteria.

## Hugging Face Space boundary

A Hugging Face Space may host the RIF reference runtime and demo UI. It must not be treated as a trusted control plane. The Space may demonstrate intent evaluation, failure diagnosis, sandboxed repair planning, and evidence visualization. Credentials, production tools, and protected branch mutation remain outside the Space boundary.
