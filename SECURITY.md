# Security Model

## Overview

RIF Runtime operates on a principle of **defense in depth** with multiple security layers protecting against unauthorized execution, evidence tampering, and policy bypass. This document describes the threat model and mitigations.

## Threat Model

### T1: Unauthorized Capability Invocation

**Threat**: An untrusted actor or compromised agent attempts to execute a capability without policy approval.

**Mitigations**:
- **Policy Engine**: All capabilities must pass policy evaluation before execution
- **Actor Validation**: Cryptographic verification of actor identity
- **Audit Trail**: Immutable record of all attempts (approved and rejected)

### T2: Evidence Tampering

**Threat**: Attacker modifies stored decisions or execution evidence to hide unauthorized actions.

**Mitigations**:
- **Immutable Log**: JSONL append-only; no in-place edits
- **Cryptographic Hashing**: SHA-256 hash chains for evidence integrity
- **Signed Records**: HMAC-SHA256 signing of critical fields with runtime key
- **Versioning**: Schema version in each record prevents silent format changes

### T3: Policy Bypass

**Threat**: Attacker crafts malicious intent or parameters that circumvent policy evaluation.

**Mitigations**:
- **Intent Validation**: Schema validation on all intent inputs
- **Path Traversal Prevention**: Normalized path comparison
- **Context Binding**: Policy decisions include execution context (sandbox level, actor reputation)
- **Policy Versioning**: Active policy version tracked; rollback possible

### T4: Sandbox Escape

**Threat**: Capability execution escapes sandbox isolation and accesses host resources.

**Mitigations**:
- **Resource Limits**: Memory, CPU, and file descriptor limits enforced
- **Capability Dropping**: Linux capabilities dropped (CAP_SYS_ADMIN, CAP_NET_ADMIN, etc.)
- **Read-Only Filesystem**: Root FS read-only; only temp directories writable
- **Network Isolation**: Capabilities limited to approved egress targets
- **seccomp**: System call filtering in strict mode

### T5: Replay Attacks

**Threat**: Attacker captures and replays an old authorization decision to re-execute an action.

**Mitigations**:
- **Timestamp Validation**: Decisions include strict timestamps; old decisions rejected
- **Nonce Binding**: Each decision bound to a unique execution nonce
- **State Verification**: Pre-execution state hash checked against decision state

### T6: Elevation of Privilege

**Threat**: Non-admin actor escalates privileges to execute admin capabilities.

**Mitigations**:
- **Role-Based Access Control**: Explicit role matrix in policy
- **Least Privilege**: Non-root container user (UID 10001)
- **Sudo Prevention**: No sudo in container; no password-less privilege escalation
- **Capability Isolation**: Admin capabilities isolated to dedicated containers

### T7: Side-Channel Attacks (Timing, Resource Leakage)

**Threat**: Attacker infers policy decisions or evidence content through timing variations or resource consumption.

**Mitigations**:
- **Constant-Time Comparison**: Policy engine uses constant-time string comparison
- **Resource Normalization**: Execution time normalized before logging to prevent timing leakage
- **Batched Telemetry**: Metrics aggregated and rounded to hide individual request patterns

### T8: Supply Chain Compromise

**Threat**: Attacker compromises build pipeline or dependencies to inject malicious code.

**Mitigations**:
- **Dependency Pinning**: Exact versions in `requirements.txt`
- **SBOM Generation**: Software Bill of Materials generated on release
- **Signed Releases**: Binaries and containers signed with release key
- **Reproducible Builds**: Docker builds tagged with Git SHA for verification

## Security Controls

### Authentication & Authorization

```yaml
actor: "agent:orchestrator"
role: "admin"
policy:
  - action: "http.request"
    target_pattern: "https://api.*.example.com/v1/*"
    approval_required: false
  - action: "file.write"
    target_pattern: "/data/*"
    approval_required: true
    approvers: ["admin:security", "admin:devops"]
```

### Policy Rules

```yaml
rules:
  - id: "default-deny"
    priority: 0
    condition: "true"
    effect: "deny"
    
  - id: "allow-trusted-http"
    priority: 100
    condition: "actor in trusted_actors && action == 'http.request' && target_domain in allowlist"
    effect: "allow"
    
  - id: "require-approval"
    priority: 50
    condition: "action == 'file.delete'"
    effect: "require_approval"
    approval_timeout_minutes: 30
```

### Evidence Integrity

Each decision record is signed:

```json
{
  "id": "dec_abc123",
  "timestamp": "2024-01-15T10:30:00Z",
  "actor": "agent:orchestrator",
  "action": "http.request",
  "target": "https://api.example.com/v1/resource",
  "policy_id": "default-policy",
  "result": "allow",
  "rationale": "actor in trusted_actors && target in allowlist",
  "metadata": { "request_id": "req_xyz789" },
  "_signature": "HMAC-SHA256(fields || runtime_secret)"
}
```

Verification:

```python
def verify_decision(decision: Dict, runtime_secret: str) -> bool:
    """Verify decision integrity."""
    stored_sig = decision.pop("_signature")
    canonical = json.dumps(decision, sort_keys=True, separators=(',', ':'))
    expected_sig = hmac.new(
        runtime_secret.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()
    return stored_sig == expected_sig
```

### Container Security

**Dockerfile Best Practices**:

```dockerfile
# 1. Non-root user
RUN adduser --disabled-password --no-create-home appuser
USER appuser

# 2. Read-only root filesystem
# (enforced at runtime with --read-only)

# 3. No setuid binaries
RUN find / -perm /6000 -type f 2>/dev/null | xargs chmod a-s

# 4. Minimal base image
FROM python:3.12-slim  # Not alpine, but smaller than full
```

**Runtime Execution**:

```bash
docker run \
  --user appuser:appuser \
  --read-only \
  --tmpfs /tmp \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt=no-new-privileges \
  --security-opt=seccomp=strict.json \
  --memory=512m \
  --cpus=1 \
  --pids-limit=100 \
  rif-runtime-server
```

### Network Security

**Egress Controls**:

```yaml
capabilities:
  http_request:
    network_isolation:
      allowed_domains:
        - "api.anthropic.com"
        - "api.openai.com"
        - "*.example.com"
      blocked_ips:
        - "169.254.169.254"  # AWS metadata
        - "127.0.0.1"  # Loopback (unless whitelisted)
        - "0.0.0.0/8"  # This network
```

**TLS Verification**:

```python
# All outbound HTTPS must verify certificates
http_client = httpx.Client(
    verify=True,  # Enforce certificate verification
    cert_reqs="required"
)
```

## Incident Response

### Detecting Unauthorized Access

Monitor for:

```json
{
  "decision": "deny",
  "reason": "policy violation",
  "actor": "agent:unknown"
}
```

Query audit trail:

```bash
rif audit query --actor agent:unknown --result deny --since "24h ago"
rif evidence export agent_unknown.zip
```

### Revoking Compromised Actors

```bash
# 1. Remove from trusted actors in policy
# 2. Review all recent decisions by actor
rif audit query --actor agent:compromised

# 3. Replay to understand impact
rif replay exec_123 --dry-run

# 4. Force policy reload
rif policy reload config/policies.revoked.yaml --force
```

### Evidence Preservation

For forensics, immediately export evidence:

```bash
# Full bundle
rif evidence export full_audit.zip

# With crypto verification
rif evidence export --verify full_audit.zip
```

## Compliance

### OWASP Top 10

| Risk | Control | Evidence |
|------|---------|----------|
| A1: Injection | Intent validation, parameterized compilation | `tests/unit/test_injection_prevention.py` |
| A2: Broken Auth | Actor identity verification, role-based policy | `config/policies.yaml`, audit logs |
| A3: Broken Access Control | Policy engine, capability isolation | Policy evaluation results |
| A4: Insecure Deserialization | Pydantic schema validation | `rif_runtime/schemas.py` |
| A5: Broken Encryption | HMAC-SHA256, TLS verification | Security scanning CI |
| A6: Auth Bypass | Policy versioning, replay protection | Audit trail immutability |
| A7: XSS / Injection | Not applicable (no web UI with user input) | - |
| A8: Insecure Deserialization | Covered in A4 | - |
| A9: Logging & Monitoring | Immutable audit trail | JSONL storage |
| A10: Broken Crypto | HMAC, SHA-256, TLS 1.2+ | Cryptography library pinning |

## Security Scanning

### Automated CI Checks

- **Bandit** (Python security linter): `.github/workflows/bandit.yml`
- **CodeQL** (static analysis): `.github/workflows/codeql.yml`
- **Gitleaks** (secret detection): `.github/workflows/gitleaks.yml`
- **Dependency Review** (CVE tracking): `.github/workflows/dependency-review.yml`

### Manual Security Audit

```bash
# Check for weak dependencies
pip-audit

# Review cryptography usage
grep -r "crypto\|hash\|encrypt" src/ --include="*.py"

# Find hardcoded secrets
gitleaks detect --report-path gitleaks-report.json
```

## Security Reporting

To report a security vulnerability, **do not** open a public issue. Instead:

1. Email `security@example.com` with details
2. Allow 7 days for initial response
3. Embargoed disclosure until patch is released

## Future Hardening

- **Hardware Security Module (HSM)**: Offload signing to HSM for production
- **Mutual TLS (mTLS)**: Client certificate verification for agent connections
- **Attestation**: TPM-based attestation of runtime integrity
- **Distributed Ledger**: Immutable evidence on blockchain for regulated environments
