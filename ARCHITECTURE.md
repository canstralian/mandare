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

## Resource discovery

Resource discovery is a pre-execution observation layer. It answers **what resources are candidates for an objective**; it does not authorize, admit, or execute them.

```text
DiscoveryIntent
      |
      v
ResourceDiscovery provider
      |
      +--> StaticResourceDiscovery
      |
      +--> ARDDiscoveryClient
      |
      +--> future registries / catalogs
      |
      v
ResourceCandidate[]
      |
      v
Governance / selection / capability admission
      |
      v
Execution
```

`ResourceDiscovery` is deliberately provider-neutral. ARD v0.91 is an adapter, not a RIF-native authority model. ARD relevance scores remain informational search signals and are never interpreted as trust, compliance, safety, or authorization. The runtime persists the discovery observation separately in `discovery_evidence.jsonl` so later policy/selection work can reconstruct what was found without conflating discovery with execution.

The ARD client implements the standard `POST /search` request shape and normalizes returned entries into `ResourceCandidate` objects. It does not fetch or invoke the artifact described by a result. Native execution protocols such as MCP or A2A remain downstream concerns.

## Governed capability execution

The runtime now has a first vertical slice for capability governance. An executable adapter and its governance identity are separate objects. The adapter is never treated as trusted merely because it is registered.

```text
ExecutionManifest
      |
      v
RIFRuntime.execute_capability()
      |
      +--> PolicyEngine
      |       |
      |       +---- deny ---> evidence ---> DENIED
      |       |
      |       +---- allow
      |             |
      |             v
      +------> CapabilityRegistry
                    |
                    +--> integrity verified?
                    +--> passing evaluation?
                    +--> lifecycle evaluated/admitted?
                    |
                    +---- fail ---> admission denied
                    |
                    +---- pass
                          |
                          v
                    ExecutionKernel
                          |
                          v
                    Capability adapter
                          |
                          v
                  capability_evidence.jsonl
```

The important boundary is:

> **Discovery is not authorization. Availability is not authorization. Admission is not execution. Policy authorization and capability admission are both required before the governed runtime path invokes an adapter.**

Capability governance records currently capture identity, provenance, integrity, permissions, dependencies, lifecycle state, and evaluation evidence. This is intentionally a small contract that can later absorb signed artifacts, SkillSpector-style inspection, benchmark evidence, and richer provenance without coupling those concerns to the executable adapter interface.

The existing `ExecutionKernel` remains capability-specificity-free: it resolves an already-selected adapter and executes it. `RIFRuntime.execute_capability()` is the governed orchestration path that performs policy evaluation and capability admission before invoking the kernel.

## Major components

| Component | Implementation | Role | Status |
|---|---|---|---|
| API | `src/rif_runtime/api.py` | FastAPI HTTP surface | Implemented |
| CLI | `src/rif_runtime/cli.py` | Local operator/developer commands | Implemented |
| Runtime | `src/rif_runtime/runtime.py` | Wires policy, posture, graph, telemetry, persistence, discovery, and governed capability execution | Implemented |
| Policy | `src/rif_runtime/policy.py` | Evaluates policy requests and constraints | Implemented |
| Configuration | `src/rif_runtime/config.py`, `rif.toml`, `config/` | Runtime/environment configuration | Implemented |
| Posture | `src/rif_runtime/governance/` | Tracks and escalates runtime posture | Implemented |
| Graph | `src/rif_runtime/graph/` | In-memory actor/target relationship view | Implemented |
| Persistence | `src/rif_runtime/storage/` | JSONL append-oriented state storage | Implemented |
| Replay | `src/rif_runtime/replay.py` | Reconstructs graph/posture state from decision history | Implemented |
| Audit primitives | `src/rif_runtime/audit.py` | Hash-chain record primitives and verification | Implemented as a library surface; not equivalent to every persisted decision being hash-chained |
| Resources | `src/rif_runtime/resources/` | Resource identity, descriptors, registries, and discovery contracts | Implemented first discovery vertical slice |
| Capabilities | `src/rif_runtime/capabilities/` | Executable adapters plus governance identity/admission records | Implemented first vertical slice |
| Execution | `src/rif_runtime/execution/` | Manifest and capability execution kernel | Implemented; governed orchestration lives in `RIFRuntime` |
| MCP | `src/rif_runtime/mcp/` | MCP governance and Metasploit-specific evaluation | Implemented in the current scope |
| Supabase integration | `src/rif_runtime/integrations/supabase.py` | Optional remote persistence/JWT verification | Optional |

## Capability trust model

A capability record deliberately separates several claims:

- **identity** — what capability is being discussed;
- **provenance** — where it came from and which version/commit was inspected;
- **integrity** — whether the expected artifact identity/signature was verified;
- **evaluation** — whether an explicit evaluation suite produced passing evidence;
- **lifecycle** — whether the capability has progressed far enough to be admitted;
- **permissions/dependencies** — what the capability declares it may require.

A signature, when present, proves an integrity relationship. It does not by itself prove that the capability is safe, useful, or policy-authorized.

This deliberately mirrors the evidence-first trust model being explored from external skill ecosystems without making RIF dependent on a particular skill package format.

## Persistence model

The default runtime uses a configured data directory. The repository seed contains `data/policies.json`; runtime-generated JSONL files are normally ignored by Git.

Common files include:

- `decisions.jsonl` — persisted policy decisions;
- `posture_history.jsonl` — persisted posture transitions;
- `metasploit_evidence.jsonl` — Metasploit-related evidence when that path is used;
- `capability_evidence.jsonl` — governed capability execution attempts and results;
- `discovery_evidence.jsonl` — resource discovery observations and candidate sets.

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
- capability integrity/evaluation admission checks;
- discovery separated from authorization and execution;
- non-root container execution in the supplied Dockerfile;
- dependency locks and security scanning in CI.

These controls should not be conflated with a complete sandbox, zero-trust deployment, compliance certification, or tamper-proof audit system. See [`SECURITY.md`](SECURITY.md) for the current limitations.

## Specifications and target architecture

`spec/` and several documents under `docs/` describe contracts and architecture that are ahead of the current implementation. They are useful design inputs, but they are not automatically runtime guarantees.

Remaining architectural work includes:

- durable registry persistence and richer capability discovery;
- signed artifact verification and provenance attestations;
- automated static/security inspection of skill packages;
- benchmark and regression evidence ingestion;
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
