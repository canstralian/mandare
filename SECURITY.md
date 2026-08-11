# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| `1.x` (once released) | Yes — see [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) support window |
| `0.3.x` / `0.3.0rc*` | Best-effort until `1.0.0` |
| `< 0.3` | No |

Report vulnerabilities privately (see Reporting below). Do not open public issues for undisclosed vulns.

## Reporting a vulnerability

Email or GitHub Security Advisory for [canstralian/rif-runtime](https://github.com/canstralian/rif-runtime).

Please include: affected version, reproduction, impact, and any suggested fix. We aim to acknowledge within **7 days** and provide a remediation plan for supported versions.

## Threat model (honest — what ships today)

RIF Runtime is a **governed policy / posture mediator** (FastAPI + Typer + local JSONL). It is **not** a full sandbox hypervisor. Claims below match `src/rif_runtime/` unless marked **Planned**.

### Implemented controls

| ID | Threat | Mitigation in tree |
| --- | --- | --- |
| T1 | Unauthorized control-plane mutation | `auth.py`: `X-API-Key` vs `RIF_CONTROL_PLANE_API_KEYS`; SHA-256 digests + `hmac.compare_digest`; **fail-closed** (503 if unset) on guarded routes |
| T2 | Anonymous posture / audit flooding via sim routes | MCP invoke/evaluate use `record=False` (dry-run; no JSONL / posture mutate) |
| T3 | Host egress outside allowlist | `PolicyEngine` + environment `allowed_hosts` / networking flags |
| T4 | Locked runtime | `Posture.locked` denies further allows in the engine |
| T5 | Metasploit capability abuse at the governance boundary | Modeled firewall/shadow/broker; HMAC capability tokens; evidence JSONL — **does not execute Metasploit** |
| T6 | Secret leakage in logs | Prefer hashes/redaction helpers in `security.py` for token material; do not log raw API keys |
| T7 | Supply chain (CI) | GitHub Actions: CodeQL, Bandit, Gitleaks, dependency review (see `.github/workflows/`) |

### Not implemented (do not assume)

| Claim sometimes found in older docs | Reality |
| --- | --- |
| OS sandbox (seccomp, CAP drop, RO rootfs) | **Not** enforced by this Python package |
| HMAC-signed every `PolicyDecision` row | Decisions are plain JSONL `model_dump()` today |
| Cryptographic actor identity / full RBAC matrix | Actor is a string id; control plane is API-key based |
| Hash-chained production audit on every evaluate | `audit.py` exists with tests; **not** wired into `RIFRuntime.record_decision` |
| Multi-tenant isolation | Single-process, shared `data/` files |

v1.0 contracts (`spec/events`, `spec/replay`) define hash chains and content-addressed evidence for the **target** audit model; treat them as requirements for the v1.0 implementation cut, not as live guarantees of `0.3.0rc1`.

## Operational hardening (deployers)

1. Set `RIF_CONTROL_PLANE_API_KEYS` before exposing the API.
2. Bind to localhost or put TLS/authn at a reverse proxy; do not expose unauthenticated sim routes to the public internet without understanding dry-run semantics.
3. Restrict filesystem permissions on `data/*.jsonl`.
4. Pin dependency versions in production images; rebuild on advisories.
5. Prefer `rif serve --no-reload` (or raw uvicorn without reload) in production.

## Security updates

- **Patch** releases for supported majors may include security fixes without API breaks.
- Critical issues may ship out-of-band advisories and patched tags (`1.0.x`).

## Coordinated disclosure

We request **90 days** before public PoC detail when possible. Credit will be given unless you opt out.
