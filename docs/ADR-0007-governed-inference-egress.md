# ADR-0007: Governed inference egress

- **Status:** Accepted
- **Date:** 2026-06-25
- **Decision owner:** RIF Runtime

## Context

The optional intelligence layer may call a remote model provider to interpret
RIF state. A provider API key alone is not authority to send data outside the
runtime. The runtime must treat model invocation as a governed network action,
not as an implementation detail of an HTTP endpoint.

The original intelligence endpoint accepted a caller-supplied decision snapshot
and arbitrary evidence/context, then invoked a provider whenever credentials
were available. This would permit a fabricated snapshot to appear
"deterministic" and would make cloud egress dependent on environment variables
rather than current RIF policy.

## Decision

Remote inference is permitted only through a governed provider-access path.

1. The client submits an intent and evidence references; it does not submit an
authoritative decision snapshot.
2. RIF Runtime evaluates the intent and constructs the deterministic snapshot
from its own current decision record.
3. RIF Runtime separately evaluates provider egress as a network action against
an explicit provider host and capability allowlist.
4. If provider egress is denied, ambiguous, expired, or unavailable, the
intelligence endpoint returns a deterministic local fallback and does not send
any content externally.
5. The external request is built from a versioned redaction policy and bounded
payload limits. The runtime records the hash of the redacted material actually
sent, not only the pre-redaction input.
6. The model output is a non-authoritative advisory artifact. It cannot mutate
policy, posture, approvals, decisions, execution leases, or tool state.
7. Security-oriented outputs are typed declarative recommendations. Free-form
fields must not be used to carry shell commands, tool calls, payloads, scan
instructions, or exploit instructions.

## Required provider-access artifact

Every allowed remote invocation must produce an artifact containing at least:

- source decision identifier and deterministic decision hash;
- provider, model, and endpoint host;
- provider-egress decision and matched rule;
- policy and capability-manifest hashes;
- redaction-policy version;
- hash of the redacted payload sent;
- output hash;
- request timestamp, expiry, and source classification;
- warning set for missing or excluded evidence.

## Consequences

- `OPENAI_API_KEY` enables a configured adapter but does not itself authorize
  network egress.
- Cloud model use remains deny-by-default until the provider host and capability
  are explicitly allowed by current policy.
- Provider failures degrade to deterministic local interpretation.
- The intelligence layer remains advisory and replayable, but is not an
  execution path.

## Acceptance criteria

The implementation is not complete until automated tests prove that:

1. forged client decision data is replaced by a current RIF evaluation;
2. denied provider egress produces no provider call;
3. absent policy allowance produces no provider call;
4. redacted payload hashes identify the exact outgoing material;
5. secret-like fields, credentials, and oversized payloads are excluded before
   egress;
6. command/tool/payload smuggling in every output field is rejected;
7. model output cannot change deterministic governance state;
8. fallback output is deterministic when provider access is unavailable.
