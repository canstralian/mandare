# RIF Runtime Architecture

## Overview

RIF (Reflexive Intelligence Framework) Runtime is a governed execution substrate for intelligent systems. It provides a policy-driven layer between intent and execution, with complete auditability and replay capability.

## Core Components

### 1. Intent Compiler (`rif_runtime/execution`)
Parses user/agent intent into structured, policy-evaluable command objects. Validates schema and context before forwarding to policy engine.

**Files:**
- `execution/compiler.py` — intent parsing & validation
- `execution/models.py` — command object schemas

### 2. Policy Engine (`rif_runtime/policy`, `rif_runtime/governance`)
Evaluates execution requests against active policies before any action is taken. Records all evaluations for audit.

**Files:**
- `policy.py` — core policy evaluation logic
- `governance/policy_store.py` — policy persistence
- `governance/graph.py` — governance relationship tracking

### 3. Capability Router (`rif_runtime/capabilities`)
Maps validated & approved commands to executable capabilities. Routes through adapter layer for isolation.

**Files:**
- `capabilities/registry.py` — capability discovery & registration
- `capabilities/adapter.py` — capability isolation interface

### 4. Execution Layer (`rif_runtime/execution`)
Executes approved capabilities in isolated contexts. Captures stdout, stderr, return values, and timing.

**Files:**
- `execution/executor.py` — capability invocation
- `execution/sandbox.py` — execution environment isolation

### 5. Evidence & Audit (`rif_runtime/audit`, `rif_runtime/storage`)
Records all decisions, inputs, outputs, and policy evaluations. Enables deterministic replay.

**Files:**
- `audit.py` — audit trail management
- `storage/decision_store.py` — persisted decision records
- `storage/posture_store.py` — security posture snapshots

### 6. Reflexive Review (`rif_runtime/explainability`)
Post-execution analysis and governance refinement. Feeds learnings back into policy layer.

**Files:**
- `explainability.py` — decision explanation & tracing
- `governance/reflexive_loop.py` — policy adaptation

### 7. API Layer (`rif_runtime/api`)
HTTP endpoints for policy evaluation, capability invocation, audit queries, and governance inspection.

**Files:**
- `api.py` — FastAPI app definition
- `api/routes/*.py` — endpoint implementations

### 8. CLI (`rif_runtime/cli`)
Command-line interface for local invocation, validation, evidence export, and telemetry.

**Files:**
- `cli.py` — Typer CLI app

## Data Flow

```
┌─────────────┐
│   Agent     │
└──────┬──────┘
       │ intent: "POST https://api.example.com/resource"
       ▼
┌─────────────────────┐
│ Intent Compiler     │
│ (parse & validate)  │
└──────┬──────────────┘
       │ CommandObject { actor, action, target, params }
       ▼
┌──────────────────────┐
│  Policy Engine       │
│  (evaluate rules)    │
└──────┬───────────────┘
       │ decision: allow/deny with rationale
       ▼
┌─────────────────────────┐
│ Capability Router       │
│ (map to handler)        │
└──────┬──────────────────┘
       │ handler_ref
       ▼
┌─────────────────────────┐
│ Adapter Layer           │
│ (prepare isolation)     │
└──────┬──────────────────┘
       │ sandboxed_context
       ▼
┌─────────────────────────┐
│ Execution Layer         │
│ (run in sandbox)        │
└──────┬──────────────────┘
       │ result, timing, exit_code
       ▼
┌─────────────────────────┐
│ Evidence Record         │
│ (persist all state)     │
└──────┬──────────────────┘
       │ decision_id
       ▼
┌─────────────────────────┐
│ Reflexive Review        │
│ (analyze outcome)       │
└──────┬──────────────────┘
       │ feedback loop → policy refinement
       ▼
┌─────────────────────────┐
│ Governance Graph        │
│ (update relationships)  │
└─────────────────────────┘
```

## Storage Model

### Decisions (`data/decisions.jsonl`)
One JSON object per line; immutable append-only log of all policy evaluations.

```json
{
  "id": "dec_abc123",
  "timestamp": "2024-01-15T10:30:00Z",
  "actor": "agent:orchestrator",
  "action": "http.request",
  "target": "https://api.example.com/v1/resource",
  "policy_id": "default-policy",
  "result": "allow",
  "rationale": "actor in approved_actors list",
  "metadata": { "request_id": "req_xyz789" }
}
```

### Posture History (`data/posture_history.jsonl`)
Snapshots of system security state at decision points.

```json
{
  "id": "pos_def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "decision_id": "dec_abc123",
  "runtime_version": "0.3.0rc1",
  "policy_version": "2",
  "actor_reputation": 95,
  "environment_flags": ["sandbox", "network_limited"]
}
```

## Module Organization

```
src/rif_runtime/
├── __init__.py
├── api.py                          # FastAPI app entry
├── cli.py                          # Typer CLI entry
├── policy.py                       # Policy evaluation logic
├── audit.py                        # Audit trail
├── auth.py                         # Authentication & identity
├── config.py                       # Configuration loading
├── schemas.py                      # Shared Pydantic models
├── security.py                     # Security utilities (signing, hashing)
├── startup.py                      # Initialization hooks
├── explainability.py               # Decision explanation
├── replay.py                       # Deterministic replay
├── runtime.py                      # Runtime orchestration
├── agents/                         # Agent integrations
│   ├── __init__.py
│   ├── base.py
│   └── openai_adapter.py
├── capabilities/                   # Capability system
│   ├── __init__.py
│   ├── registry.py
│   ├── adapter.py
│   └── http_capability.py
├── execution/                      # Execution layer
│   ├── __init__.py
│   ├── compiler.py
│   ├── executor.py
│   ├── sandbox.py
│   └── models.py
├── governance/                     # Governance engine
│   ├── __init__.py
│   ├── graph.py
│   ├── policy_store.py
│   ├── reflexive_loop.py
│   └── models.py
├── graph/                          # Governance graph
│   ├── __init__.py
│   └── serializer.py
├── mcp/                            # Model Context Protocol
│   ├── __init__.py
│   ├── client.py
│   └── server_registry.py
├── resources/                      # Resource definitions
│   ├── __init__.py
│   └── registry.py
├── storage/                        # Persistence layer
│   ├── __init__.py
│   ├── decision_store.py
│   ├── posture_store.py
│   └── backend.py
└── configuration/                  # Configuration schemas
    ├── __init__.py
    ├── policy_config.py
    └── runtime_config.py
```

## Configuration

Runtime configuration via:
1. `rif.toml` — static configuration
2. Environment variables — overrides (`RIF_*` prefix)
3. `config/` directory — policy, capability, and resource definitions

## Extension Points

### Custom Capabilities
Implement `rif_runtime.capabilities.Capability` interface and register in `config/capabilities.yaml`.

### Custom Policies
Extend `rif_runtime.governance.PolicyRule` and reload via policy store.

### Custom Evidence Handlers
Implement `rif_runtime.storage.EvidenceBackend` for non-JSONL persistence.

## Security Model

- **Defense in Depth**: Policy layer → capability adapter → execution sandbox
- **Immutable Audit**: JSONL append-only, cryptographic validation
- **Least Privilege**: Non-root container user, minimal syscall surface
- **Cryptographic Binding**: Signed evidence bundles, replay verification

See `SECURITY.md` for detailed threat model.

## Performance Characteristics

- **Decision Latency**: ~50ms (policy evaluation)
- **Execution Overhead**: Sandbox overhead ~5-10% depending on capability
- **Storage**: ~1KB per decision record; ~500 records/day typical
- **Graph Traversal**: O(n) policy evaluation; O(log n) with index

## Versioning

- **Runtime Version**: SemVer in `pyproject.toml`
- **API Version**: URL-prefixed (`/v1/`, `/v2/`)
- **Evidence Version**: Schema version in record headers
- **Policy Version**: Tracked separately; independent releases

## Future Architecture

See `docs/ROADMAP.md` for planned enhancements:
- Multi-node governance (Kubernetes integration)
- Real-time telemetry export
- Advanced ML-driven policy optimization
- Distributed evidence ledger
