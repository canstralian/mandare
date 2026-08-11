# RIF Runtime architecture (v1.0 view)

Short circuit (always true of the MVP core):

```text
Agent request
  → Policy evaluation
  → Decision
  → Reflexive posture + governance graph
  → Append-only persistence
  → Audit / replay / CLI
```

Trust model: environment-scoped hosts, posture escalation, fail-closed control
plane auth for mutating routes. Deny-by-default is the **GaC** target; today’s
engine still has legacy default-allow after constraints — see CHANGELOG.

## Component diagram

```mermaid
flowchart TB
  subgraph clients [Clients]
    Agent[Agent_or_operator]
    CLI[rif_CLI]
    HTTP[HTTP_clients]
  end

  subgraph api_layer [API_and_CLI]
    FastAPI[FastAPI_api.py]
    Typer[Typer_CLI]
  end

  subgraph core [Governance_core]
    Runtime[RIFRuntime]
    Policy[PolicyEngine_or_GaC_evaluator]
    Reflex[ReflexiveLoop_Posture]
    Graph[GovernanceGraph]
  end

  subgraph persist [Persistence]
    JSONL[JsonlStore_events_or_decisions]
    Policies[PolicyStore_JSON]
    Evidence[Content_addressed_evidence]
  end

  subgraph contracts [v1_contracts_spec]
    Events[spec_events]
    ReplaySpec[spec_replay]
    GaC[spec_governance_GaC]
  end

  Agent --> CLI
  Agent --> HTTP
  CLI --> Typer
  HTTP --> FastAPI
  Typer --> Runtime
  FastAPI --> Runtime
  Runtime --> Policy
  Runtime --> Reflex
  Runtime --> Graph
  Runtime --> JSONL
  Runtime --> Policies
  Runtime --> Evidence
  Events -.defines.-> JSONL
  ReplaySpec -.defines.-> Typer
  GaC -.defines.-> Policy
```

## Evaluate path (sequence)

```mermaid
sequenceDiagram
  participant C as Client
  participant A as API_or_CLI
  participant R as RIFRuntime
  participant P as PolicyEvaluator
  participant G as Graph_and_Reflex
  participant S as JsonlStore

  C->>A: policy request / rif run
  A->>R: evaluate
  R->>P: PolicyInput plus pack
  P-->>R: decision plus explanation
  R->>G: record_decision
  G->>S: append event or decision
  R-->>A: PolicyDecision / explanation
  A-->>C: JSON response
```

## v1.0 target vs MVP

| Area | MVP (`0.3.x`) | v1.0 target |
| --- | --- | --- |
| Audit unit | `PolicyDecision` JSONL | `rif.runtime.event/v1` envelopes |
| Replay | Summary recover from decisions | Pure / verify / time-travel engine |
| Policy | Exact rules + hardcoded constraints | GaC policy packs |
| CLI | serve / check / replay file / status | run / replay / verify / inspect / policy / evidence |

Details: [ARCHITECTURE.md](ARCHITECTURE.md) (one-pager), root aspirational essays may lag — prefer this file + `spec/`.
