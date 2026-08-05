# RIF Runtime Architecture

## Execution circuit (implemented)

```text
Transport (HTTP / CLI / …)
      ↓
RIFRuntime (composition root)
      ↓
PolicyEngine.evaluate()
      ↓
PolicyDecision
      ↓
GovernanceGraph.record_decision()
      ↓
ReflexiveLoop.observe() → Posture
      ↓
JsonlStore (decisions + posture transitions)
      ↓
Audit / telemetry / graph / recovered-state (via Runtime methods)
```

Trust Model:

- Deny by default
- Environment governed execution
- Reflexive posture adaptation
- Persistent audit trail

## Composition root

`RIFRuntime` (`src/rif_runtime/runtime.py`) owns the live collaborators used by
the evaluate circuit: policy engine, policy store, reflexive loop, governance
graph, decision/posture/evidence stores, Metasploit governor, and
`ReplayEngine`.

FastAPI (`api.py`) and Typer (`cli.py`) are **transports**: they authenticate,
parse, and serialize. They do not construct parallel replay engines or mutate
posture fields except through runtime methods. See
[ADR-0028](adr/ADR-0028-runtime-composition-root.md).

## Target architecture (roadmap)

Stages beyond the policy/governance circuit — Capability Router, Adapter Layer,
Execution, and EvidenceRecord as a full system — are sequenced in
[ROADMAP.md](ROADMAP.md). ADR-0008 describes the longer-term package layout
(`spec/`, control plane, evidence/replay systems); those moves are incremental
and must not invent parallel aggregates.
