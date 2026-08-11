# RIF Runtime v1.0 CLI — Implementation Contract

**Version**: 1.0.0  
**Status**: Implementation-Ready  
**Go Version**: 1.21+  

---

## Goal

Implement the smallest production-quality runtime that satisfies the v1.0 specification while preserving deterministic replay and auditability.

---

## Approved Decisions

| Area | Decision |
|------|----------|
| Policy engine | Simple string/list matching (no expression language) |
| Rule precedence | Highest numeric priority wins |
| Evidence storage | Local filesystem only |
| Replay hashing | SHA256 of canonicalized `decision.json` |
| Compliance checks | All enabled checks must pass; support 3 types: `side_effect_forbidden`, `policy_rule_required`, `latency_check` |
| Config format | Optional YAML (`rif.yaml`); fields: `policy_path`, `evidence_path`, `compliance_path` |
| Large datasets | In-memory loading v1.0; streaming deferred to v1.1 |
| Evidence artifacts | Minimal set: `decision.json`, `policy_evaluation.json`, `artifacts_manifest.json` |
| Validation scope | Schema, required fields, duplicate IDs, priorities only; static analysis deferred |
| Test fixtures | Realistic fixtures in `testdata/`; temp directories for integration tests |

---

## Runtime Guarantees

- **Deterministic policy evaluation** — Same policy + inputs = identical decision
- **Deterministic decision serialization** — Canonical JSON format always produces identical bytes
- **Deterministic replay hashing** — Same decision replayed twice produces identical SHA256
- **Append-only evidence storage** — Decisions never modified; audit trail immutable
- **Auditability of every governance decision** — Complete trace from policy rule to decision recorded

---

## Canonical JSON Specification

All JSON output and evidence persistence must use:

- **Encoding**: UTF-8
- **Object key ordering**: Sorted lexicographically (not insertion order)
- **Whitespace**: No insignificant whitespace (compact format)
- **Field ordering**: Stable across all persisted structs
- **Timestamps**: RFC3339 format, UTC timezone (e.g., `2025-01-15T10:30:00Z`)
- **Encoder settings**: 
  - `json.Marshal()` with custom type that implements `json.Marshaler` or
  - Post-processing to ensure sorted keys

**Example**:
```json
{
  "actor": "agent:test",
  "decision": "allow",
  "decisionId": "01938c4e-8a8c-7c47-b000-000000000000",
  "reason": "policy rule matched",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Evidence Identity

- **Decision ID format**: UUIDv7 (sortable, time-ordered)
- **Evidence directory**: `<evidence_path>/<decision_id>/`
- **Directory structure**:
  ```
  evidence/
  └── 01938c4e-8a8c-7c47-b000-000000000000/
      ├── decision.json
      ├── policy_evaluation.json
      ├── artifacts_manifest.json
      └── hashes.json
  ```

---

## Exit Code Contract

All commands must adhere to:

- **Exit code 0**: Success (decision evaluated, verification passed, etc.)
- **Non-zero on error**: Exit code must not be 0 if stderr contains a fatal error message
- **Standard mappings**: Use exit codes from specification (1, 2, 3, 4, 5, 6, 7)

---

## I/O Contract

- **stdout**: Successful results (human-readable or `--json`)
- **stderr**: Error messages, warnings, debug logs (`--verbose`)
- **Rule**: Commands must never return exit code 0 when stderr contains a fatal error message
- **JSON mode**: `--json` produces strict JSON with `schemaVersion: "1.0"` envelope

---

## Architecture

### Framework
**Cobra** — subcommands, help system, shell completion, command tree.

### Package Structure
```
rif-runtime/
├── main.go                      # CLI entrypoint
├── go.mod / go.sum
│
├── cmd/
│   ├── root.go                  # Root command setup
│   ├── run.go                   # `rif run` handler
│   ├── replay.go                # `rif replay` handler
│   ├── verify.go                # `rif verify` handler
│   ├── inspect.go               # `rif inspect` handler
│   ├── policy.go                # `rif policy` handler
│   └── evidence.go              # `rif evidence` handler
│
├── internal/
│   ├── cli/
│   │   ├── output.go            # Human + JSON formatting
│   │   ├── errors.go            # Error types and exit codes
│   │   └── flags.go             # Common flag parsing
│   │
│   ├── policy/
│   │   ├── parser.go            # YAML/JSON policy parsing
│   │   ├── engine.go            # String/list matching evaluation
│   │   └── validator.go         # Schema validation
│   │
│   ├── evidence/
│   │   ├── store.go             # Filesystem storage interface
│   │   ├── file_store.go        # Filesystem implementation
│   │   ├── hasher.go            # SHA256 canonical hashing
│   │   └── serializer.go        # Canonical JSON serialization
│   │
│   ├── decision/
│   │   ├── model.go             # Decision struct
│   │   └── uuidv7.go            # UUIDv7 ID generation
│   │
│   ├── replay/
│   │   ├── engine.go            # Replay logic
│   │   └── comparator.go        # Hash comparison
│   │
│   └── compliance/
│       ├── verifier.go          # Compliance verification
│       └── rule_engine.go       # Check evaluation
│
├── testdata/
│   ├── policies/
│   │   ├── valid_policy.yaml
│   │   └── complex_policy.yaml
│   │
│   ├── evidence/
│   │   └── sample_decision.json
│   │
│   └── compliance/
│       └── sample_rules.yaml
│
└── test/
    ├── cli_test.go              # Integration tests
    ├── golden_test.go           # Golden file tests
    └── fixtures.go              # Test utilities
```

---

## Verification Gate

Before presenting the final implementation, verify all of:

1. `gofmt -w ./...` — All code formatted
2. `go vet ./...` — No static analysis warnings
3. `go build ./...` — Compiles without errors
4. `go test ./...` — All tests pass
5. **Replay determinism test**: Execute the same decision twice and confirm identical SHA256 hashes

---

## Execution Contract

**Proceed with implementation only after confirming that all approved decisions are represented in the code.**

If any new ambiguity is discovered during implementation, **stop and request a decision** rather than inventing behavior.

Do not proceed to implementation until explicitly confirmed.

---

## Deferred to v1.1+

- Expression language (CEL, Lua)
- Pluggable storage backends
- Streaming for large datasets
- Static policy analysis (unreachable rules, dead conditions)
- Additional evidence artifacts
- Database backends (SQLite, PostgreSQL)
- Compliance check plugins

---

## Success Criteria

A v1.0 implementation is complete when:

- ✅ All 6 commands fully functional
- ✅ Exit codes match specification
- ✅ JSON output schema-versioned with canonical format
- ✅ Deterministic replay passes twice with identical hashes
- ✅ Evidence stored with UUIDv7 IDs in `<evidence_path>/<decision_id>/`
- ✅ All error paths tested and verified
- ✅ Cross-platform tests pass (Linux, macOS, Windows)
- ✅ `gofmt`, `go vet`, `go build`, `go test` all pass
- ✅ README with realistic usage examples

---

**Ready for implementation confirmation.**
