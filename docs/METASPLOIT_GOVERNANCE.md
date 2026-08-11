# Metasploit MCP Governance

RIF treats a Metasploit MCP tool as a **hostile-capability dependency**. The
goal is not "RIF can run Metasploit" — it is that RIF can prove *why* an action
was allowed, *why* a neighbouring action was denied, and *exactly which
authority boundary* prevented escalation. The core invariant is **intent is not
authority**: neither a natural-language assertion nor an imported instruction
grants a capability.

Nothing in this subsystem executes a module or reaches a live RPC endpoint. It
is the policy boundary that sits in front of one.

## Capability taxonomy

Every concrete MCP tool method is classified (`src/rif_runtime/mcp/capabilities.py`):

- **read-only** — security *knowledge*: `module.search`, `module.info`,
  `module.metadata`, `module.options`, `module.references`, `module.compatible`,
  `remediation.context`, `recon.read`, `recon.lab_data`. These never mutate
  target, session, datastore, or control-plane state.
- **consequential** — execution or mutation *authority*: `module.execute`,
  `exploit.run`, `payload.generate`, `handler.create`, `listener.create`,
  `session.*`, `route.add`, `datastore.set`, `target.set`.
- **severe** — a consequential subset whose denial escalates posture
  immediately: persistent footholds (`session.create`, `handler.create`),
  `route.add`, scope widening (`scope.widen`), and data/artifact egress
  (`credentials.export`, `artifact.export`, `payload.export`, `loot.export`).

Anything unrecognised is **denied by default** (treated as `unknown`). The
taxonomy is hashed into every evidence event as `contract_hash` so a decision
can be replayed against the exact contract that produced it.

## Ordered decision procedure

The order of checks in `MetasploitGovernor.evaluate` *is* the answer to "which
boundary prevented escalation":

1. `posture.locked` — a locked runtime denies everything.
2. **injection / NL-authority quarantine** — operator text, imported recon
   (`untrusted_context`), and string params are scanned for authority
   assertions and prompt-injection markers. Any hit denies with
   `msf.injection.quarantined` (severe).
3. **read-only capability** — always permitted (`msf.capability.read_only`).
4. **consequential / unknown capability** — requires authority the lane may not
   grant.

## The three lanes (`GovernanceMode`)

| Lane | Mode | Consequential capability outcome |
|------|------|----------------------------------|
| Read-only firewall | `read_only_firewall` | Deny — `msf.capability.execution_absent` |
| Shadow harness | `shadow` | Deny + simulate — `msf.shadow.denied`; never reaches the tool |
| Lab broker | `lab_broker` | Allow only with a valid capability token |

### 1. Read-only capability firewall

Proves RIF can distinguish knowledge from authority: read-only queries pass,
everything else is denied because execution authority is absent.

### 2. Shadow-execution harness

Every proposed call is evaluated, recorded, and returned as a simulated
denial — no action reaches the real tool. `run_benchmark`
(`src/rif_runtime/mcp/corpus.py`) drives a fixed corpus of benign, ambiguous,
and maliciously-framed requests and asserts the two success criteria:

- **zero execution-path leaks** — no consequential/unknown capability is ever
  allowed outside the broker lane;
- **100% evidence coverage** — every request yields exactly one signed evidence
  event.

### 3. Time-bound, dual-authorised lab broker

The only lane that permits a consequential action, and only with a
`CapabilityToken` minted after signed human approval. The token binds **one**
capability to **one** target, to the exact approved `intent_hash`, and expires
quickly. Verification denies with a specific boundary on each escalation route:

| Attempt | Denial rule |
|---------|-------------|
| No token | `msf.broker.approval_absent` |
| Forged/foreign signature | `msf.broker.signature_invalid` |
| Token expired | `msf.broker.token_expired` |
| Different capability class | `msf.broker.capability_mismatch` |
| Target widened off the pinned asset | `msf.broker.target_pinned` |
| Params changed after approval | `msf.broker.intent_mismatch` |
| All checks pass | `msf.broker.authorized` (allow) |

## Evidence

Each recorded governance decision emits a signed `EvidenceEvent` (HMAC over
the canonical event), appended to `data/metasploit_evidence.jsonl`. Dry-run
evaluations (`record=False`) — including `/v1/mcp/invoke` and
`/v1/mcp/metasploit/evaluate` — compute and return an `EvidenceEvent` but do
not write it to the store:

```json
{
  "decision_id": "uuid",
  "intent_hash": "sha256",
  "tool": "msfmcpd",
  "requested_capability": "module.search",
  "policy_decision": "allow",
  "scope_id": "lab-2026-07",
  "contract_hash": "sha256",
  "matched_rule": "msf.capability.read_only",
  "timestamp": "RFC3339",
  "signature": "hmac-sha256"
}
```

`MetasploitGovernor.verify_evidence` re-derives the signature; the broker
signing key comes from `RIF_MSF_BROKER_KEY` (a per-process random key is used
if unset, so tokens are session-scoped unless a stable key is configured).

## Interfaces

- `GET  /v1/mcp/metasploit/capabilities` — the taxonomy + contract hash (explain).
- `POST /v1/mcp/metasploit/evaluate` — evaluate an intent (`intent`, `mode`, optional `token`).
- `POST /v1/mcp/metasploit/token` — mint a capability token (`intent`, `approver`, `ttl_seconds`).
- CLI: `rif msf-check <capability> <target> [--mode ...]`.

Sealed-lab environment profiles (`RIF_Metasploit_ReadOnly`, `RIF_Metasploit_Lab`)
in `config/environments.yaml` restrict egress to the local broker only.
