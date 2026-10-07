# Specification Review — OpenShell Authority Projection and Enforcement Boundary

**Repository:** canstralian/mandare  
**Governs:** translation of a RIF authorization decision into an enforceable OpenShell sandbox policy and the verification gate applied before execution  
**Status:** `Draft` — implementation is held until this review is approved  
**Track:** B (Specification) — authority, capability scope, provider egress, and execution boundary  
**Depends on:** `docs/spec-review-identity-spine-migration.md`; `docs/spec-review-capability-snapshot-authority.md` where external capability observations are involved  
**Upstream reference:** NVIDIA/OpenShell commit `834b79a8c2351370e7c6c363423f5be18d440256` (2026-10-07)  
**Upstream policy contract:** OpenShell policy schema v1  
**Upstream prover contract:** `openshell-prover check <candidate> --boundary <boundary> --output json`

---

## 1. Decision

RIF SHALL treat OpenShell as an external enforcement substrate, not as the source of
authorization semantics.

The architectural split is:

```text
agent/model
    |
    | proposes
    v
RIF policy + capability admission
    |
    | produces an AuthorityProjection
    v
OpenShell policy compiler
    |
    | candidate policy
    v
OpenShell containment prover
    |
    | verified within boundary
    v
OpenShell sandbox / supervisor
    |
    | effects
    v
filesystem / process / network / provider / MCP
```

OpenShell decides what the sandbox can mechanically reach. RIF decides whether the
requested effect is authorized. Neither layer may silently substitute for the other.

This preserves the existing invariant:

> **Availability is not authorization. Admission is not execution.**

and adds:

> **A RIF allow decision is not sufficient for execution until the projected
> OpenShell policy is proven to remain within the configured runtime boundary.**

---

## 2. Non-goals

This review does not:

- replace `PolicyEngine` or RIF capability admission with OpenShell policy;
- make OpenShell a dependency of replay;
- authorize unrestricted shell, network, provider, MCP, or credential access;
- treat a successful prover result as evidence that a sandbox installed or enforced
  the policy at runtime;
- bind external capability discovery to a Decision; that contract remains governed
  by `docs/spec-review-capability-snapshot-authority.md`;
- authorize production use of the OpenShell Python SDK or gateway in this review.

The first implementation slice is the projection/compiler/prover seam only.

---

## 3. Normative invariants

### OP-1 — Intent is not authority

Model output, tool availability, requested endpoints, requested binaries, and requested
credentials are untrusted inputs. They may contribute to an authorization request but
cannot create or expand authority.

### OP-2 — Projection may narrow, never broaden

An `AuthorityProjection` MUST be derived from an already-authorized RIF decision and
MUST NOT contain filesystem paths, binaries, network destinations, methods, paths,
providers, or middleware authority absent from that decision and its admitted
capability contract.

A projection compiler may reduce authority to fit OpenShell semantics. It MUST fail
closed rather than broaden authority to obtain a representable policy.

### OP-3 — Boundary containment is mandatory

Before a projected policy may be used for execution, RIF MUST check the fully composed
candidate against an operator-supplied maximum boundary using the OpenShell containment
prover.

Only prover result `Within` / process exit code `0` is authorization-compatible.

The following are denials:

- `Exceeds` / exit code `1`;
- input, output, usage, or internal error / exit code `2`;
- unsupported or inconclusive semantics / exit code `3`;
- interruption / exit code `130`;
- unknown exit codes;
- malformed or missing JSON output when JSON output was requested;
- missing prover executable when the prover gate is configured as required.

Unknown future result states fail closed.

### OP-4 — Prover coverage is evidence, not decoration

A successful JSON prover result MUST retain:

- `schema_version`;
- `prover_version`;
- `coverage.domains`;
- result state;
- candidate policy digest;
- boundary policy digest.

A caller MUST NOT claim authority over a domain that is absent from
`coverage.domains`. A passing containment check is valid only for the domains the
upstream prover declares it modeled.

### OP-5 — Runtime enforcement is distinct from proof

The prover answers whether a candidate configuration is contained by a boundary under
its modeled semantics. It does not prove that a running sandbox installed those
restrictions.

Execution evidence must therefore distinguish at least:

```text
projection evidence
prover evidence
sandbox creation evidence
policy installation evidence
effect evidence
```

No earlier record may be used as a substitute for a later one.

### OP-6 — Credentials are referenced, not possessed

An `AuthorityProjection` may identify an approved provider or credential binding by
opaque identifier. It MUST NOT contain reusable secret material.

Credential resolution and injection belong to the enforcement/runtime layer and will
be specified before provider integration.

### OP-7 — Replay remains side-effect free

Replay may reconstruct a stored projection and its prover result. Replay MUST NOT invoke
OpenShell, create a sandbox, refresh provider credentials, or re-run external effects.

---

## 4. AuthorityProjection contract

The first implementation SHALL use a small immutable internal contract rather than
embedding OpenShell YAML throughout RIF.

Proposed Python shape:

```python
@dataclass(frozen=True, slots=True)
class AuthorityProjection:
    projection_id: str
    decision_id: str
    actor: str
    capability: str
    filesystem_read: tuple[str, ...] = ()
    filesystem_write: tuple[str, ...] = ()
    network_rules: tuple[NetworkAuthority, ...] = ()
    provider_refs: tuple[str, ...] = ()
```

with:

```python
@dataclass(frozen=True, slots=True)
class NetworkAuthority:
    name: str
    host: str
    port: int
    protocol: Literal["rest", "tcp", "mcp", "json-rpc", "websocket", "graphql"]
    binaries: tuple[str, ...]
    access: Literal["read-only", "read-write", "full"] | None = None
    allow_rules: tuple[RequestRule, ...] = ()
    deny_rules: tuple[RequestRule, ...] = ()
```

The exact representation may change during review, but the semantic requirements are
binding:

1. projection is immutable;
2. projection carries the governing `decision_id`;
3. filesystem authority is separated into read and write sets;
4. network authority is explicit per destination and executable;
5. request-level authority is explicit where OpenShell can inspect it;
6. secret values are forbidden;
7. unspecified authority means denied.

`projection_id` SHOULD be a deterministic digest of the canonical projection payload
excluding non-authority metadata. The exact canonicalization algorithm remains an open
decision in this review and MUST be fixed before implementation evidence depends on it.

---

## 5. OpenShell policy compilation

The compiler SHALL target OpenShell policy schema v1.

The minimum composed policy shape is:

```yaml
version: 1

filesystem_policy:
  include_workdir: false
  read_only: []
  read_write: []

landlock:
  compatibility: best_effort

network_policies: {}
```

The compiler MUST NOT rely on OpenShell defaults where an omitted field could create
more authority than an explicit RIF projection.

### 5.1 Filesystem mapping

- `filesystem_read` -> `filesystem_policy.read_only`
- `filesystem_write` -> `filesystem_policy.read_write`
- workdir access is explicit; it is not silently enabled by the compiler

Path normalization must reject ambiguous or invalid paths before YAML generation.
Whether symlink/canonical path validation belongs in the compiler or sandbox preparation
is open, but no validation may broaden a path.

### 5.2 Network mapping

Each `NetworkAuthority` maps to one named `network_policies` entry with:

- explicit endpoint host;
- explicit port;
- explicit protocol;
- `enforcement: enforce` for inspected protocols;
- explicit binary path(s).

For REST, WebSocket, and GraphQL, the compiler may use an OpenShell access preset only
when the preset is equal to or narrower than the RIF authority. Otherwise it MUST emit
explicit `rules`.

For REST rules, method and path are both required. A projection such as:

```text
GET api.github.com /repos/canstralian/mandare/**
```

must not compile to:

```yaml
access: read-only
```

because that preset would authorize GET/HEAD/OPTIONS to every path on the endpoint.

It must compile to an explicit rule such as:

```yaml
rules:
  - allow:
      method: GET
      path: /repos/canstralian/mandare/**
```

### 5.3 TCP

`protocol: tcp` is L4 authority. It cannot encode HTTP method/path restrictions.

If a RIF projection requires application-layer restrictions, the compiler MUST reject
a TCP representation rather than erase those restrictions.

### 5.4 MCP

OpenShell can inspect MCP methods and tool names but not tool arguments.

Therefore:

- RIF MAY project method/tool-name constraints into OpenShell;
- RIF MUST NOT treat an allowed MCP tool name as argument-level authorization;
- any argument-sensitive capability contract remains enforced by RIF or a dedicated
  MCP governance layer;
- OpenShell's MCP policy is defense in depth, not a replacement for RIF's capability
  semantics.

This review does not resolve the capability snapshot binding governed by the existing
capability-snapshot review.

---

## 6. Maximum boundary

The operator boundary is a separate artifact from the candidate projection.

```text
RIF authorized decision
        |
        v
candidate OpenShell policy
        |
        +---------------------+
        |                     |
        v                     v
maximum boundary       openshell-prover
                              |
                         Within only
                              |
                              v
                        execution eligible
```

The boundary MUST NOT be generated from the same untrusted request that produced the
candidate. Doing so would make containment tautological.

The boundary must come from trusted operator configuration, environment policy, or
another explicitly authorized source.

For the first implementation slice:

- boundary is read from a configured local file path;
- missing boundary fails closed;
- candidate and boundary are both written to isolated temporary files for the prover;
- temporary files are removed after the result is captured;
- the original projection and digests are retained as evidence.

---

## 7. Prover adapter contract

Proposed interface:

```python
class PolicyProver(Protocol):
    def check(
        self,
        candidate: str,
        boundary: str,
    ) -> ProverResult:
        ...
```

The first adapter invokes:

```text
openshell-prover check <candidate-file> --boundary <boundary-file> --output json
```

Requirements:

- argv list invocation only; never `shell=True`;
- absolute or explicitly configured executable path;
- bounded timeout;
- bounded stdout/stderr capture;
- controlled environment;
- no fallback to "allow" if the binary is missing;
- parse JSON only after an exit-code-compatible result;
- preserve stderr for diagnostics but never use diagnostic text as authority;
- unexpected output shape => denial;
- timeout => denial.

The adapter SHALL return a typed result containing the raw upstream result state and
stable RIF-local denial reason.

RIF MUST NOT infer success merely from empty stderr, parseable JSON, or process launch.

---

## 8. Relationship to the existing capability-snapshot review

This review and `docs/spec-review-capability-snapshot-authority.md` govern different
seams.

The existing review answers:

> What observed external capability catalog is authoritative for a Decision?

This review answers:

> Given an authorized Decision, what mechanical runtime authority may be projected into
> OpenShell, and how is that projection bounded before execution?

When both apply, ordering is:

```text
DISCOVER
  -> SNAPSHOT
  -> AUTHORIZE (Decision binds capability_snapshot_id)
  -> PROJECT (AuthorityProjection binds decision_id)
  -> PROVE
  -> EXECUTE
  -> OBSERVE
```

No OpenShell integration may bypass the snapshot requirements where a remote capability
catalog was consulted.

---

## 9. Evidence and persistence

The first implementation may keep prover evidence local and append-oriented, but the
record must be shaped so it can later participate in the unified evidence contract.

Minimum fields:

```text
projection_id
decision_id
candidate_sha256
boundary_sha256
prover_schema_version
prover_version
prover_result
coverage_domains
checked_at
adapter_version
```

Do not record secrets, provider token values, or generated credential material.

A prover pass is `verification evidence` about the projected policy. It is not
`effect evidence` and must not be represented as an execution success.

---

## 10. Implementation sequence after approval

### O1 — Projection + compiler + standalone prover

Implement:

- `src/rif_runtime/authority/projection.py`
- `src/rif_runtime/execution/openshell/policy.py`
- `src/rif_runtime/execution/openshell/prover.py`
- unit tests with a fake prover executable/result fixture
- no OpenShell Python SDK dependency
- no gateway requirement
- no sandbox creation
- no credentials

Acceptance:

```text
candidate <= boundary  -> eligible
candidate > boundary   -> denied
unsupported            -> denied
inconclusive           -> denied
prover unavailable     -> denied
timeout                -> denied
malformed result       -> denied
```

### O2 — OpenShell execution backend

Introduce an execution-backend protocol and an experimental OpenShell backend. The
existing `ExecutionKernel` remains capability-specificity-free.

Initial backend authority:

- no providers;
- no reusable credentials;
- default-deny network;
- one sandbox;
- one bounded command;
- bounded output;
- bounded timeout;
- teardown after execution.

### O3 — Provider and credential mediation

Add opaque provider bindings and prove that workloads do not receive reusable provider
secrets directly.

This stage requires a follow-up specification amendment for credential lifecycle and
evidence.

### O4 — Supervisor middleware

Evaluate RIF as an OpenShell supervisor middleware/policy hook for request inspection,
posture enforcement, DLP, or higher-level governance.

This stage is not authorized by this review.

---

## 11. Conformance tests

The approved implementation MUST include tests that prove at least:

1. default projection emits no network policy;
2. explicit filesystem read/write sets do not cross-map;
3. REST path-limited authority does not compile to a wider access preset;
4. TCP refuses application-layer constraints;
5. binaries are explicit and an empty binary set is rejected for network rules;
6. compiler output is deterministic for equivalent projections;
7. prover exit `0` with valid JSON and required coverage can pass;
8. prover exits `1`, `2`, `3`, `130`, and unknown all deny;
9. missing prover denies;
10. timeout denies;
11. malformed JSON denies;
12. missing required coverage denies the affected authority domain;
13. boundary/candidate digests are stable over the exact bytes checked;
14. secret-like values are rejected from projection fields intended to carry only
    opaque provider references.

Integration tests with a real OpenShell prover are desirable but MUST NOT replace the
deterministic unit suite.

---

## 12. Security implications

### Positive

- converts RIF authority into a second, independent runtime enforcement layer;
- constrains network access by destination, executable, and where representable,
  application-layer operation;
- adds a formal containment check before runtime authority is materialized;
- creates a path to credential mediation without exposing reusable secrets to agents;
- preserves deny-by-default semantics when OpenShell is missing or inconclusive.

### New risks

- policy compiler bugs can under-constrain OpenShell;
- OpenShell upstream schema or prover semantics can drift;
- a boundary generated from the same request as the candidate is meaningless;
- prover coverage can be overclaimed;
- a passing proof can be incorrectly treated as runtime enforcement evidence;
- YAML serialization/canonicalization differences can corrupt evidence identity;
- WSL2 support may differ from Linux production behavior.

Mitigations are the conformance tests above, an upstream compatibility pin, explicit
coverage handling, and keeping RIF authorization independent from OpenShell availability.

---

## 13. Upstream compatibility policy

The initial implementation SHALL pin its validated compatibility to an explicit
OpenShell release or commit range.

The upstream reference used for this review is:

```text
NVIDIA/OpenShell
834b79a8c2351370e7c6c363423f5be18d440256
2026-10-07
```

At that revision:

- authored policy schema version is `1`;
- containment CLI is `openshell-prover check`;
- exit `0` means within boundary;
- exit `1` means exceeds;
- exit `2` means usage/input/output/internal error;
- exit `3` means unsupported/inconclusive;
- exit `130` is interruption on Unix;
- JSON includes a numeric `schema_version`, `prover_version`, and
  machine-readable `coverage.domains`.

If any of those contracts change, compatibility must fail closed until the adapter is
reviewed and updated.

---

## 14. Open decisions

- **OD-O1 — Projection digest canonicalization.** Proposed: RFC8785-JCS over a
  JSON-compatible projection model, consistent with the capability-snapshot review.
- **OD-O2 — Required prover coverage domains for O1.** The implementation must name
  the domains it relies on rather than assuming every upstream domain is modeled.
- **OD-O3 — Boundary source configuration.** Proposed: environment-specific local
  path in current configuration, not model-supplied input.
- **OD-O4 — Workdir semantics.** Proposed: `include_workdir: false` unless a governed
  workspace path is explicitly projected.
- **OD-O5 — Landlock compatibility.** Proposed for development:
  `best_effort`; production posture may require a stricter compatibility mode if
  OpenShell exposes one compatible with supported environments.
- **OD-O6 — OpenShell package dependency.** O1 should use the standalone executable
  adapter and add no Python SDK dependency. SDK adoption is evaluated at O2.
- **OD-O7 — Windows/WSL2 status.** Development support may be experimental; no
  production-security claim is made from WSL2 validation alone.

---

## 15. Approval criteria

This review is ready to move from `Draft` when:

- [ ] Runtime Architect confirms the Mandare/OpenShell responsibility split.
- [ ] Specification Governor confirms OP-1 through OP-7.
- [ ] OD-O1 through OD-O7 are resolved.
- [ ] Required prover coverage domains are named from the upstream prover contract.
- [ ] Interaction with the open capability-snapshot review is confirmed non-conflicting.
- [ ] O1 test matrix is accepted.
- [ ] Builder is explicitly released for O1.

**Sign-off**

| Role | Name | Date | Status |
| --- | --- | --- | --- |
| Specification Governor | | | Pending |
| Runtime Architect | | | Pending |
