# Metasploit MCP Governance

> **Scope:** governance/evaluation. This document does not claim that Mandare provides a general-purpose Metasploit execution service.

Mandare treats a Metasploit MCP integration as a high-risk capability boundary. The core invariant is:

> **Intent is not authority.**

The current subsystem classifies requested MCP capabilities, applies ordered governance checks, and can simulate/deny consequential actions without reaching a live RPC endpoint in the governance path documented here.

## Capability classes

`src/mandare/mcp/capabilities.py` classifies known methods into:

- **read-only** — information-oriented methods such as module metadata/options/references and selected reconnaissance/context queries;
- **consequential** — execution or state-changing methods;
- **severe** — selected consequential operations that cause a stronger posture response.

Unknown capabilities are denied by the governor's default handling.

The exact taxonomy and its contract hash are exposed by the current API. Treat the implementation as authoritative if this document and code diverge.

## Decision order

The Metasploit governor evaluates, in order:

1. locked posture;
2. injection/authority-assertion quarantine;
3. read-only classification;
4. consequential/unknown capability handling;
5. broker token validation where the selected mode permits that path.

The ordering matters because the first applicable boundary determines the recorded reason.

## Governance modes

| Mode | Intended behaviour |
|---|---|
| `read_only_firewall` | Read-only capability requests may be evaluated; consequential requests are denied |
| `shadow` | Requests are evaluated and simulated without reaching a live tool |
| `lab_broker` | Consequential requests may proceed through the capability-token checks implemented by the governor |

`lab_broker` is a controlled governance path, not a claim of a production-safe Metasploit broker. Deployment owners must supply the surrounding isolation, scope, credentials, and network controls.

## Capability tokens

The broker path can issue a `CapabilityToken` bound to the approved capability/target/intent and a configured expiry. Token verification checks the fields implemented by `src/mandare/mcp/metasploit.py`.

The token-minting API is a control-plane operation and therefore requires the configured `X-API-Key` guard.

Do not describe this as a complete dual-control or human-approval system unless an external human approval mechanism actually participates in the request path.

## Evidence

Governed Metasploit evaluations can produce signed `EvidenceEvent` records using the HMAC utilities in the runtime. Persisted events are written to the configured Metasploit evidence JSONL path when recording is enabled.

A returned evidence object from a dry-run is not the same thing as a persisted audit record. Consumers must distinguish:

```text
computed evidence
vs.
persisted evidence
vs.
independently protected evidence
```

The current HMAC key is process/configuration scoped. It does not provide external anchoring or tamper resistance against an attacker who can modify both the evidence file and its key/configuration.

## Interfaces

- `GET /v1/mcp/metasploit/capabilities` — current capability taxonomy and contract hash;
- `POST /v1/mcp/metasploit/evaluate` — evaluate an intent/mode/token;
- `POST /v1/mcp/metasploit/token` — mint a capability token under control-plane authentication;
- `rif msf-check <capability> <target> [--mode ...]` — local evaluation command.

## Security boundary

The governance subsystem should be understood as a policy/evaluation boundary. A production deployment that connects it to a real Metasploit service still needs independent network isolation, target scoping, credential management, operator authorization, logging, and incident-response controls.
