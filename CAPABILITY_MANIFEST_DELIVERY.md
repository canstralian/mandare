# 🎯 Capability Manifest System - Complete Delivery

## Executive Summary

RIF Runtime's **Capability Manifest System** provides a declarative, policy-friendly approach to govern intelligent agent execution. Every tool and side effect is represented as an explicit manifest, enabling informed policy decisions, complete auditability, and safe replay.

---

## What is a Capability Manifest?

A **manifest** is a YAML/JSON file that explicitly declares:

✅ **What the capability does** (side effects)  
✅ **What access it needs** (network, filesystem, external services)  
✅ **What evidence must be captured** (for audit)  
✅ **How safely it can be replayed** (deterministic, idempotent, etc.)  
✅ **Whether it requires approval** (high-risk governance)  

**Example**: Shell command manifest declares:
- Executes arbitrary processes (side effect: PROCESS_EXECUTION)
- Accesses temp filesystem (filesystem_access: /tmp/**, allowed)
- May write files (evidence: stdout, stderr, exit_code captured)
- Cannot be replayed safely (replayability: non_deterministic)
- Requires explicit approval before execution

---

## System Components

### 1. Schema Layer (`src/rif_runtime/schemas/capability.py`)

**500 lines** defining:

```python
class CapabilityManifest:
    name: str                                 # shell_command
    version: str                              # 1.0.0 (semver)
    description: str                          # Execute arbitrary shell commands
    category: str                             # process|network|filesystem|etc.
    side_effects: List[SideEffectType]        # [PROCESS_EXECUTION, ...]
    mutates_state: bool                       # True = has side effects
    
    network_access: NetworkAccessSpec         # Protocols, domains, TLS
    filesystem_access: FilesystemAccessSpec   # Paths, access level, size limits
    external_services: List[ExternalServiceSpec]  # Third-party integrations
    
    timeout_seconds: int                      # 60 max
    evidence_requirements: List[EvidenceRequirement]  # What to capture
    replayability: Replayability              # deterministic|idempotent|etc.
    
    cost_estimate: CostEstimate               # API calls, data transfer, USD
    requires_approval: bool                   # Needs explicit OK
```

**Validation**:
- ✅ Pydantic schema enforcement
- ✅ Cross-field consistency (side effects match access patterns)
- ✅ Semantic versioning
- ✅ Least privilege defaults

### 2. Example Manifests (`src/rif_runtime/schemas/capability_examples.py`)

**600 lines** with 5 real-world examples:

| Capability | Risk | Replays | Mutates | Approval |
|-----------|------|---------|---------|----------|
| **shell_command** | 9/10 | NON_DETERMINISTIC | Yes | Required |
| **web_search** | 2/10 | NON_DETERMINISTIC | No | Not required |
| **file_write** | 6/10 | IDEMPOTENT | Yes | Required |
| **git_push** | 8/10 | NON_IDEMPOTENT | Yes | Required |
| **http_api_call** | 4/10 | NON_DETERMINISTIC | Depends | Not required |

Each shows:
- Complete side effects declaration
- Restrictive access patterns
- Evidence capture requirements
- Replayability semantics
- Parameter schemas

### 3. Registry & Validation (`src/rif_runtime/capabilities/manifest_registry.py`)

**500 lines** providing:

**ManifestRegistry**:
```python
registry = ManifestRegistry("config/capabilities")
manifest = registry.load("shell_command")      # Load with validation
registry.load_all()                            # Batch load
registry.validate("shell_command")             # Check validity
registry.validate_all()                        # Validate batch
registry.clear_cache()                         # Force reload
```

**ManifestValidator**:
```python
checks = ManifestValidator.check_all(manifest)
print(checks["risk_score"])                    # 1-10 risk
print(checks["least_privilege_warnings"])      # Security gaps
print(checks["evidence_warnings"])             # Audit gaps
```

### 4. Documentation

**CAPABILITY_MANIFESTS.md** (550 lines):
- Validation rules (schema, policy-level, compatibility)
- Security implications (threat model, risk scoring)
- Best practices (do's and don'ts)
- Examples (good vs bad manifests)

**CAPABILITY_MANIFEST_SYSTEM.md** (400 lines):
- System overview
- Usage examples
- Integration guide
- Benefits and next steps

---

## Key Features

### 1. Explicit Side Effects Declaration

Every manifest declares all observable behaviors:

```yaml
side_effects:
  - network_egress              # Communicates externally
  - filesystem_write            # Creates/modifies files
  - external_service_mutation   # Changes external state
  - credential_exposure         # Accesses secrets
  - privilege_escalation        # Elevates permissions
  - process_execution           # Runs code
  - environment_mutation        # Changes env vars
  - filesystem_delete           # Deletes files
```

**Why**: Enables policy engine to make informed decisions without inspecting code.

### 2. Restrictive Access Patterns (Least Privilege)

Network and filesystem access are whitelisted:

```yaml
network_access:
  enabled: true
  protocols: [HTTPS]
  allowed_domains:
    - "api.anthropic.com"
    - "api.openai.com"
  blocked_domains:
    - "169.254.169.254"  # AWS metadata
  require_tls: true
  timeout_seconds: 30

filesystem_access:
  enabled: true
  access_level: WRITE
  allowed_paths:
    - "/home/user/workspace/**"
    - "/tmp/**"
  blocked_paths:
    - "/etc/**"
    - "/sys/**"
    - "/root/**"
  max_file_size_mb: 100
```

**Why**: Prevents accidental over-privilege or privilege escalation.

### 3. Replayability Semantics

Each capability declares how safely it can be replayed:

```yaml
replayability: deterministic        # Same input → same output ✓ safe to replay
# or
replayability: idempotent           # Safe to replay (e.g., mkdir -p) ✓
# or
replayability: non_idempotent       # Replay may differ (e.g., API call) ⚠️
# or
replayability: non_replayable       # Cannot replay (e.g., rm) ✗
```

**Why**: Recovery engine knows whether it can safely re-execute for consistency.

### 4. Evidence Requirements

Each manifest specifies what evidence must be captured:

```yaml
evidence_requirements:
  - name: command_invoked
    format: text
    sensitive: false          # Not redacted
    immutable: true           # Cryptographically signed
  - name: stdout
    format: text
    sensitive: true           # May contain secrets; redact in logs
    immutable: true
  - name: exit_code
    format: json
    sensitive: false
    immutable: true
```

**Why**: Policy-agnostic evidence capture; different manifests need different audit trails.

### 5. Automated Risk Scoring (1-10)

Risk calculated from manifest properties:

```
Base: 1
+ mutates_state: 2
+ network_egress: 1
+ filesystem_write: 1
+ external_service_mutation: 2
+ credential_exposure: 3
+ privilege_escalation: 4
- deterministic_replayable: 1
```

**Risk Levels**:
- 1-2: Read-only queries (web search, HTTP GET)
- 3-4: Filesystem reads, basic API calls
- 5-6: Filesystem writes, non-idempotent ops
- 7-8: Process execution, credential access
- 9-10: Privilege escalation, destructive ops

---

## Security Model

### Threat Mitigation

| Threat | Mitigation |
|--------|-----------|
| **T1: Unauthorized Invocation** | `requires_approval=true` + policy evaluation |
| **T2: Over-Privilege** | Restrictive `allowed_paths`, `allowed_domains` |
| **T3: Data Exfiltration** | Whitelist domains, block metadata, capture network |
| **T4: Credential Exposure** | Mark evidence `sensitive=true`, enforce masking |
| **T5: Side Effect Concealment** | Exhaustive `side_effects`, evidence capture |
| **T6: Denial of Service** | `timeout_seconds`, `max_file_size_mb`, rate limits |
| **T7: Privilege Escalation** | Non-root execution, mark as high-risk |

### Validation Rules

**Schema Level**:
- ✅ Version must be semantic (X.Y.Z)
- ✅ Side effects must match category
- ✅ Network access disabled if no network effects
- ✅ Replayability consistent with mutations

**Policy Level**:
- ✅ Cost limit >= estimated cost
- ✅ Rate limit appropriate for capability
- ✅ Approval groups exist in RBAC
- ✅ Timeout >= manifest timeout

**Runtime Level**:
- ✅ Evidence captured per requirements
- ✅ Sensitive evidence redacted
- ✅ Immutable evidence signed
- ✅ Side effects match manifest

---

## Usage Example

### 1. Define Manifest

```yaml
# config/capabilities/shell_command.yaml
name: shell_command
version: 1.0.0
description: Execute arbitrary shell commands
category: process

side_effects:
  - PROCESS_EXECUTION
  - FILESYSTEM_WRITE  # May write to /tmp

mutates_state: true

filesystem_access:
  enabled: true
  access_level: WRITE
  allowed_paths: ["/tmp/**", "/home/user/workspace/**"]
  blocked_paths: ["/etc/**", "/sys/**"]
  max_file_size_mb: 500

timeout_seconds: 60

evidence_requirements:
  - name: command_invoked
    immutable: true
  - name: stdout
    sensitive: true
    immutable: true
  - name: exit_code
    immutable: true

replayability: non_deterministic

requires_approval: true
approval_reason: "Arbitrary code execution is high-risk"
```

### 2. Load and Validate

```python
from rif_runtime.capabilities.manifest_registry import ManifestRegistry, ManifestValidator

registry = ManifestRegistry("config/capabilities")
manifest = registry.load("shell_command")

# Check security
checks = ManifestValidator.check_all(manifest)
print(f"Risk: {checks['risk_score']}/10")
```

### 3. Policy Evaluation

```python
# At policy evaluation time:
if manifest.requires_approval:
    policy_decision = policy_engine.evaluate(
        actor=actor,
        capability=manifest,
        action="execute",
    )
    if policy_decision.decision == "deny":
        raise ExecutionError("Approval required")
```

### 4. Evidence Capture

```python
# During execution:
evidence = {}
for req in manifest.evidence_requirements:
    evidence[req.name] = capture(req.name)
    if req.sensitive:
        evidence[req.name] = redact(evidence[req.name])

audit_trail.record(manifest, evidence)
```

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/rif_runtime/schemas/capability.py` | 500 | Core manifest schema |
| `src/rif_runtime/schemas/capability_examples.py` | 600 | 5 real examples |
| `src/rif_runtime/capabilities/manifest_registry.py` | 500 | Registry & loader |
| `docs/CAPABILITY_MANIFESTS.md` | 550 | Validation & security |
| `docs/CAPABILITY_MANIFEST_SYSTEM.md` | 400 | Overview & guide |

**Total**: ~2,550 lines of code + documentation

---

## Benefits

✅ **Explicit Governance**: Policy engine knows all side effects upfront  
✅ **Auditability**: Complete evidence trail per manifest requirements  
✅ **Replay Safety**: Replayability semantics prevent accidental re-execution  
✅ **Least Privilege**: Restrictive access patterns by default  
✅ **Compliance**: Automated risk scoring and approval workflows  
✅ **Security**: Comprehensive threat model integration  
✅ **Developer Experience**: Clear examples and validation  
✅ **Versioning**: Semantic versioning with compatibility matrix  

---

## Next Steps

1. **Create manifest library**: Shell command, file I/O, API calls, etc.
2. **Policy templates**: Pre-built policies for common manifests
3. **CLI commands**: `rif capability list`, `rif capability validate`
4. **Cost tracking**: Enforce cost_estimate limits
5. **Monitoring**: Track usage, success rates, error patterns
6. **Integration tests**: Verify manifest side effects match implementation
7. **IDE support**: YAML schema for manifest authoring

---

## Conclusion

The **Capability Manifest System** shifts governance from reactive (after the fact) to **proactive (before execution)**. By making side effects explicit upfront, RIF Runtime enables:

- **Informed policy decisions** based on declared behaviors
- **Complete auditability** through evidence requirements
- **Safe replay** via replayability semantics
- **Least privilege** through restrictive access patterns
- **Compliance automation** via risk scoring

This design significantly improves security posture, auditability, and developer experience when building trustworthy agent runtimes.

---

**Status**: ✅ Complete and ready for use  
**Commit**: ebd856f (feat(capabilities): design and implement capability manifest system)  
**Branch**: agent/update-run-rif-runtime-skill
