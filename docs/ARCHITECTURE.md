# RIF Runtime Architecture

RIF Runtime is a small governance layer for systems builders who want agents, scripts, and tools to take action under explicit control. The runtime does one job: turn a proposed action into a policy decision, record why that decision happened, and update posture so later decisions reflect recent behavior.

It is deliberately simple infrastructure:

- FastAPI service: `rif_runtime.api:app`
- Typer CLI: `rif`
- Persistence: JSON and append-only JSONL under `data/`
- No database
- No external service dependency
- Source-of-truth API implementation: `src/rif_runtime/api.py`

## Execution circuit

```text
Agent / automation / operator
  ↓
PolicyRequest
  ↓
PolicyEngine.evaluate()
  ↓
PolicyDecision
  ↓
ReflexiveLoop.observe()
  ↓
PostureManager threshold update
  ↓
GovernanceGraph.record_decision()
  ↓
JsonlStore append
  ↓
Audit, telemetry, graph, and replay surfaces
```

## Core layers

| Layer | Responsibility | Useful when debugging |
| --- | --- | --- |
| API | Receives policy, posture, MCP, telemetry, graph, and audit requests. | Check `src/rif_runtime/api.py` first when endpoint docs drift. |
| Runtime | Wires config, policy, posture, graph, telemetry, and persistence together. | Follow `RIFRuntime` when behavior crosses module boundaries. |
| Policy | Makes allow/deny decisions from posture, environment config, and rules. | Start here for surprising decisions. |
| Reflexive governance | Converts denial history into posture changes. | Check this when repeated denies change future behavior. |
| Graph memory | Records actor-to-target relationships for audit and summary views. | Use this to see who tried to touch what. |
| Persistence | Writes decisions and posture transitions to JSONL. | Use normal shell tooling to inspect exact runtime history. |

## Trust model

- **Deny by default:** unknown or disallowed network targets are blocked.
- **Environment-scoped control:** allowed hosts and constraints come from the active environment profile.
- **Action-aware policy:** network governance applies to real action names such as `http.request`, `api.call`, `mcp.invoke`, and `package.install`.
- **Reflexive posture:** repeated denials can escalate posture from `normal` to `elevated`, `restricted`, and `locked`.
- **Locked means locked:** once posture is `locked`, all actions are denied until posture is explicitly reset.
- **Auditable by construction:** decisions and posture transitions are persisted as append-only JSONL records.

## Operational flow

1. An agent, script, or operator proposes an action as a `PolicyRequest`.
2. The policy engine checks locked posture, exact-match policy rules, package/MCP/network constraints, and the active environment profile.
3. The runtime records a `PolicyDecision` with the matched rule and reason.
4. The reflexive loop observes the decision and updates posture if denial thresholds are crossed.
5. The governance graph stores the actor-target edge for later inspection.
6. JSONL persistence keeps a replayable trail for audit and recovery.

## Design bias

RIF favors control, observability, and small moving parts over magic:

- Local-first development should work before cloud deployment is considered.
- Runtime behavior should be inspectable from code, API responses, and log files.
- Policy changes should be explicit and reviewable.
- Recovery should be possible from persisted decisions, not hidden process memory.
- The system should remain understandable when debugging under pressure.
