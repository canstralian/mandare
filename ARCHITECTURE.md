# RIF Runtime Architecture

## Purpose

RIF Runtime places a deterministic governance boundary between an agent or caller and actions the runtime is willing to evaluate or invoke.

The architectural invariant is:

> **Policy is authoritative; model output is advisory.**

This document describes the implementation currently present in `src/rif_runtime/`. Proposed architecture is kept separate and explicitly labelled as such.

## Implemented request path

```text
Caller
  |
  v
PolicyRequest
  |
  v
RIFRuntime.evaluate()
  |
  +--> PolicyEngine --------------------+
  |                                     |
  +--> policy / environment constraints |
  |                                     v
  |                               PolicyDecision
  |                                     |
  +--> GovernanceGraph <----------------+
  |
  +--> ReflexiveLoop -> Posture
  |
  +--> JsonlStore -> decisions.jsonl / posture_history.jsonl
  |
  +--> telemetry / audit / recovery surfaces
```

The exact behaviour of this path is defined by the Python implementation and its tests. The API route definitions in `src/rif_runtime/api.py` are the source of truth for the HTTP surface.

## Major components

| Component | Implementation | Role | Status |
|---|---|---|---|
| API | `src/rif_runtime/api.py` | FastAPI HTTP surface | Implemented |
| CLI | `src/rif_runtime/cli.py` | Local operator/developer commands | Implemented |
| Runtime | `src/rif_runtime/runtime.py` | Wires policy, posture, graph, telemetry and persistence | Implemented |
| Policy | `src/rif_runtime/policy.py` | Evaluates policy requests and constraints | Implemented |
| Configuration | `src/rif_runtime/config.py`, `rif.toml`, `config/` | Runtime/environment configuration | Implemented |
| Posture | `src/rif_runtime/governance/` | Tracks and escalates runtime posture | Implemented |
| Graph | `src/rif_runtime/graph/` | In-memory actor/target relationship view | Implemented |
| Persistence | `src/rif_runtime/storage/` | JSONL append-oriented state storage | Implemented |
| Replay | `src/rif_runtime/replay.py` | Reconstructs graph/posture state from decision history | Implemented |
| Audit primitives | `src/rif_runtime/audit.py` | Hash-chain record primitives and verification | Implemented as a library surface; not equivalent to every persisted decision being hash-chained |
| Security utilities | `src/rif_runtime/security.py` | Canonicalization, hashing, HMAC, encryption helpers and redaction | Implemented |
| MCP | `src/rif_runtime/mcp/` | MCP governance and Metasploit-specific evaluation | Implemented in the current scope |
| Supabase integration | `src/rif_runtime/integrations/supabase.py` | Optional remote persistence/JWT verification | Optional |
| Resources / runs / execution packages | `src/rif_runtime/resources/`, `runs/`, `execution/` | Supporting domain surfaces | Present; not all are on the default request path |

## Persistence model

The default runtime uses a configured data directory. The repository seed contains `data/policies.json`; runtime-generated JSONL files are normally ignored by Git.

Common files include:

- `decisions.jsonl` — persisted policy decisions;
- `posture_history.jsonl` — persisted posture transitions;
- `metasploit_evidence.jsonl` — Metasploit-related evidence when that path is used.

JSONL is durable local state, not a distributed database. File integrity, backup, concurrency, retention, and recovery are deployment responsibilities unless a future storage contract states otherwise.

## Authentication boundary

Mutable control-plane operations use the `X-API-Key` header and the `RIF_CONTROL_PLANE_API_KEYS` environment variable. If no control-plane keys are configured, guarded operations fail closed.

This is an application-level API-key guard, not a complete enterprise identity system. Production deployments should place the service behind an appropriate identity, network, secret-management, TLS, logging, and authorization architecture.

## Optional remote persistence

The repository includes an optional Supabase integration. It can verify Supabase JWTs and write execution/evidence records when configured. Local JSONL remains the authoritative store for the helper functions in that integration; remote writes are intentionally non-authoritative and failures are logged rather than silently replacing local state.

## Security boundaries

The runtime contains several useful security primitives:

- deny-oriented policy evaluation;
- control-plane authentication;
- secret redaction helpers;
- cryptographic hashing/HMAC/encryption helpers;
- an audit hash-chain library;
- replay and persisted-state recovery;
- non-root container execution in the supplied Dockerfile;
- dependency locks and security scanning in CI.

These controls should not be conflated with a complete sandbox, zero-trust deployment, compliance certification, or tamper-proof audit system. See [`SECURITY.md`](SECURITY.md) for the current limitations.

## Specifications and target architecture

`spec/` and several documents under `docs/` describe contracts and architecture that are ahead of the current implementation. They are useful design inputs, but they are not automatically runtime guarantees.

In particular, the following remain architectural work rather than claims about the current request path:

- a general capability router/execution adapter pipeline;
- a unified EvidenceRecord contract across all runtime paths;
- governed remote-inference authorization;
- automated reflexive repair/evolution;
- distributed or tamper-evident evidence storage;
- enterprise identity federation and policy administration.

When implementation and design documentation disagree, current executable code and passing tests determine shipped behaviour; the discrepancy should then be documented and corrected rather than rationalized.

## Change discipline

Architecture changes should answer four questions:

1. **Authority:** who or what is allowed to make the decision?
2. **Boundary:** where does the proposed action cross from evaluation into effect?
3. **Evidence:** what durable fact proves what happened?
4. **Recovery:** can the resulting state be inspected and reconstructed?

For changes that alter a cross-domain contract, use the specification-review process described in [`spec/README.md`](spec/README.md) before implementing a second, competing contract.
