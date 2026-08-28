# Mandare Roadmap

## North star

Mandare aims to make the boundary between **intent** and **authority** explicit, testable, and reviewable.

The model may propose. The runtime evaluates. A governed system records what decision was made and why.

This is a roadmap, not a statement that every item below exists today.

## Current state

| Area | Current status |
|---|---|
| Policy evaluation | Implemented, still evolving |
| Runtime posture | Implemented |
| Graph and telemetry views | Implemented |
| Local decision/posture persistence | Implemented |
| Replay/recovery of local runtime state | Implemented |
| Audit hash-chain primitives | Implemented as a library surface |
| MCP governance surfaces | Implemented in current scope |
| Capability identity/admission contract | Implemented first vertical slice |
| Governed capability execution | Implemented through `MandareRuntime.execute_capability()` |
| Remote provider authorization seam | Specification work / gated |
| Unified EvidenceRecord contract | Specification/design |
| Signed skill/artifact verification | Planned |
| Skill/static security inspection | Planned |
| Benchmark/regression evidence ingestion | Planned |
| Reflexive repair | Planned |
| Controlled evolution | Planned |
| Distributed evidence / enterprise storage | Planned |
| SBOM / signed releases / reproducible builds | Planned |

## Near-term engineering priorities

### 1. Capability supply-chain evidence

The first capability-governance slice now separates executable adapters from their governance identity and requires integrity plus passing evaluation evidence before admission. The next increment should make that evidence durable and independently verifiable.

- persist capability records rather than keeping them only in process memory;
- ingest artifact digests and signatures;
- represent source commit/version and retrieval provenance;
- add static inspection and dependency findings;
- ingest regression/benchmark results;
- keep admission decisions replayable.

### 2. Specification integrity

Keep implementation and contract work synchronized without allowing parallel interpretations of the same boundary.

- close or update open specification reviews;
- inventory fixtures before schema changes;
- keep identity, capability, evidence, and replay contracts explicit;
- make contract tests executable where practical.

### 3. Governed provider egress

The next provider-inference seam is a **Specification Review**, not an implementation shortcut.

The intended architecture is:

```text
Decision
   |
   v
Egress authorization
   |
   v
Redaction
   |
   v
Inference adapter
   |
   v
Advisory output
   |
   v
Evidence
```

Provider credentials must never become implicit authority. This work is subject to the repository's existing Track-B governance and must not bypass an open cross-domain review.

### 4. Evidence contract

Define what an EvidenceRecord means, which events are authoritative, how provenance is represented, and what replay can and cannot prove.

The goal is stronger than "we wrote a log": evidence should have a clear owner, schema, retention model, integrity story, and verification procedure.

### 5. Enterprise release assurance

Future release hardening should add, in a deliberate sequence:

- SBOM generation;
- signed artefacts and/or provenance attestations;
- reproducible-build verification;
- release verification documentation;
- tested upgrade and rollback procedures.

These are not current guarantees.

## Longer-term directions

### Bounded reflexive repair

Introduce explicit schemas for failure observation, diagnosis, repair proposal, and verification. Keep model-generated diagnosis and proposals subordinate to deterministic policy and human-controlled promotion.

### Controlled evolution

Architecture and policy changes should be promoted through reviewable proposals with threat models, evaluation evidence, rollback plans, and observation windows.

### Reference demonstration

A public demonstration can show the governance thesis without becoming a production control plane. Demo infrastructure should use no privileged production credentials and should not imply production assurance.

## Non-goals

The roadmap does not seek to make Mandare:

- an autonomous agent framework;
- an implicit approval layer for model output;
- an unrestricted shell/MCP execution broker;
- a credential vault;
- a compliance certification;
- a tamper-proof distributed ledger by assertion;
- a replacement for enterprise identity, network, or incident-response systems.

## Planning rule

A roadmap item moves into implementation only when its authority boundary, contract, fixtures/tests, and rollback implications are sufficiently specified.
