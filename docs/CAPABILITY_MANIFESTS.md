# Capability Manifest - Validation Rules & Security

## Validation Rules

### Schema Validation

All capability manifests must be valid according to `CapabilityManifest` Pydantic schema:

```python
from rif_runtime.schemas.capability import CapabilityManifest

# Load from YAML/JSON
manifest = CapabilityManifest(**yaml.safe_load(manifest_content))

# Validation happens automatically (raises ValidationError on failure)
```

#### Required Fields

| Field | Type | Purpose |
|-------|------|---------|
| `name` | str | Unique capability identifier (1-255 chars) |
| `description` | str | Human-readable explanation |
| `category` | enum | Primary category (network, filesystem, process, etc.) |
| `version` | str | Semantic version (X.Y.Z format) |

#### Automatic Validations

1. **Version Format** (regex)
   - Must be semantic versioning: `\d+\.\d+\.\d+`
   - Examples: `1.0.0`, `2.1.3`
   - Rejects: `1.0`, `v1.0.0`, `1.0.0-beta`

2. **Side Effects vs Category** (cross-field)
   - Network capabilities must have `network_access.enabled=true` if `NETWORK_EGRESS` side effect present
   - Filesystem capabilities must have `filesystem_access.enabled=true` if write/delete side effects present
   - Process capabilities can have `PROCESS_EXECUTION`, `ENVIRONMENT_MUTATION`
   - Credential capabilities must declare `CREDENTIAL_EXPOSURE`

3. **Replayability vs Mutates State** (cross-field)
   - If `mutates_state=true`, cannot be `DETERMINISTIC` replayable
   - `NON_REPLAYABLE` must have `mutates_state=true`
   - `IDEMPOTENT` must have `mutates_state=true` (but safe to replay)

4. **Network Access Consistency**
   - If `network_access.enabled=false`, cannot have `HTTPS` protocol, cannot have `allowed_domains`
   - If `require_tls=true`, must use `HTTPS` protocol
   - DNS-only capabilities cannot use HTTP/HTTPS/SSH protocols

5. **Filesystem Access Consistency**
   - If `access_level=READ`, cannot have `filesystem_delete` side effect
   - If `access_level=WRITE`, must declare `allowed_paths`
   - Blocked paths cannot be within allowed paths
   - File extensions must match intended operations (`.py` for code execution, etc.)

6. **External Services**
   - If `mutation_allowed=true`, side effects must include `EXTERNAL_SERVICE_MUTATION`
   - Auth-required services must declare `credentials_type`
   - Rate limits must be positive integers (or None)

7. **Timeout Constraints**
   - Must be between 1 and 3600 seconds
   - Network timeouts typically 15-60 seconds
   - Filesystem operations typically 10-300 seconds
   - Long-running operations require justification in description

8. **Evidence Requirements**
   - At least one evidence requirement must be immutable
   - Sensitive evidence must be marked (for credential masking)
   - Evidence names should match implementation capabilities

### Policy-Level Validation

#### Manifest Registration

When registering a manifest in policy/config:

```yaml
capabilities:
  - name: shell_command
    manifest: config/capabilities/shell_command.yaml
    policy:
      allowed: true
      requires_approval: true
      approval_groups: ["security", "devops"]
      cost_limit: 10  # USD per execution
      rate_limit: 5   # per minute
```

**Validation rules**:
1. Manifest name must match config name
2. Cost limit >= cost_estimate.estimated_cost_usd (if set)
3. Rate limit must be reasonable for capability (web search max 60/min, file write max 10/min)
4. Approval groups must exist in RBAC
5. Timeout in policy must be >= timeout in manifest

#### Policy Compatibility Matrix

Policy must declare compatibility with:

```yaml
compatibility:
  manifest_versions: ["1.0.0", "1.0.1"]  # Semver ranges supported
  api_versions: ["v1"]
  evidence_schema_version: 1
  recovery_compatible: true  # Can be replayed for recovery
```

---

## Security Implications

### Threat Model Integration

Each manifest addresses specific threat classes:

#### T1: Unauthorized Capability Invocation
**Threat**: Untrusted actor invokes dangerous capability without policy approval.

**Mitigations**:
- `requires_approval: true` blocks execution unless explicitly approved
- Policy engine validates actor role/group before allowing
- Audit trail records who approved what

**Example**: `shell_command`, `git_push` require approval.

#### T2: Over-Privilege Execution
**Threat**: Capability given access beyond what's needed (e.g., shell with `/` filesystem access).

**Mitigations**:
- `allowed_paths` must be specific (e.g., `/tmp/**`, `/home/user/workspace/**`)
- `access_level` is granular (READ, WRITE, EXECUTE, ADMIN)
- `allowed_extensions` restricts file types
- Blocked paths prevent access to sensitive dirs (`/etc`, `/sys`, `/root`)

**Validation**: Policy must verify `allowed_paths` is restrictive (no `/`).

#### T3: Data Exfiltration
**Threat**: Network capability sends data to unauthorized external service.

**Mitigations**:
- `allowed_domains` whitelist restricts egress targets
- `blocked_domains` blacklist prevents metadata service access (AWS 169.254.169.254)
- `require_tls` enforces encryption
- Evidence captures all network requests (headers, body, status)

**Validation**: Policy must ensure `allowed_domains` doesn't include attacker-controlled domains.

#### T4: Credential Exposure
**Threat**: Capability logs or leaks credentials to untrusted systems.

**Mitigations**:
- `sensitive=true` evidence is redacted before logging
- Credentials passed via secure mechanisms (environment, mounted files)
- SSH keys in `filesystem_access.blocked_paths` (or explicitly allowed)
- Evidence marked with `credentials_type` for policy review

**Validation**: Evidence marked sensitive are properly masked in audit trail.

#### T5: Side Effect Concealment
**Threat**: Capability performs unauthorized mutations not declared in manifest.

**Mitigations**:
- `side_effects` list is exhaustive and validated at registration
- Evidence captures all observable side effects
- Replay engine detects unexpected evidence
- Policy evaluation requires explicit approval for mutating capabilities

**Validation**: Manifest side effects match implementation (via integration tests).

#### T6: Denial of Service
**Threat**: Capability resource exhaustion (infinite loops, memory bombs, bandwidth floods).

**Mitigations**:
- `timeout_seconds` enforces max execution time
- `max_file_size_mb`, `max_total_size_mb` limits filesystem writes
- `max_retries` limits retry storms
- Rate limits in policy (e.g., max 5 web searches/min)
- Cost estimation prevents runaway API spend

**Validation**: Timeout + cost limits enforced by policy engine.

#### T7: Privilege Escalation
**Threat**: Capability used to gain elevated privileges.

**Mitigations**:
- Container runs as non-root user (UID 10001)
- No `sudo` available in execution environment
- Capabilities with `PRIVILEGE_ESCALATION` side effect require explicit approval
- Evidence captures process exit codes (non-zero = failure)

**Validation**: Manifests with `PRIVILEGE_ESCALATION` must be marked `requires_approval=true`.

### Risk Scoring Model

Each manifest is scored (1-10) based on:

```python
class RiskScore:
    """Calculate risk score for a capability."""
    
    def __init__(self, manifest: CapabilityManifest):
        self.score = 0
    
    def evaluate(self) -> int:
        """Return risk score 1-10."""
        score = 1  # Base score
        
        # Mutates state = +2 risk
        if self.manifest.mutates_state:
            score += 2
        
        # Network egress = +1 risk
        if SideEffectType.NETWORK_EGRESS in self.manifest.side_effects:
            score += 1
        
        # Filesystem write = +1 risk
        if SideEffectType.FILESYSTEM_WRITE in self.manifest.side_effects:
            score += 1
        
        # External service mutation = +2 risk
        if SideEffectType.EXTERNAL_SERVICE_MUTATION in self.manifest.side_effects:
            score += 2
        
        # Credential exposure = +3 risk
        if SideEffectType.CREDENTIAL_EXPOSURE in self.manifest.side_effects:
            score += 3
        
        # Privilege escalation = +4 risk
        if SideEffectType.PRIVILEGE_ESCALATION in self.manifest.side_effects:
            score += 4
        
        # Process execution = +2 risk
        if SideEffectType.PROCESS_EXECUTION in self.manifest.side_effects:
            score += 2
        
        # Replayability affects trust
        if self.manifest.replayability == Replayability.DETERMINISTIC:
            score -= 1  # More trustworthy
        elif self.manifest.replayability == Replayability.NON_REPLAYABLE:
            score += 1  # Harder to audit
        
        # Non-idempotent = harder to recover from
        if self.manifest.replayability == Replayability.NON_IDEMPOTENT:
            score += 1
        
        # Requires approval = +0 risk (mitigated by policy)
        # But indicates high-risk by design
        
        return min(10, max(1, score))
```

**Risk Levels**:
- **1-2**: Read-only queries (web search, HTTP GET)
- **3-4**: Filesystem reads, basic API calls
- **5-6**: Filesystem writes, non-idempotent operations
- **7-8**: Process execution, credential access
- **9-10**: Privilege escalation, destructive operations (git push, file delete)

### Audit Trail Integration

Each manifest evidence requirement maps to audit trail:

```json
{
  "decision_id": "dec_abc123",
  "execution_id": "exec_xyz789",
  "capability_name": "shell_command",
  "capability_version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "policy_decision": "allow",
  "evidence": {
    "command_invoked": "ls /tmp",
    "stdout": "file1.txt\nfile2.txt",
    "stderr": "",
    "exit_code": 0,
    "execution_time_ms": 45
  },
  "evidence_integrity": {
    "content_hash": "sha256:abcd1234...",
    "signed": true,
    "signature": "..."
  }
}
```

**Properties**:
- Evidence marked `sensitive=true` is redacted in logs but available for audit queries
- Evidence marked `immutable=true` is cryptographically signed
- Evidence captures full request/response (for replay)

### Manifest Versioning & Compatibility

Manifest versions follow semantic versioning:

- **MAJOR**: Breaking changes (new required parameters, new side effects)
- **MINOR**: Backward-compatible additions (new optional parameters)
- **PATCH**: Bug fixes, documentation updates

Policy must declare compatible versions:

```yaml
capability_manifest:
  name: shell_command
  compatible_versions:
    - "1.0.*"    # Any 1.0.x version
    - "1.1.0"    # Specific version
  deprecated_versions:
    - "0.x.*"
```

---

## Manifest Lifecycle

### Creation → Registration → Execution → Audit

```
1. CREATION (Developer)
   - Write manifest YAML/JSON
   - Validate against schema
   - Test against implementation

2. REVIEW (Security)
   - Audit side effects
   - Verify access patterns are least-privilege
   - Check risk score
   - Approve for registration

3. REGISTRATION (Ops)
   - Add to config/capabilities/
   - Register with policy engine
   - Set rate limits, cost limits, approval requirements
   - Distribute to runtime environments

4. EXECUTION (Runtime)
   - Policy engine loads manifest
   - Evaluates against policy rules
   - Executes if approved
   - Captures all evidence per requirements

5. AUDIT (Compliance)
   - Retrieve decision + evidence
   - Verify side effects match manifest
   - Check replay determinism
   - Generate compliance report

6. UPDATE (Maintenance)
   - New version with bug fixes → PATCH
   - New optional feature → MINOR
   - Breaking change → MAJOR (requires policy update)
```

---

## Best Practices

### ✅ DO

1. **Be explicit**: Declare all side effects, even "obvious" ones
2. **Be restrictive**: Use specific `allowed_paths`, `allowed_domains` (not wildcards)
3. **Be defensive**: Mark evidence `sensitive=true` when in doubt
4. **Be testable**: Include examples in description for policy writers
5. **Be versioned**: Follow semantic versioning rigorously
6. **Be auditable**: Require immutable evidence for critical capabilities

### ❌ DON'T

1. **Don't under-declare**: Missing a side effect defeats governance
2. **Don't use wildcards**: `allowed_paths: ["/**"]` gives full filesystem access
3. **Don't skip validation**: Always run schema validation before registration
4. **Don't mix concerns**: One capability = one primary purpose
5. **Don't set unlimited timeouts**: Always set reasonable max time
6. **Don't assume trust**: Mark evidence `sensitive=true` for any data containing secrets

---

## Examples

### ✅ Good Manifest (restrictive, explicit)

```yaml
name: upload_file_to_s3
version: 1.0.0
description: Upload a single file to an allowed S3 bucket
category: external_service

side_effects:
  - EXTERNAL_SERVICE_MUTATION
  - NETWORK_EGRESS

mutates_state: true

network_access:
  enabled: true
  protocols: [HTTPS]
  allowed_domains:
    - s3.us-east-1.amazonaws.com
    - my-bucket.s3.amazonaws.com
  blocked_domains:
    - 169.254.169.254  # AWS metadata
  require_tls: true
  timeout_seconds: 60

filesystem_access:
  enabled: true
  access_level: READ
  allowed_paths:
    - /home/user/uploads/**
  max_file_size_mb: 100

external_services:
  - name: aws_s3
    endpoint: https://s3.us-east-1.amazonaws.com
    auth_required: true
    credentials_type: aws_iam_role
    mutation_allowed: true

requires_approval: true
approval_reason: "S3 uploads mutate external state and require explicit authorization"

parameters:
  bucket:
    type: string
    description: S3 bucket name (must match allowed list)
  key:
    type: string
    description: S3 object key
  file_path:
    type: string
    description: Local file path (must be in /home/user/uploads/)

required_parameters: [bucket, key, file_path]
```

### ❌ Bad Manifest (too permissive)

```yaml
name: do_anything  # ❌ Too vague
version: 1.0  # ❌ Not semver

category: process

side_effects: []  # ❌ Missing all side effects

mutates_state: true

network_access:
  enabled: true
  protocols: [HTTP, HTTPS, SSH]  # ❌ Too many
  allowed_domains: ["*"]  # ❌ Wildcard!

filesystem_access:
  enabled: true
  access_level: ADMIN  # ❌ Too much privilege
  allowed_paths: ["/"]  # ❌ Entire filesystem!

timeout_seconds: 3600  # ❌ Too long
max_retries: 999  # ❌ Too many

parameters: {}  # ❌ No parameters?

requires_approval: false  # ❌ Should require approval
```

---

## Conclusion

Capability manifests provide:
- ✅ **Explicit governance**: All side effects declared upfront
- ✅ **Auditability**: Complete evidence trail captured per manifest
- ✅ **Replay safety**: Replayability semantics prevent accidental re-execution
- ✅ **Least privilege**: Restrictive access patterns by default
- ✅ **Compliance**: Risk scoring and approval workflows
- ✅ **Security**: Threat model integration and credential protection

Use them to build trustworthy, auditable agent runtimes.
