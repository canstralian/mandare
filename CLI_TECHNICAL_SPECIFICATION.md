# RIF Runtime v1.0 - CLI Technical Specification

**Version**: 1.0.0  
**Date**: 2025-01-15  
**Status**: Final Specification  
**Language Choice**: Go 1.21+  

---

## Table of Contents

1. [Language Choice & Justification](#language-choice--justification)
2. [Command Specification](#command-specification)
3. [Example Sessions](#example-sessions)
4. [Error Handling](#error-handling)
5. [CI Integration](#ci-integration)
6. [Package Structure](#package-structure)
7. [Code Quality](#code-quality)
8. [Testing Strategy](#testing-strategy)
9. [Edge Cases](#edge-cases)
10. [Assumptions](#assumptions)
11. [Verification Checklist](#verification-checklist)

---

## Language Choice & Justification

### Selected: Go 1.21+

**Rationale**:

| Criterion | Go | Rust | Node.js |
|-----------|----|----|---------|
| **CLI maturity** | ✅ Excellent (Cobra, pflag) | ✅ Excellent (clap) | ⚠️ Less idiomatic |
| **Binary size** | ✅ 5-10MB single file | ✅ 3-8MB (smaller) | ❌ 50MB+ (Node runtime) |
| **Startup latency** | ✅ <5ms | ✅ <5ms | ❌ 100-200ms |
| **Cross-platform** | ✅ Single binary | ✅ Single binary | ⚠️ Requires Node.js |
| **JSON handling** | ✅ Excellent (encoding/json) | ✅ Excellent (serde_json) | ✅ Native |
| **Learning curve** | ✅ Easy | ❌ Steep | ✅ Medium |
| **Concurrency** | ✅ Goroutines | ✅ Threads | ⚠️ Event-loop |
| **CI/pipeline use** | ✅ Perfect (single binary) | ✅ Good | ⚠️ Requires runtime |
| **Tooling** | ✅ Built-in (fmt, test) | ✅ Excellent (cargo) | ⚠️ Fragmented (npm/yarn) |

**Decision**: Go maximizes CI/pipeline utility (single binary, fast startup, zero runtime dependencies). Rust would be acceptable but adds compilation complexity; Node.js penalizes CI runners.

**Dependencies** (minimal):
```go
require (
    github.com/spf13/cobra v1.7.0
    github.com/spf13/pflag v1.0.5
)
```

---

# 1. Command Specification

## 1.1 Exit Code Enum

All commands return standardized exit codes:

```go
const (
    // Success
    ExitOK = 0

    // Errors
    ExitRuntimeError       = 1  // Unexpected runtime error (IO, panic, etc.)
    ExitUsageError         = 2  // Usage/parsing error (missing arg, invalid flag)
    ExitPolicyViolation    = 3  // Policy evaluation returned deny
    ExitVerificationFailure = 4  // Verification failed (hash mismatch, schema invalid)
    ExitNotFound           = 5  // Resource not found (file missing, replay ID invalid)
    ExitConflict           = 6  // Conflicting state (already exists, incompatible versions)
    ExitInternalError      = 7  // Unrecoverable internal error (bug)
)
```

---

## 1.2 Global Flags

**All commands support**:

```bash
--json                # Output strict JSON (schema v1) to stdout
--json-schema-version # Print JSON schema version and exit
--verbose             # Include debug logging on stderr
--config FILE         # Load configuration from FILE (YAML or JSON)
--version             # Print version and exit
--help                # Print help and exit
```

**Default behavior**: Human-readable output; colors only if stdout is TTY.

---

## 1.3 `rif run` Command

### Purpose
Execute a RIF Runtime decision: evaluate policy against an intent, capture evidence, record decision.

### Usage

```bash
rif run [FLAGS] [OPTIONS] ACTOR ACTION TARGET

# Positional arguments
ACTOR              # Actor ID (e.g., "agent:orchestrator")
ACTION             # Action name (e.g., "http.request")
TARGET             # Target resource (e.g., "https://api.example.com")

# Options
-p, --policy FILE           # Policy configuration file (required if no --config)
-c, --capability FILE       # Capability manifest file (optional, may be embedded in policy)
--timeout SECONDS           # Execution timeout (default: 30)
--sandbox-level LEVEL       # Sandbox isolation: read_only|standard|permissive (default: standard)
--env KEY=VALUE             # Set environment variable (repeatable)
--output FILE               # Write decision JSON to FILE (default: stdout for --json, human-readable to stdout)
--evidence-dir DIR          # Directory to persist evidence artifacts (default: ./evidence)

# Global flags (see 1.2)
--json
--verbose
--config FILE
--version
--help
```

### Input Files

**Policy file format** (YAML or JSON):
```yaml
# policy.yaml
version: "1.0"
rules:
  - id: "allow_trusted"
    priority: 100
    condition: 'actor in ["agent:test", "agent:trusted"]'
    effect: "allow"
  - id: "deny_default"
    priority: 0
    condition: "true"
    effect: "deny"
```

**Capability manifest** (optional, may be embedded or external):
```yaml
# capability.yaml
name: "http_request"
version: "1.0.0"
category: "network"
side_effects: ["network_egress"]
mutates_state: false
network_access:
  enabled: true
  protocols: ["https"]
  allowed_domains: ["api.example.com", "api.openai.com"]
  timeout_seconds: 30
```

### Output Schema

**Human-readable (default)**:
```
Decision: ALLOW
Reason: policy rule 'allow_trusted' matched
Actor: agent:test
Action: http.request
Target: https://api.example.com
Timestamp: 2025-01-15T10:30:00Z
DecisionID: dec_abc123
Duration: 45ms

Evidence:
  - policy_evaluation.json (125 bytes)
  - network_request.json (512 bytes)
  - posture_snapshot.json (89 bytes)
```

**JSON output** (`--json` flag):
```json
{
  "schemaVersion": "1.0",
  "decision": "allow",
  "reason": "policy rule 'allow_trusted' matched",
  "actor": "agent:test",
  "action": "http.request",
  "target": "https://api.example.com",
  "timestamp": "2025-01-15T10:30:00Z",
  "decisionId": "dec_abc123",
  "durationMs": 45,
  "evidence": {
    "policy_evaluation": {
      "format": "json",
      "path": "evidence/dec_abc123/policy_evaluation.json",
      "sizeBytes": 125,
      "hash": "sha256:abc123..."
    },
    "network_request": {
      "format": "json",
      "path": "evidence/dec_abc123/network_request.json",
      "sizeBytes": 512,
      "hash": "sha256:def456..."
    },
    "posture_snapshot": {
      "format": "json",
      "path": "evidence/dec_abc123/posture_snapshot.json",
      "sizeBytes": 89,
      "hash": "sha256:ghi789..."
    }
  },
  "error": null
}
```

### Exit Codes

| Code | Condition |
|------|-----------|
| 0 | Decision successfully evaluated (allow or deny) |
| 2 | Missing required argument (ACTOR, ACTION, TARGET) or invalid flag |
| 3 | Policy evaluation resulted in DENY |
| 5 | Policy file not found or policy version unsupported |
| 1 | Unexpected runtime error (IO, policy parse failure, etc.) |

---

## 1.4 `rif replay` Command

### Purpose
Replay a past decision deterministically using recorded evidence and governance state.

### Usage

```bash
rif replay [FLAGS] [OPTIONS] DECISION_ID

# Positional arguments
DECISION_ID         # Decision ID to replay (e.g., "dec_abc123")

# Options
--evidence-dir DIR      # Directory containing evidence (default: ./evidence)
--policy FILE           # Policy file to apply (optional; uses recorded policy if omitted)
--dry-run               # Simulate replay without persisting (default: false)
--output FILE           # Write replayed decision to FILE (default: stdout)
--compare-original      # Compare replayed vs. original; exit 4 if different

# Global flags (see 1.2)
--json
--verbose
--config FILE
```

### Input Files

**Evidence bundle structure** (from `rif run`):
```
evidence/
├── dec_abc123/
│   ├── policy_evaluation.json
│   ├── network_request.json
│   ├── posture_snapshot.json
│   ├── governance_graph.json
│   └── manifest.json                # Decision metadata
```

### Output Schema

**Human-readable (default)**:
```
Replay: DETERMINISTIC
Original Decision: dec_abc123 (allow)
Replayed Decision: dec_abc123_replay (allow)
Status: ✓ IDENTICAL

Original Timestamp: 2025-01-15T10:30:00Z
Replayed Timestamp: 2025-01-15T10:35:15Z
Hashes Match: ✓ yes
Duration (original): 45ms
Duration (replay): 42ms
```

**JSON output**:
```json
{
  "schemaVersion": "1.0",
  "originalDecisionId": "dec_abc123",
  "replayedDecisionId": "dec_abc123_replay",
  "status": "deterministic",
  "originalHash": "sha256:abc123...",
  "replayedHash": "sha256:abc123...",
  "hashesMatch": true,
  "originalTimestamp": "2025-01-15T10:30:00Z",
  "replayedTimestamp": "2025-01-15T10:35:15Z",
  "originalDurationMs": 45,
  "replayedDurationMs": 42,
  "error": null
}
```

### Exit Codes

| Code | Condition |
|------|-----------|
| 0 | Replay succeeded; hashes match |
| 2 | Missing DECISION_ID or invalid flag |
| 4 | Replay succeeded but hashes differ (when --compare-original) |
| 5 | Evidence not found or corrupted |
| 1 | Unexpected runtime error |

---

## 1.5 `rif verify` Command

### Purpose
Verify that a decision (or set of decisions) meets governance and compliance criteria.

### Usage

```bash
rif verify [FLAGS] [OPTIONS] [DECISION_ID]

# Positional arguments (optional)
DECISION_ID         # Specific decision ID; if omitted, verify all in evidence-dir

# Options
--evidence-dir DIR          # Directory containing evidence (default: ./evidence)
--schema FILE               # JSON schema to validate against (optional)
--policy FILE               # Policy file for re-evaluation (optional)
--compliance-rules FILE     # Compliance rules (e.g., no external network access)
--fail-fast                 # Exit on first failure (default: continue and report all)
--output FILE               # Write verification report to FILE (default: stdout)

# Global flags (see 1.2)
--json
--verbose
--config FILE
```

### Input Files

**Compliance rules file** (YAML or JSON):
```yaml
# compliance.yaml
version: "1.0"
rules:
  - id: "no_external_network"
    type: "side_effect_forbidden"
    side_effects: ["network_egress"]
    message: "External network access not allowed"
    
  - id: "policy_matched"
    type: "policy_rule_required"
    policy_rules: ["allow_trusted"]
    message: "Decision must match 'allow_trusted' policy rule"
    
  - id: "within_timeout"
    type: "latency_check"
    max_duration_ms: 100
    message: "Execution must complete within 100ms"
```

### Output Schema

**Human-readable (default)**:
```
Verification Report
═════════════════════════════════════════════

Decisions Verified: 5
Passed: 5
Failed: 0
Skipped: 0

Results:
  ✓ dec_abc123    policy matched
  ✓ dec_def456    no external network access
  ✓ dec_ghi789    execution within timeout
  ✓ dec_jkl012    schema valid
  ✓ dec_mno345    hash verified

Status: PASSED
```

**JSON output**:
```json
{
  "schemaVersion": "1.0",
  "status": "passed",
  "totalDecisions": 5,
  "passed": 5,
  "failed": 0,
  "skipped": 0,
  "decisions": [
    {
      "decisionId": "dec_abc123",
      "status": "passed",
      "checks": [
        {"checkId": "policy_matched", "status": "passed", "message": null}
      ]
    },
    {
      "decisionId": "dec_def456",
      "status": "passed",
      "checks": [
        {"checkId": "no_external_network", "status": "passed", "message": null}
      ]
    }
  ],
  "error": null
}
```

### Exit Codes

| Code | Condition |
|------|-----------|
| 0 | All verifications passed |
| 2 | Invalid flag or DECISION_ID format |
| 4 | Verification failed (see report for details) |
| 5 | Evidence file not found |
| 1 | Unexpected runtime error |

---

## 1.6 `rif inspect` Command

### Purpose
Inspect and display the contents of a decision, evidence artifact, or policy/capability file.

### Usage

```bash
rif inspect [FLAGS] [OPTIONS] PATH

# Positional arguments
PATH                # File or directory to inspect
                    # - Decision ID (e.g., "dec_abc123") searches evidence-dir
                    # - File path (e.g., "evidence/dec_abc123/policy_eval.json")
                    # - Policy/capability file

# Options
--evidence-dir DIR      # Search for decision IDs in this directory (default: ./evidence)
--format FORMAT         # Output format: auto|json|yaml (default: auto)
--validate              # Validate against schema (default: false)
--schema FILE           # Custom schema for validation (optional)
--show-sensitive        # Include sensitive fields (default: false, redacted)
--output FILE           # Write to FILE (default: stdout)

# Global flags (see 1.2)
--json
--verbose
--config FILE
```

### Output Schema

**Human-readable (default, decision)**:
```
Decision: dec_abc123
═════════════════════════════════════════════

Status: ALLOW
Timestamp: 2025-01-15T10:30:00Z
Duration: 45ms

Actor: agent:test
Action: http.request
Target: https://api.example.com

Policy Matched: allow_trusted
Policy Rule ID: allow_trusted (priority: 100)

Artifacts:
  1. policy_evaluation.json (125 bytes)
  2. network_request.json (512 bytes)
  3. posture_snapshot.json (89 bytes)
  4. governance_graph.json (2.1 KB)

Hashes:
  Decision hash: sha256:abc123...
  Governance graph hash: sha256:def456...
  Posture snapshot hash: sha256:ghi789...
```

**JSON output**:
```json
{
  "schemaVersion": "1.0",
  "type": "decision",
  "decisionId": "dec_abc123",
  "decision": "allow",
  "timestamp": "2025-01-15T10:30:00Z",
  "durationMs": 45,
  "actor": "agent:test",
  "action": "http.request",
  "target": "https://api.example.com",
  "policyMatched": "allow_trusted",
  "artifacts": [
    {"name": "policy_evaluation.json", "sizeBytes": 125, "hash": "sha256:abc123..."},
    {"name": "network_request.json", "sizeBytes": 512, "hash": "sha256:def456..."}
  ],
  "error": null
}
```

### Exit Codes

| Code | Condition |
|------|-----------|
| 0 | Successfully inspected |
| 2 | Invalid flag |
| 5 | Path not found |
| 1 | Unexpected runtime error |

---

## 1.7 `rif policy` Command

### Purpose
Manage, validate, and test policy files.

### Usage

```bash
rif policy [SUBCOMMAND] [FLAGS] [OPTIONS]

# Subcommands
rif policy validate FILE        # Validate policy file syntax and schema
rif policy test FILE            # Test policy with sample inputs
rif policy show FILE            # Display policy in human-readable form
rif policy lint FILE            # Check policy for best practices

# Global flags for all subcommands
--json
--verbose
--config FILE
```

### 1.7.1 `rif policy validate`

```bash
rif policy validate [FLAGS] [OPTIONS] FILE

# Options
--schema FILE           # Custom schema (optional)
--rules-dir DIR         # Directory containing reusable rule snippets

# Global flags (see 1.2)
--json
```

**Human-readable output**:
```
Policy Validation
═════════════════════════════════════════════

File: policy.yaml
Version: 1.0
Rules: 5
Status: ✓ VALID

Rules:
  1. allow_trusted        (priority: 100)   ✓ valid
  2. deny_external_api    (priority: 50)    ✓ valid
  3. deny_default         (priority: 0)     ✓ valid
  4. audit_all_network    (priority: 75)    ✓ valid
  5. sandbox_strict       (priority: 90)    ✓ valid

Warnings: 0
Errors: 0
```

**JSON output**:
```json
{
  "schemaVersion": "1.0",
  "status": "valid",
  "file": "policy.yaml",
  "policyVersion": "1.0",
  "ruleCount": 5,
  "errors": [],
  "warnings": [],
  "error": null
}
```

### 1.7.2 `rif policy test`

```bash
rif policy test [FLAGS] [OPTIONS] FILE TEST_CASE_FILE

# Options
--fail-fast         # Exit on first failure (default: continue)
--output FILE       # Write report to FILE

# Test case file format (YAML/JSON)
tests:
  - name: "allow_trusted_agent"
    actor: "agent:trusted"
    action: "http.request"
    target: "https://api.example.com"
    expectedDecision: "allow"
    
  - name: "deny_untrusted_agent"
    actor: "agent:untrusted"
    action: "http.request"
    target: "https://blocked.example.com"
    expectedDecision: "deny"
```

**Human-readable output**:
```
Policy Test Results
═════════════════════════════════════════════

File: policy.yaml
Test cases: 2
Passed: 2
Failed: 0

Test Results:
  ✓ allow_trusted_agent          (ALLOW matches expected)
  ✓ deny_untrusted_agent         (DENY matches expected)
```

### 1.7.3 `rif policy show`

```bash
rif policy show [FLAGS] FILE

# Output: formatted policy rules
```

### 1.7.4 `rif policy lint`

```bash
rif policy lint [FLAGS] FILE

# Checks for:
# - Unreachable rules (shadowed by higher-priority rules)
# - Unused conditions
# - Overly broad wildcard conditions
# - Performance warnings
```

### Exit Codes (all subcommands)

| Code | Condition |
|------|-----------|
| 0 | Success (validation passed, tests passed, etc.) |
| 2 | Invalid flag |
| 4 | Validation failed / Tests failed |
| 5 | File not found |
| 1 | Unexpected runtime error |

---

## 1.8 `rif evidence` Command

### Purpose
Manage, export, and audit evidence artifacts.

### Usage

```bash
rif evidence [SUBCOMMAND] [FLAGS] [OPTIONS]

# Subcommands
rif evidence list [DIR]                 # List all evidence in directory
rif evidence export DECISION_ID FILE     # Export decision bundle (ZIP or TAR)
rif evidence delete DECISION_ID          # Delete evidence for decision
rif evidence audit [OPTIONS] [DIR]       # Audit evidence for integrity/compliance
rif evidence query [OPTIONS]             # Query evidence with filters
```

### 1.8.1 `rif evidence list`

```bash
rif evidence list [FLAGS] [OPTIONS] [DIR]

# Options
--sort FIELD            # Sort by: timestamp|actor|decision (default: timestamp)
--filter QUERY          # Filter: "actor:agent:test decision:allow" (optional)
--limit N               # Limit results (default: 100)
--output FILE           # Write to FILE

# Global flags
--json
```

**Human-readable output**:
```
Evidence Summary
═════════════════════════════════════════════

Directory: ./evidence
Total decisions: 42
Decisions (last 5):

ID              Timestamp               Actor               Decision  Duration
dec_abc123      2025-01-15 10:30:00Z    agent:test          allow     45ms
dec_def456      2025-01-15 10:29:15Z    agent:trusted       allow     38ms
dec_ghi789      2025-01-15 10:28:30Z    agent:untrusted     deny      22ms
dec_jkl012      2025-01-15 10:27:45Z    agent:test          allow     51ms
dec_mno345      2025-01-15 10:27:00Z    agent:orchestrator  deny      19ms
```

**JSON output**:
```json
{
  "schemaVersion": "1.0",
  "directory": "./evidence",
  "totalDecisions": 42,
  "decisions": [
    {
      "decisionId": "dec_abc123",
      "timestamp": "2025-01-15T10:30:00Z",
      "actor": "agent:test",
      "decision": "allow",
      "durationMs": 45
    }
  ],
  "error": null
}
```

### 1.8.2 `rif evidence export`

```bash
rif evidence export [FLAGS] [OPTIONS] DECISION_ID OUTPUT_FILE

# Options
--format FORMAT         # zip|tar|tar.gz (default: zip)
--include-sensitive     # Include sensitive fields (default: redacted)
--output-dir DIR        # Override output directory

# Output: compressed bundle with all artifacts, metadata, hashes
```

**Bundle contents**:
```
evidence_bundle.zip
├── manifest.json                        # Metadata
├── decision.json
├── policy_evaluation.json
├── network_request.json
├── posture_snapshot.json
├── governance_graph.json
└── hashes.json                          # SHA256 hashes for verification
```

### 1.8.3 `rif evidence audit`

```bash
rif evidence audit [FLAGS] [OPTIONS] [DIR]

# Options
--check-hashes          # Verify SHA256 hashes (default: true)
--check-schema          # Validate JSON schema (default: true)
--check-timestamps      # Verify timestamp ordering (default: false)
--repair                # Attempt to repair corrupted files (default: false)
```

**Human-readable output**:
```
Evidence Audit Report
═════════════════════════════════════════════

Directory: ./evidence
Files scanned: 126
Status: ✓ PASSED

Checks:
  ✓ Hash verification      (126 files, all valid)
  ✓ Schema validation      (126 files, all valid)
  ✓ Timestamp ordering     (passed)
  ✓ No corruption          (passed)

Summary: All evidence artifacts are valid and unmodified.
```

### 1.8.4 `rif evidence query`

```bash
rif evidence query [FLAGS] [OPTIONS]

# Options
--actor PATTERN         # Filter by actor (supports wildcards)
--action PATTERN        # Filter by action
--decision DECISION     # Filter by decision (allow|deny)
--since TIMESTAMP       # Results after timestamp (RFC3339)
--until TIMESTAMP       # Results before timestamp
--limit N               # Limit results (default: 100)
--output FILE           # Write to FILE
```

### Exit Codes (all subcommands)

| Code | Condition |
|------|-----------|
| 0 | Success |
| 2 | Invalid flag or DECISION_ID |
| 4 | Audit failed / Corruption detected |
| 5 | Directory/file not found |
| 1 | Unexpected runtime error |

---

# 2. Example Sessions

All examples show **exit code**, **stderr**, **stdout**.

---

## 2.1 `rif run` — Normal Session (Human-Readable)

```bash
$ rif run --policy policy.yaml agent:test http.request https://api.example.com
Decision: ALLOW
Reason: policy rule 'allow_trusted' matched
Actor: agent:test
Action: http.request
Target: https://api.example.com
Timestamp: 2025-01-15T10:30:00Z
DecisionID: dec_abc123
Duration: 45ms

Evidence:
  - policy_evaluation.json (125 bytes)
  - network_request.json (512 bytes)
  - posture_snapshot.json (89 bytes)
  - governance_graph.json (2.1 KB)

$ echo $?
0
```

---

## 2.2 `rif run` — Same Session with `--json`

```bash
$ rif run --policy policy.yaml --json agent:test http.request https://api.example.com
{
  "schemaVersion": "1.0",
  "decision": "allow",
  "reason": "policy rule 'allow_trusted' matched",
  "actor": "agent:test",
  "action": "http.request",
  "target": "https://api.example.com",
  "timestamp": "2025-01-15T10:30:00Z",
  "decisionId": "dec_abc123",
  "durationMs": 45,
  "evidence": {
    "policy_evaluation": {
      "format": "json",
      "path": "evidence/dec_abc123/policy_evaluation.json",
      "sizeBytes": 125,
      "hash": "sha256:abc123def456..."
    },
    "network_request": {
      "format": "json",
      "path": "evidence/dec_abc123/network_request.json",
      "sizeBytes": 512,
      "hash": "sha256:fed789abc123..."
    }
  },
  "error": null
}

$ echo $?
0
```

---

## 2.3 `rif run` — Policy Violation

```bash
$ rif run --policy policy.yaml agent:untrusted http.request https://blocked.example.com
Decision: DENY
Reason: policy default rule (no allow rule matched)
Actor: agent:untrusted
Action: http.request
Target: https://blocked.example.com
Timestamp: 2025-01-15T10:31:00Z
DecisionID: dec_def456
Duration: 22ms

$ echo $?
3
```

---

## 2.4 `rif run` — Usage Error (Missing Argument)

```bash
$ rif run --policy policy.yaml agent:test
Usage: rif run [FLAGS] [OPTIONS] ACTOR ACTION TARGET

Error: missing required positional argument ACTION

Run 'rif run --help' for usage information.

$ echo $?
2
```

**Note**: Error message on stderr, usage hint on stderr.

---

## 2.5 `rif verify` — Successful Verification

```bash
$ rif verify --evidence-dir ./evidence --compliance-rules compliance.yaml
Verification Report
═════════════════════════════════════════════

Decisions Verified: 5
Passed: 5
Failed: 0
Skipped: 0

Results:
  ✓ dec_abc123    policy matched
  ✓ dec_def456    no external network access
  ✓ dec_ghi789    execution within timeout
  ✓ dec_jkl012    schema valid
  ✓ dec_mno345    hash verified

Status: PASSED

$ echo $?
0
```

---

## 2.6 `rif verify` — Verification Failure

```bash
$ rif verify --evidence-dir ./evidence --compliance-rules compliance.yaml
Verification Report
═════════════════════════════════════════════

Decisions Verified: 5
Passed: 3
Failed: 2
Skipped: 0

Results:
  ✓ dec_abc123    policy matched
  ✓ dec_def456    no external network access
  ✗ dec_ghi789    TIMEOUT: execution took 150ms (max: 100ms)
  ✓ dec_jkl012    schema valid
  ✗ dec_mno345    POLICY VIOLATION: unexpected rule matched

Status: FAILED

$ echo $?
4
```

---

## 2.7 `rif replay` — Deterministic Replay

```bash
$ rif replay --evidence-dir ./evidence --compare-original dec_abc123
Replay: DETERMINISTIC
Original Decision: dec_abc123 (allow)
Replayed Decision: dec_abc123_replay (allow)
Status: ✓ IDENTICAL

Original Timestamp: 2025-01-15T10:30:00Z
Replayed Timestamp: 2025-01-15T10:35:15Z
Hashes Match: ✓ yes
Duration (original): 45ms
Duration (replay): 42ms

$ echo $?
0
```

---

## 2.8 `rif inspect` — Inspect Decision

```bash
$ rif inspect dec_abc123
Decision: dec_abc123
═════════════════════════════════════════════

Status: ALLOW
Timestamp: 2025-01-15T10:30:00Z
Duration: 45ms

Actor: agent:test
Action: http.request
Target: https://api.example.com

Policy Matched: allow_trusted
Policy Rule ID: allow_trusted (priority: 100)

Artifacts:
  1. policy_evaluation.json (125 bytes)
  2. network_request.json (512 bytes)
  3. posture_snapshot.json (89 bytes)
  4. governance_graph.json (2.1 KB)

Hashes:
  Decision hash: sha256:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz...
  Governance graph hash: sha256:def456ghi789jkl012mno345pqr678stu901vwx234yz...
  Posture snapshot hash: sha256:ghi789jkl012mno345pqr678stu901vwx234yz...

$ echo $?
0
```

---

## 2.9 `rif policy` — Policy Validation

```bash
$ rif policy validate policy.yaml
Policy Validation
═════════════════════════════════════════════

File: policy.yaml
Version: 1.0
Rules: 5
Status: ✓ VALID

Rules:
  1. allow_trusted        (priority: 100)   ✓ valid
  2. deny_external_api    (priority: 50)    ✓ valid
  3. deny_default         (priority: 0)     ✓ valid
  4. audit_all_network    (priority: 75)    ✓ valid
  5. sandbox_strict       (priority: 90)    ✓ valid

Warnings: 0
Errors: 0

$ echo $?
0
```

---

## 2.10 `rif evidence` — List Evidence

```bash
$ rif evidence list ./evidence
Evidence Summary
═════════════════════════════════════════════

Directory: ./evidence
Total decisions: 42
Decisions (last 5):

ID              Timestamp               Actor               Decision  Duration
dec_abc123      2025-01-15 10:30:00Z    agent:test          allow     45ms
dec_def456      2025-01-15 10:29:15Z    agent:trusted       allow     38ms
dec_ghi789      2025-01-15 10:28:30Z    agent:untrusted     deny      22ms
dec_jkl012      2025-01-15 10:27:45Z    agent:test          allow     51ms
dec_mno345      2025-01-15 10:27:00Z    agent:orchestrator  deny      19ms

$ echo $?
0
```

---

## 2.11 `rif evidence` — Audit Evidence

```bash
$ rif evidence audit ./evidence
Evidence Audit Report
═════════════════════════════════════════════

Directory: ./evidence
Files scanned: 126
Status: ✓ PASSED

Checks:
  ✓ Hash verification      (126 files, all valid)
  ✓ Schema validation      (126 files, all valid)
  ✓ Timestamp ordering     (passed)
  ✓ No corruption          (passed)

Summary: All evidence artifacts are valid and unmodified.

$ echo $?
0
```

---

# 3. Error Handling

## 3.1 Error Taxonomy

```go
// Error types (internal classification)

// UsageError: user provided invalid arguments, flags, or syntax
type UsageError struct {
    Message string
    Hint    string  // Suggestion for fix
}

// ValidationError: input file is malformed, schema invalid, etc.
type ValidationError struct {
    Field   string
    Message string
    Details string  // Line number, character position, etc.
}

// IOError: file not found, permission denied, disk full, etc.
type IOError struct {
    Operation string  // "read", "write", "create_dir"
    Path      string
    Cause     error
}

// RuntimeError: unexpected execution error (panic, goroutine failure, etc.)
type RuntimeError struct {
    Message string
    Details string  // Stack trace in verbose mode
}

// DomainError: policy violation, verification failure, etc.
type DomainError struct {
    Code    string  // "policy_violation", "verify_failed", "hash_mismatch"
    Message string
    Details map[string]interface{}
}

// NotFoundError: resource does not exist
type NotFoundError struct {
    ResourceType string  // "policy", "evidence", "decision"
    Identifier   string
}
```

## 3.2 Human-Readable Error Output

**Format** (on stderr):

```
Error: <Message>

Details:
  <Additional context>

Hint: <Suggestion for fix>

Run 'rif <command> --help' for usage information.
```

**Example**:
```bash
$ rif run --policy nonexistent.yaml agent:test http.request https://api.example.com 2>&1
Error: policy file not found: nonexistent.yaml

Details:
  Searched in:
    - nonexistent.yaml (current directory)
    - /etc/rif/nonexistent.yaml (system config)

Hint: Use --policy <path> to specify the policy file location.

Run 'rif run --help' for usage information.
```

## 3.3 JSON Error Output

**Format** (when `--json` flag present):

```json
{
  "schemaVersion": "1.0",
  "error": {
    "code": "file_not_found",
    "message": "policy file not found: nonexistent.yaml",
    "type": "IOError",
    "details": {
      "resourceType": "policy",
      "searchPaths": [
        "nonexistent.yaml",
        "/etc/rif/nonexistent.yaml"
      ]
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Error codes** (comprehensive list):

```
file_not_found
file_read_error
file_write_error
file_permission_denied
invalid_json
invalid_yaml
schema_validation_failed
policy_violation
verify_failed
hash_mismatch
decision_not_found
timeout
resource_conflict
internal_error
unknown_error
```

## 3.4 Stderr vs. Stdout

| Stream | Content |
|--------|---------|
| **stdout** | Successful results (human-readable or JSON) |
| **stderr** | Error messages, warnings, debug logs (when `--verbose`) |

**Example**:
```bash
$ rif run --verbose --policy policy.yaml agent:test http.request https://api.example.com 2>err.log
# stdout: human-readable decision
# stderr (err.log): verbose debug logs
```

## 3.5 File Format Errors

**Unsupported version**:
```
Error: policy version not supported: 2.0

Supported versions: 1.0

Details:
  File: policy.yaml (line 2)
  Found: version: "2.0"
  Expected: version: "1.0"

Hint: Update the policy file or upgrade RIF Runtime.
```

**Malformed JSON**:
```
Error: invalid JSON in policy file

Details:
  File: policy.yaml (line 15, column 8)
  Unexpected character: }
  Context: "rules": [{ "id": "test", }

Hint: Check for trailing commas or missing closing brackets.
```

**Schema validation**:
```
Error: policy schema validation failed

Details:
  Rule 'allow_trusted' (line 5):
    - Missing required field: 'effect'
    - Invalid field 'condition': expected string, got number

Hint: See 'rif policy validate policy.yaml --json' for detailed report.
```

---

# 4. CI Integration

## 4.1 GitHub Actions Example

```yaml
name: RIF Runtime Policy Evaluation

on:
  pull_request:
    paths:
      - 'policy.yaml'
      - 'compliance.yaml'

jobs:
  rif-evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Download rif binary (or build from source)
      - name: Install RIF Runtime
        run: |
          wget https://releases.rif-runtime.io/rif-v1.0.0-linux-x64 -O rif
          chmod +x rif
      
      # Validate policy
      - name: Validate policy
        run: ./rif policy validate policy.yaml --json > policy_validation.json
        continue-on-error: false
      
      # Run policy evaluation on sample inputs
      - name: Test policy
        run: |
          ./rif policy test policy.yaml test_cases.yaml --json > policy_test_results.json
        continue-on-error: false
      
      # Verify compliance
      - name: Verify compliance
        run: |
          ./rif verify \
            --evidence-dir ./evidence \
            --compliance-rules compliance.yaml \
            --json > verify_report.json
        continue-on-error: false
      
      # Parse results and comment on PR
      - name: Comment on PR
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const validate = JSON.parse(fs.readFileSync('policy_validation.json'));
            const test = JSON.parse(fs.readFileSync('policy_test_results.json'));
            const verify = JSON.parse(fs.readFileSync('verify_report.json'));
            
            const status = validate.status === 'valid' && test.status === 'passed' && verify.status === 'passed'
              ? '✓ PASSED'
              : '✗ FAILED';
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## RIF Runtime Policy Evaluation\n\n**Status**: ${status}\n\n- Validation: ${validate.status}\n- Test cases: ${test.passed}/${test.totalTests} passed\n- Compliance: ${verify.passed}/${verify.totalDecisions} passed`
            });
```

---

## 4.2 GitLab CI Example

```yaml
rif-policy-validation:
  stage: test
  image: rif-runtime:latest
  script:
    - rif policy validate policy.yaml --json > validation.json
    - rif policy test policy.yaml test_cases.yaml --json > test_results.json
    - |
      if [ "$(jq -r '.status' validation.json)" != "valid" ]; then
        echo "Policy validation failed"
        exit 4
      fi
    - |
      if [ "$(jq -r '.status' test_results.json)" != "passed" ]; then
        echo "Policy tests failed"
        exit 4
      fi
  artifacts:
    reports:
      dotenv: validation.json
    paths:
      - validation.json
      - test_results.json
  allow_failure: false
```

---

## 4.3 Shell Pipeline Example

```bash
#!/bin/bash
set -e

POLICY_FILE="policy.yaml"
EVIDENCE_DIR="./evidence"

echo "Step 1: Validate policy"
rif policy validate "$POLICY_FILE" --json > /tmp/validation.json
if [ "$(jq -r '.status' /tmp/validation.json)" != "valid" ]; then
    echo "❌ Policy validation failed"
    jq . /tmp/validation.json
    exit 1
fi
echo "✓ Policy is valid"

echo "Step 2: Run policy tests"
rif policy test "$POLICY_FILE" test_cases.yaml --json > /tmp/test_results.json
PASSED=$(jq -r '.passed' /tmp/test_results.json)
TOTAL=$(jq -r '.totalTests' /tmp/test_results.json)
if [ "$PASSED" != "$TOTAL" ]; then
    echo "❌ Policy tests failed: $PASSED/$TOTAL passed"
    jq . /tmp/test_results.json
    exit 1
fi
echo "✓ All policy tests passed ($PASSED/$TOTAL)"

echo "Step 3: Verify evidence compliance"
rif verify "$EVIDENCE_DIR" --compliance-rules compliance.yaml --json > /tmp/verify_report.json
if [ "$(jq -r '.status' /tmp/verify_report.json)" != "passed" ]; then
    echo "❌ Verification failed"
    jq . /tmp/verify_report.json
    exit 1
fi
echo "✓ All evidence is compliant"

echo ""
echo "✓ All RIF Runtime checks passed"
```

---

## 4.4 JSON Output Parsing with `jq`

**Extract decision from JSON**:
```bash
$ rif run --policy policy.yaml --json agent:test http.request https://api.example.com | jq '.decision'
"allow"

$ rif run --policy policy.yaml --json agent:test http.request https://api.example.com | jq '.decisionId'
"dec_abc123"
```

**Conditional logic**:
```bash
$ if [ "$(rif verify --json --evidence-dir ./evidence | jq -r '.status')" = "passed" ]; then
>   echo "✓ Verification passed"
> else
>   echo "✗ Verification failed"
>   exit 1
> fi
```

**Extract error code**:
```bash
$ rif run --policy nonexistent.yaml --json agent:test http.request https://api.example.com 2>/dev/null | jq '.error.code'
"file_not_found"
```

---

# 5. Package Structure

## 5.1 Repository Layout

```
rif-runtime/
├── Makefile                     # Build, test, release targets
├── go.mod                       # Go module definition
├── go.sum                       # Dependency hashes
├── main.go                      # CLI entrypoint
├── README.md
├── LICENSE
│
├── cmd/
│   ├── root.go                  # Root command setup
│   ├── run.go                   # `rif run` handler
│   ├── replay.go                # `rif replay` handler
│   ├── verify.go                # `rif verify` handler
│   ├── inspect.go               # `rif inspect` handler
│   ├── policy.go                # `rif policy` handler + subcommands
│   └── evidence.go              # `rif evidence` handler + subcommands
│
├── internal/
│   ├── cli/                     # CLI framework utilities
│   │   ├── flags.go             # Flag parsing and validation
│   │   ├── output.go            # Human-readable + JSON formatting
│   │   ├── errors.go            # Error types and handling
│   │   └── version.go           # Version and build info
│   │
│   ├── policy/                  # Policy evaluation
│   │   ├── parser.go            # YAML/JSON policy parsing
│   │   ├── engine.go            # Policy evaluation logic
│   │   ├── compiler.go          # Policy condition compilation
│   │   └── validator.go         # Policy schema validation
│   │
│   ├── evidence/                # Evidence persistence
│   │   ├── store.go             # Evidence storage interface
│   │   ├── file_store.go        # Filesystem implementation
│   │   ├── serializer.go        # JSON/YAML serialization
│   │   └── hasher.go            # SHA256 hashing
│   │
│   ├── decision/                # Decision data model
│   │   ├── decision.go          # Decision struct
│   │   ├── schema.go            # JSON schema validation
│   │   └── artifact.go          # Artifact metadata
│   │
│   ├── replay/                  # Deterministic replay
│   │   ├── engine.go            # Replay logic
│   │   ├── comparator.go        # Hash/output comparison
│   │   └── validator.go         # Replay validation
│   │
│   └── compliance/              # Compliance verification
│       ├── verifier.go          # Verification logic
│       ├── rule_engine.go       # Compliance rule evaluation
│       └── report.go            # Verification report generation
│
├── pkg/                         # Exported packages (for library use)
│   ├── runtime/
│   │   ├── client.go            # RIF Runtime API client
│   │   └── types.go             # Public types
│   │
│   └── config/
│       ├── loader.go            # Configuration loading
│       └── types.go             # Config structs
│
├── testdata/
│   ├── policies/
│   │   ├── valid_policy.yaml
│   │   ├── invalid_policy.yaml
│   │   └── complex_policy.yaml
│   │
│   ├── evidence/
│   │   ├── sample_decision.json
│   │   └── sample_artifacts.zip
│   │
│   ├── compliance/
│   │   └── sample_rules.yaml
│   │
│   └── fixtures/                # Golden test fixtures
│       ├── run_simple.json
│       ├── verify_passed.json
│       └── replay_deterministic.json
│
├── test/
│   ├── integration_test.go       # Integration tests (spawn binary)
│   ├── e2e_test.go              # End-to-end tests
│   └── fixtures.go              # Test fixture utilities
│
└── docs/
    ├── CLI_SPEC.md              # This file
    ├── ARCHITECTURE.md
    ├── ERROR_CODES.md
    └── examples/
        ├── policy.yaml
        ├── compliance.yaml
        ├── test_cases.yaml
        └── transcripts/          # Example session logs
```

---

## 5.2 `go.mod` Example

```go
module github.com/rif-runtime/rif

go 1.21

require (
    github.com/spf13/cobra v1.7.0
    github.com/spf13/pflag v1.0.5
    github.com/ghodss/yaml v1.0.0        // YAML ↔ JSON conversion
)

require (
    gopkg.in/yaml.v2 v2.4.0               // YAML parsing
)
```

---

## 5.3 Command Handler Skeleton

**`cmd/run.go`**:
```go
package cmd

import (
    "github.com/spf13/cobra"
    "github.com/rif-runtime/rif/internal/cli"
    "github.com/rif-runtime/rif/internal/policy"
)

// runCmd represents the 'rif run' command
var runCmd = &cobra.Command{
    Use:   "run [FLAGS] [OPTIONS] ACTOR ACTION TARGET",
    Short: "Execute a RIF Runtime decision",
    Long: `Execute a policy evaluation, capture evidence, and record the decision.
    
    The decision is evaluated against the policy file and returns:
    - exit code 0 for successful evaluation (allow or deny)
    - exit code 3 for policy violation (deny)
    - exit code 2 for usage errors`,
    
    Args: cobra.ExactArgs(3),  // ACTOR, ACTION, TARGET
    RunE: runRun,
    PreRunE: validateRunFlags,
}

func init() {
    rootCmd.AddCommand(runCmd)
    
    // Options
    runCmd.Flags().StringP("policy", "p", "", "Policy configuration file (required)")
    runCmd.Flags().StringP("capability", "c", "", "Capability manifest file")
    runCmd.Flags().IntP("timeout", "t", 30, "Execution timeout in seconds")
    runCmd.Flags().String("sandbox-level", "standard", "Sandbox isolation level")
    runCmd.Flags().StringToString("env", map[string]string{}, "Environment variables")
    runCmd.Flags().String("output", "", "Output file for decision (default: stdout)")
    runCmd.Flags().String("evidence-dir", "./evidence", "Directory for evidence artifacts")
    
    // Mark required flags
    runCmd.MarkFlagRequired("policy")
}

func runRun(cmd *cobra.Command, args []string) error {
    actor := args[0]
    action := args[1]
    target := args[2]
    
    // ... implementation
    
    return nil
}

func validateRunFlags(cmd *cobra.Command, args []string) error {
    // ... validate flags before execution
    return nil
}
```

---

## 5.4 Output Formatter

**`internal/cli/output.go`**:
```go
package cli

import (
    "encoding/json"
    "fmt"
    "io"
    "os"
)

// OutputFormat specifies human-readable or JSON output
type OutputFormat string

const (
    FormatHuman OutputFormat = "human"
    FormatJSON  OutputFormat = "json"
)

// Formatter handles output generation
type Formatter struct {
    format OutputFormat
    stdout io.Writer
    stderr io.Writer
    isTTY  bool
}

// NewFormatter creates a formatter
func NewFormatter(jsonMode bool) *Formatter {
    isTTY := isTerminal(os.Stdout)
    
    format := FormatHuman
    if jsonMode {
        format = FormatJSON
        isTTY = false  // No colors in JSON mode
    }
    
    return &Formatter{
        format: format,
        stdout: os.Stdout,
        stderr: os.Stderr,
        isTTY:  isTTY,
    }
}

// FormatDecision formats a decision for output
func (f *Formatter) FormatDecision(d *Decision) error {
    if f.format == FormatJSON {
        return f.formatJSON(d)
    }
    return f.formatHuman(d)
}

func (f *Formatter) formatJSON(d *Decision) error {
    // Ensure sorted keys for deterministic output
    encoder := json.NewEncoder(f.stdout)
    encoder.SetEscapeHTML(false)
    encoder.SetIndent("", "  ")
    
    // Wrap in response envelope
    response := map[string]interface{}{
        "schemaVersion": "1.0",
        "decision":      d,
        "error":         nil,
    }
    
    return encoder.Encode(response)
}

func (f *Formatter) formatHuman(d *Decision) error {
    // Format human-readable output
    fmt.Fprintf(f.stdout, "Decision: %s\n", d.Decision)
    fmt.Fprintf(f.stdout, "Reason: %s\n", d.Reason)
    // ... more fields
    
    return nil
}

// FormatError formats an error for output
func (f *Formatter) FormatError(err error) {
    if f.format == FormatJSON {
        f.formatErrorJSON(err)
    } else {
        f.formatErrorHuman(err)
    }
}
```

---

## 5.5 Error Handling

**`internal/cli/errors.go`**:
```go
package cli

import "fmt"

// ExitCode maps errors to exit codes
func ExitCode(err error) int {
    switch err.(type) {
    case *UsageError:
        return 2
    case *PolicyViolation:
        return 3
    case *VerificationFailure:
        return 4
    case *NotFoundError:
        return 5
    case *ConflictError:
        return 6
    case *InternalError:
        return 7
    case *RuntimeError:
        return 1
    default:
        return 1
    }
}

// UsageError indicates incorrect usage
type UsageError struct {
    Message string
    Hint    string
}

func (e *UsageError) Error() string {
    return e.Message
}

// PolicyViolation indicates policy evaluation returned deny
type PolicyViolation struct {
    Message string
}

func (e *PolicyViolation) Error() string {
    return e.Message
}

// ... more error types
```

---

# 6. Code Quality

## 6.1 Idiomatic Go Conventions

- **Package organization**: `cmd/` for CLT handlers, `internal/` for private packages, `pkg/` for public API.
- **Naming**: Interfaces end in `-er` (e.g., `PolicyEvaluator`, `EvidenceStore`).
- **Error handling**: Use `errors.Is()`, `errors.As()` for comparison; wrap with `fmt.Errorf()`.
- **Exports**: Document all exported functions, types, and constants with comments.
- **Concurrency**: Goroutines for parallel operations; channels for communication.

---

## 6.2 Doc Comments

```go
// Run executes a policy evaluation and returns a decision.
//
// The decision is evaluated against the provided policy file and returns:
//   - ExitOK (0) if evaluation succeeds (allow or deny)
//   - ExitPolicyViolation (3) if policy evaluation returns deny
//   - ExitUsageError (2) if arguments are invalid
//
// Run is the handler for the 'rif run' command.
func Run(ctx context.Context, args RunArgs) (*Decision, error) {
    // ...
}

// Decision represents a policy evaluation result.
type Decision struct {
    // DecisionID uniquely identifies this decision.
    DecisionID string
    
    // Decision is the policy evaluation result: "allow" or "deny".
    Decision string
    
    // Reason is a human-readable explanation of the decision.
    Reason string
    
    // Timestamp is when the decision was made (RFC 3339).
    Timestamp string
    
    // Evidence maps artifact names to their metadata.
    Evidence map[string]ArtifactMetadata
}
```

---

## 6.3 Function Size & Testability

- Keep functions under 50 lines; delegate to smaller helpers.
- Inject dependencies (policy engine, evidence store) rather than using globals.
- Use interfaces for abstraction: `PolicyEvaluator`, `EvidenceStore`, `Hasher`.
- Test one concern per test function.

**Example**:
```go
// Evaluator is the policy evaluation engine.
type Evaluator interface {
    Evaluate(ctx context.Context, req EvaluationRequest) (*EvaluationResult, error)
}

// Handler encapsulates run command logic.
type Handler struct {
    evaluator Evaluator
    store     EvidenceStore
    hasher    Hasher
}

// Handle executes the run command.
func (h *Handler) Handle(ctx context.Context, args RunArgs) (*Decision, error) {
    // Validate inputs
    if err := args.Validate(); err != nil {
        return nil, &UsageError{Message: err.Error()}
    }
    
    // Evaluate policy
    req := h.argsToRequest(args)
    result, err := h.evaluator.Evaluate(ctx, req)
    if err != nil {
        return nil, fmt.Errorf("policy evaluation: %w", err)
    }
    
    // Convert result to decision
    decision := h.resultToDecision(result)
    
    // Persist evidence
    if err := h.store.Save(ctx, decision); err != nil {
        return nil, fmt.Errorf("evidence storage: %w", err)
    }
    
    return decision, nil
}
```

---

# 7. Testing Strategy

## 7.1 Unit Tests

**`internal/policy/engine_test.go`**:
```go
package policy

import (
    "context"
    "testing"
)

func TestEvaluate_AllowTrusted(t *testing.T) {
    engine := NewEngine(loadPolicy(t, "testdata/policies/valid_policy.yaml"))
    
    result, err := engine.Evaluate(context.Background(), EvaluationRequest{
        Actor:  "agent:trusted",
        Action: "http.request",
        Target: "https://api.example.com",
    })
    
    if err != nil {
        t.Fatalf("Evaluate failed: %v", err)
    }
    if result.Decision != "allow" {
        t.Errorf("Expected 'allow', got %q", result.Decision)
    }
}

func TestEvaluate_DenyDefault(t *testing.T) {
    engine := NewEngine(loadPolicy(t, "testdata/policies/valid_policy.yaml"))
    
    result, err := engine.Evaluate(context.Background(), EvaluationRequest{
        Actor:  "agent:untrusted",
        Action: "http.request",
        Target: "https://blocked.example.com",
    })
    
    if err != nil {
        t.Fatalf("Evaluate failed: %v", err)
    }
    if result.Decision != "deny" {
        t.Errorf("Expected 'deny', got %q", result.Decision)
    }
}
```

---

## 7.2 Integration Tests

**`test/integration_test.go`**:
```go
package test

import (
    "encoding/json"
    "os/exec"
    "testing"
)

func TestRunCommand_Success(t *testing.T) {
    cmd := exec.Command("./rif", "run",
        "--policy", "testdata/policies/valid_policy.yaml",
        "agent:test", "http.request", "https://api.example.com")
    
    output, err := cmd.Output()
    if err != nil {
        t.Fatalf("Command failed: %v", err)
    }
    
    if cmd.ProcessState.ExitCode() != 0 {
        t.Errorf("Expected exit code 0, got %d", cmd.ProcessState.ExitCode())
    }
    
    var result map[string]interface{}
    if err := json.Unmarshal(output, &result); err != nil {
        t.Fatalf("Failed to parse JSON output: %v", err)
    }
}

func TestRunCommand_PolicyViolation(t *testing.T) {
    cmd := exec.Command("./rif", "run",
        "--policy", "testdata/policies/valid_policy.yaml",
        "agent:untrusted", "http.request", "https://blocked.example.com")
    
    cmd.Output()
    
    if cmd.ProcessState.ExitCode() != 3 {
        t.Errorf("Expected exit code 3 (policy violation), got %d", cmd.ProcessState.ExitCode())
    }
}

func TestRunCommand_UsageError(t *testing.T) {
    cmd := exec.Command("./rif", "run",
        "--policy", "testdata/policies/valid_policy.yaml",
        "agent:test")  // Missing ACTION and TARGET
    
    cmd.Output()
    
    if cmd.ProcessState.ExitCode() != 2 {
        t.Errorf("Expected exit code 2 (usage error), got %d", cmd.ProcessState.ExitCode())
    }
}
```

---

## 7.3 Golden File Tests

**`test/golden_test.go`**:
```go
package test

import (
    "os"
    "path/filepath"
    "testing"
)

func TestGoldenOutput(t *testing.T) {
    tests := []struct {
        name    string
        command []string
        golden  string
    }{
        {
            name:    "run_simple",
            command: []string{"run", "--policy", "testdata/policies/valid_policy.yaml", "--json", "agent:test", "http.request", "https://api.example.com"},
            golden:  "testdata/fixtures/run_simple.json",
        },
        {
            name:    "verify_passed",
            command: []string{"verify", "--evidence-dir", "testdata/evidence", "--json"},
            golden:  "testdata/fixtures/verify_passed.json",
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            cmd := exec.Command("./rif", tt.command...)
            output, _ := cmd.Output()
            
            golden, err := os.ReadFile(tt.golden)
            if err != nil {
                t.Fatalf("Failed to read golden file: %v", err)
            }
            
            if string(output) != string(golden) {
                t.Errorf("Output mismatch.\nExpected:\n%s\nGot:\n%s", golden, output)
            }
        })
    }
}
```

---

## 7.4 Test Matrix (CI)

**`.github/workflows/test.yml`**:
```yaml
name: Test Matrix

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        go: ['1.21', '1.22']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: ${{ matrix.go }}
      
      - name: Build
        run: make build
      
      - name: Unit tests
        run: make test-unit
      
      - name: Integration tests
        run: make test-integration
      
      - name: Golden tests
        run: make test-golden
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.out
```

---

# 8. Edge Cases

## 8.1 Empty/Malformed Input Files

**Empty policy file**:
```bash
$ rif policy validate empty.yaml
Error: policy file is empty

Hint: Provide a policy file with at least one rule.
```

**Trailing newlines** (handled correctly):
```bash
# These all produce identical hashes:
echo '{"rule": "test"}' | rif inspect --json
echo '{"rule": "test"}
' | rif inspect --json
echo '{"rule": "test"}

' | rif inspect --json
```

**BOMs (Byte Order Mark)** — handled by `encoding/json` and YAML parsers automatically.

**CRLF line endings** — normalized to LF before processing:
```go
// internal/cli/normalizer.go
func NormalizeLineEndings(data []byte) []byte {
    return bytes.ReplaceAll(data, []byte("\r\n"), []byte("\n"))
}
```

---

## 8.2 Large Inputs

**Streaming for large evidence directories**:
```go
// internal/evidence/store.go
func (s *FileStore) StreamAll(ctx context.Context, fn func(*Decision) error) error {
    entries, err := os.ReadDir(s.dir)
    if err != nil {
        return err
    }
    
    for _, entry := range entries {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        
        decision, err := s.Load(entry.Name())
        if err != nil {
            return err
        }
        
        if err := fn(decision); err != nil {
            return err
        }
    }
    
    return nil
}
```

**JSON streaming for large decision lists**:
```go
// Emit each decision as a JSON line (JSONL format)
encoder := json.NewEncoder(stdout)
for decision := range decisions {
    encoder.Encode(decision)  // Emits one JSON object per line
}
```

---

## 8.3 Unicode Handling

**Paths with Unicode**:
```bash
$ rif run --policy politique-français.yaml agent:test http.request https://api.example.com
# Handled correctly; UTF-8 paths supported
```

**JSON output with Unicode**:
```bash
$ rif run --json --policy policy.yaml agent:test http.request https://api.example.com | jq '.reason'
"政策违反"  # Chinese characters preserved and escaped properly
```

**Ensure ASCII-safe JSON**:
```go
encoder := json.NewEncoder(stdout)
encoder.SetEscapeHTML(true)  // Escapes non-ASCII as \uXXXX
```

---

## 8.4 TTY vs. Non-TTY Detection

```go
// internal/cli/output.go
func isTerminal(w io.Writer) bool {
    f, ok := w.(*os.File)
    if !ok {
        return false
    }
    
    _, err := unix.IoctlGetTermios(int(f.Fd()), unix.TCGETS)
    return err == nil
}

// Use for color output
if formatter.isTTY {
    fmt.Fprintf(stdout, "\033[32m✓\033[0m Decision: ALLOW\n")  // Green
} else {
    fmt.Fprintf(stdout, "✓ Decision: ALLOW\n")  // No color
}
```

---

## 8.5 Deterministic JSON Key Ordering

**All JSON output must have sorted keys** for stable diffs and reproducibility:

```go
// Incorrect: map iteration order is random
json.Marshal(map[string]interface{}{
    "zebra": 1,
    "apple": 2,
})  // May output {"zebra":1,"apple":2} or {"apple":2,"zebra":1}

// Correct: use ordered structure or custom marshaler
type OrderedDecision struct {
    DecisionID string                 // Alphabetically first
    Decision   string
    Reason     string
    Timestamp  string
    // ... rest in alphabetical order
}

json.Marshal(OrderedDecision{...})  // Always produces same key order
```

---

## 8.6 Versioned JSON Schema

**Every JSON response includes `schemaVersion`**:

```json
{
  "schemaVersion": "1.0",
  "decision": "allow",
  ...
}
```

**Clients can handle version mismatches**:
```go
func (c *Client) parseResponse(data []byte) (*Decision, error) {
    var envelope struct {
        SchemaVersion string `json:"schemaVersion"`
        Decision      *Decision `json:"decision"`
    }
    
    if err := json.Unmarshal(data, &envelope); err != nil {
        return nil, err
    }
    
    if envelope.SchemaVersion != "1.0" {
        return nil, fmt.Errorf("unsupported schema version: %s", envelope.SchemaVersion)
    }
    
    return envelope.Decision, nil
}
```

---

## 8.7 Interrupted Execution (SIGINT)

**Handle gracefully**:
```go
// main.go
func main() {
    ctx, cancel := context.WithCancel(context.Background())
    
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
    
    go func() {
        <-sigChan
        cancel()
    }()
    
    if err := rootCmd.ExecuteContext(ctx); err != nil {
        if errors.Is(err, context.Canceled) {
            // Interrupted; exit cleanly
            os.Exit(130)  // Standard SIGINT exit code
        }
        os.Exit(1)
    }
}
```

---

# 9. Assumptions

1. **Language**: Go 1.21+ (chosen for single binary, fast startup, minimal dependencies).

2. **Input file formats**:
   - Policy and compliance files: YAML or JSON (auto-detected by extension).
   - Evidence: ZIP or TAR archives containing JSON artifacts.
   - Test cases: YAML or JSON with `tests` array.

3. **Output defaults**:
   - Stdout: machine-readable if `--json`, else human-readable.
   - Stderr: error messages, warnings, debug logs (`--verbose`).
   - No output buffering; streams directly for large files.

4. **Evidence persistence**:
   - Default directory: `./evidence/` (relative to CWD).
   - Structure: `evidence/<DECISION_ID>/` with JSON artifacts.
   - Hashing: SHA256, lowercase hex, written to `hashes.json`.

5. **Policy evaluation**:
   - Policies use priority-based rule matching (highest priority wins).
   - Conditions are evaluated as expressions (no full scripting language).
   - Default policy (if no rule matches): DENY.

6. **Compliance verification**:
   - Compliance rules are boolean checks (pass/fail, not continuous scores).
   - Verification collects all failures before reporting (not fail-fast by default).

7. **Error messages**:
   - Errors go to stderr; results go to stdout.
   - JSON errors always have `error` field (may be null on success).
   - Human-readable errors include hints for fixing.

8. **CI/pipeline usage**:
   - Exit codes are standardized across all commands.
   - `--json` output is deterministic and parseable with `jq`.
   - Binary is statically linked; no runtime dependencies.

---

# 10. Verification Checklist

**Before shipping v1.0, verify**:

- [ ] All six commands implemented (`run`, `replay`, `verify`, `inspect`, `policy`, `evidence`).
- [ ] Exit codes match spec (0, 1, 2, 3, 4, 5, 6, 7).
- [ ] `--json` flag produces valid, schema-versioned JSON.
- [ ] `--help` and `--version` work on all commands.
- [ ] Errors go to stderr; results go to stdout.
- [ ] Colors only appear when TTY detected.
- [ ] JSON key ordering is alphabetical (deterministic).
- [ ] Large inputs handled via streaming, not buffering.
- [ ] Unicode paths and output work correctly.
- [ ] Line ending normalization (CRLF → LF).
- [ ] SIGINT/SIGTERM exit gracefully (exit code 130).
- [ ] Policy validation catches schema errors with line/column info.
- [ ] Evidence integrity checks (SHA256 hash verification).
- [ ] Cross-platform tests pass (Linux, macOS, Windows).
- [ ] Single-binary distribution works (no external dependencies).
- [ ] Unit tests cover all error paths.
- [ ] Integration tests invoke the binary and check exit codes.
- [ ] Golden file tests verify exact output format.
- [ ] CI/GitHub Actions workflow runs tests and gates PRs.
- [ ] Replay produces deterministic hashes (same policy + inputs = same output).
- [ ] JSON parsing is strict (fails on unknown fields).

---

**End of Technical Specification**
