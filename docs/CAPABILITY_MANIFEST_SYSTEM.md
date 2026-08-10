# Capability Manifest System - Design & Implementation

## Overview

RIF Runtime uses **capability manifests** to explicitly declare all observable behaviors, side effects, and access patterns. This enables:

- ✅ **Policy evaluation**: Decide whether to allow/deny based on declared side effects
- ✅ **Auditability**: Capture evidence per manifest requirements
- ✅ **Replay safety**: Understand replayability semantics before executing
- ✅ **Least privilege**: Enforce restrictive access patterns
- ✅ **Compliance**: Generate audit trails and risk reports

---

## What's Included

### 1. Schema (`src/rif_runtime/schemas/capability.py`)

**Core types**:
- `CapabilityManifest` — Complete manifest schema with validation
- `NetworkAccessSpec` — Declares network access patterns
- `FilesystemAccessSpec` — Declares filesystem access patterns
- `ExternalServiceSpec` — Declares external service integrations
- `EvidenceRequirement` — Specifies what evidence must be captured
- `CostEstimate` — Estimated cost/performance implications
- `SideEffectType` — Enumeration of all possible side effects
- `Replayability` — Semantics for safe replay

**Features**:
- Pydantic-based validation
- Cross-field validators (consistency checks)
- Semantic versioning enforcement
- Side effects vs category validation

### 2. Examples (`src/rif_runtime/schemas/capability_examples.py`)

Five real-world capability manifests:

| Capability | Category | Risk | Replays |
|-----------|----------|------|---------|
| **shell_command** | process | 9/10 | NON_DETERMINISTIC |
| **web_search** | network | 2/10 | NON_DETERMINISTIC |
| **file_write** | filesystem | 6/10 | IDEMPOTENT |
| **git_push** | external_service | 8/10 | NON_IDEMPOTENT |
| **http_api_call** | network | 4/10 | NON_DETERMINISTIC |

Each example shows:
- Side effects declared
- Access patterns restricted
- Evidence requirements
- Approval requirements
- Replayability semantics

### 3. Documentation (`docs/CAPABILITY_MANIFESTS.md`)

Comprehensive guide covering:
- **Validation rules** (schema, policy-level, compatibility matrix)
- **Security implications** (threat model integration, risk scoring)
- **Best practices** (do's and don'ts)
- **Manifest lifecycle** (creation through audit)
- **Examples** (good vs bad manifests)

### 4. Registry & Loader (`src/rif_runtime/capabilities/manifest_registry.py`)

**ManifestRegistry**:
- Discover manifests from filesystem
- Load and validate manifests
- Cache for performance
- Reload on changes
- Error tracking

**ManifestValidator**:
- Calculate risk score (1-10)
- Check least privilege violations
- Verify evidence completeness
- Validate all manifests in batch

---

## Key Design Decisions

### 1. Explicit Side Effects Declaration

Every manifest must declare **all observable behaviors**:

```yaml
side_effects:
  - network_egress        # Communicates externally
  - filesystem_write      # Creates/modifies files
  - external_service_mutation  # Changes external state
```

**Why**: Enables policy engine to make informed decisions without inspecting code.

### 2. Access Patterns are Restrictive by Default

Network and filesystem access must be explicitly whitelisted:

```yaml
network_access:
  allowed_domains:
    - "api.example.com"
    - "search.google.com"

filesystem_access:
  allowed_paths:
    - "/home/user/workspace/**"
    - "/tmp/**"
  blocked_paths:
    - "/etc/**"
    - "/sys/**"
```

**Why**: Prevents accidental over-privilege or privilege escalation.

### 3. Replayability Semantics are Explicit

Each manifest declares how safely it can be replayed:

```yaml
replayability: deterministic      # Same input → same output
# or
replayability: idempotent         # Safe to replay (e.g., mkdir -p)
# or
replayability: non_idempotent     # Replay may have different effects (e.g., API call)
# or
replayability: non_replayable      # Cannot safely replay (e.g., rm)
```

**Why**: Recovery engine knows whether it can safely re-execute for consistency.

### 4. Evidence Requirements are Manifest-Defined

Each manifest specifies what evidence must be captured:

```yaml
evidence_requirements:
  - name: command_invoked
    sensitive: false
    immutable: true
  - name: stdout
    sensitive: true        # May contain secrets; redact before logging
    immutable: true
  - name: exit_code
    sensitive: false
    immutable: true
```

**Why**: Enables policy-agnostic evidence capture; different manifests need different audit trails.

### 5. Risk Scoring is Automated

Risk score (1-10) calculated from manifest properties:

```
Base score: 1
+ mutates_state: 2
+ network_egress: 1
+ filesystem_write: 1
+ external_service_mutation: 2
+ credential_exposure: 3
+ privilege_escalation: 4
- deterministic_replayable: 1
```

**Why**: Enables policy prioritization; high-risk capabilities require explicit approval.

---

## Usage Examples

### Loading a Manifest

```python
from rif_runtime.capabilities.manifest_registry import ManifestRegistry

registry = ManifestRegistry("config/capabilities")

# Load specific manifest
shell_manifest = registry.load("shell_command")

# Load all manifests
all_manifests = registry.load_all()

# Validate
is_valid, error = registry.validate("shell_command")
```

### Validating at Policy Evaluation Time

```python
from rif_runtime.capabilities.manifest_registry import ManifestValidator

# Check security
checks = ManifestValidator.check_all(shell_manifest)

print(f"Risk score: {checks['risk_score']}/10")
print(f"Least privilege warnings: {checks['least_privilege_warnings']}")

# Decide whether to allow
if checks['risk_score'] > 7:
    # High risk; requires explicit policy approval
    policy_decision = evaluate_policy(actor, shell_manifest)
```

### Creating a Custom Manifest

```yaml
# config/capabilities/my_capability.yaml
name: my_capability
version: 1.0.0
description: "My custom capability description"
category: network

side_effects:
  - network_egress

mutates_state: false

network_access:
  enabled: true
  protocols: [HTTPS]
  allowed_domains:
    - "api.example.com"
  require_tls: true
  timeout_seconds: 30

filesystem_access:
  enabled: false

external_services:
  - name: my_api
    endpoint: "https://api.example.com"
    auth_required: true
    credentials_type: api_key
    mutation_allowed: false

timeout_seconds: 30
max_retries: 2

evidence_requirements:
  - name: api_request
    format: json
    sensitive: true
    immutable: true
  - name: api_response
    format: json
    sensitive: true
    immutable: true

replayability: deterministic

parameters:
  endpoint:
    type: string
    description: API endpoint
  data:
    type: object
    description: Request data

required_parameters: [endpoint, data]

requires_approval: false
```

---

## Integration with RIF Runtime

### 1. Policy Evaluation

```python
# At policy evaluation time:

manifest = registry.load("shell_command")

# Check against policy
policy_decision = policy_engine.evaluate(
    actor=actor,
    capability=manifest,
    intent=intent,
)

# High-risk capabilities may require approval
if manifest.requires_approval:
    if not user_approved:
        policy_decision.decision = "deny"
        policy_decision.reason = "requires approval"
```

### 2. Evidence Capture

```python
# During execution:

execution_result = executor.execute(capability_name, params)

# Capture evidence per manifest requirements
evidence = {}
for requirement in manifest.evidence_requirements:
    evidence[requirement.name] = get_evidence(requirement.name)
    
    # Redact sensitive evidence
    if requirement.sensitive:
        evidence[requirement.name] = redact(evidence[requirement.name])

# Store in audit trail
audit_trail.record_execution(
    capability_manifest=manifest,
    evidence=evidence,
)
```

### 3. Replay Safety

```python
# During recovery:

if manifest.replayability == Replayability.DETERMINISTIC:
    # Safe to replay; output will be identical
    replay_result = executor.replay(execution_id)
    assert replay_result == original_result
    
elif manifest.replayability == Replayability.NON_REPLAYABLE:
    # Cannot safely replay (e.g., file delete)
    # Skip replay; accept potential inconsistency
    logger.warning(f"Skipping replay for {manifest.name} (non-replayable)")
```

---

## Security Model

### Threat T1: Unauthorized Capability Invocation
**Mitigation**: `requires_approval=true` + policy evaluation

### Threat T2: Over-Privilege Execution
**Mitigation**: Restrictive `allowed_paths`, `allowed_domains`, `access_level`

### Threat T3: Data Exfiltration
**Mitigation**: Whitelist `allowed_domains`, block metadata services, capture network requests

### Threat T4: Credential Exposure
**Mitigation**: Mark evidence `sensitive=true`, enforce credential masking

### Threat T5: Side Effect Concealment
**Mitigation**: Exhaustive `side_effects` list, evidence capture, replay validation

### Threat T6: Denial of Service
**Mitigation**: `timeout_seconds`, `max_file_size_mb`, `max_retries`, rate limiting

### Threat T7: Privilege Escalation
**Mitigation**: Non-root execution, mark `PRIVILEGE_ESCALATION` as high-risk

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/rif_runtime/schemas/capability.py` | 500 | Core manifest schema |
| `src/rif_runtime/schemas/capability_examples.py` | 600 | 5 real-world examples |
| `docs/CAPABILITY_MANIFESTS.md` | 550 | Complete guide |
| `src/rif_runtime/capabilities/manifest_registry.py` | 500 | Registry + loader |

**Total**: ~2,150 lines of code + documentation

---

## Next Steps

1. **File Format Standardization**: YAML or JSON files in `config/capabilities/`
2. **CLI Integration**: `rif capability list`, `rif capability validate`
3. **Policy Templates**: Pre-built policy rules for common manifests
4. **Cost Tracking**: Enforce `cost_estimate` limits
5. **Monitoring**: Track manifest usage, success rates, error patterns
6. **Versioning**: Manifest version compatibility matrix in policy

---

## Benefits

✅ **Governance**: Policy engine knows exactly what each capability does  
✅ **Auditability**: Complete evidence trail per manifest  
✅ **Security**: Risk scoring and approval workflows  
✅ **Compliance**: Audit-ready documentation of all side effects  
✅ **Reproducibility**: Replayability semantics prevent inconsistency  
✅ **Least Privilege**: Restrictive defaults prevent over-access  
✅ **Developer Experience**: Clear examples and validation  

---

## Summary

Capability manifests represent a **declarative, policy-friendly approach to governance**. By making side effects explicit upfront, RIF Runtime enables:

- Informed policy decisions (allow/deny based on declared behaviors)
- Complete auditability (evidence captured per requirements)
- Safe replay (understanding replayability constraints)
- Least privilege (restrictive access by default)
- Compliance automation (risk scoring, approval workflows)

This design shifts governance from **reactive (after the fact) to proactive (before execution)**, significantly improving security posture and auditability.
