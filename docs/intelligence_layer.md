# RIF Runtime Intelligence Layer

## Boundary

**RIF decides; intelligence interprets.**

The intelligence layer is optional and isolated from deterministic enforcement.
Policy evaluation, matched rules, posture, confirmation requirements, allowlists,
approval gates, audit events, and governance artifacts remain authoritative RIF
state.

`POST /v1/intelligence/generate` returns an explanation or a planning-only
security draft. It cannot execute tools, invoke MCP, scan hosts, run commands,
approve requests, alter posture, or alter allow/deny decisions.

A request snapshot is not authority. Until the route is wired to a trusted RIF
decision resolver, `decision_verified` is `false` and the endpoint produces a
deterministic fallback only.

## Provider egress

`OPENAI_API_KEY` configures an optional adapter; it does not authorize cloud
egress. The adapter defaults to deny and no model request is made unless a
future RIF policy-backed provider-access guard explicitly supplies
`egress_permitted=True`.

Before remote inference is enabled, the runtime must verify the current provider
host/capability policy, resolve a trusted decision snapshot, apply a versioned
redaction policy, and record a provider-access artifact. See
[ADR-0007](ADR-0007-governed-inference-egress.md).

Inputs are recursively redacted and bounded before hashing or provider use. Each
response identifies the redaction-policy version and hashes the redacted input
material that would be sent externally.

## Output constraints

Structured output is validated as advisory-only. Command-like text, code fences,
MCP/tool invocation markers, and populated `execution_commands` are rejected.
Any operational action must be compiled into a separate request and pass normal
RIF evaluation and approval controls.

## Audit properties

Each response includes:

- the supplied decision snapshot and whether it was verified;
- `source` (`llm_assisted` or `deterministic_fallback`);
- `model_used` when available;
- UTC generation timestamp;
- redaction-policy version;
- SHA-256 hashes of redacted input and advisory output material;
- warnings for incomplete evidence or unavailable provider access.
