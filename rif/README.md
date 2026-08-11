# RIF Runtime v1.0 — Core Engine

A minimal, deterministic event replay kernel for evidence-based governance. The runtime records a sequence of immutable events and can replay that sequence deterministically to reproduce the exact same final state.

## Design Philosophy

**Replay guarantees over features**. Every design decision prioritizes:
- **Determinism** — given the same initial state and event log, always produce identical final state
- **Side-effect free replay** — no I/O, no time functions, no randomness during replay
- **Auditability** — immutable, append-only evidence log
- **Minimal abstractions** — concrete types, no interfaces where not needed

## Core Types

### Event System

Four concrete event types, each immutable and JSON-serializable:

- **`PolicyDecisionEvent`** — Records a governance decision (allow/deny)
  - Fields: `actor`, `action`, `target`, `decision`, `priority`, `reason`, `timestamp`
  - Example: "Agent trusted-bot executes resource-prod → ALLOW (priority 100)"

- **`CreateResourceEvent`** — Records creation of a governance resource
  - Fields: `resource_id`, `resource_type`, `name`, `version`, `metadata`
  - Example: "Policy v1 created (type=policy, version=1.0.0)"

- **`UpdateStateEvent`** — Records mutations to runtime state
  - Fields: `key`, `old_value`, `new_value`, `reason`
  - Example: "governance_version updated from 0 → 1"

- **`DeleteResourceEvent`** — Records deletion of a resource
  - Fields: `resource_id`, `reason`
  - Example: "Policy v1 deleted (cleanup)"

### State

A concrete struct representing the current runtime state:

```go
type State struct {
	Version              int                          // Incremented on each event
	LastEventID          string                       // ID of most recent event
	LastEventTime        time.Time                    // Timestamp of most recent event
	Resources            map[string]*Resource        // All managed resources
	Metadata             map[string]string           // Key-value governance data
	DecisionCount        int                          // Total decisions made
	AllowDecisionCount   int                          // Decisions that allowed
	DenyDecisionCount    int                          // Decisions that denied
}
```

- **Deep-copyable** — critical for replay validation
- **Comparable** — `Equal()` method for determinism checks
- **Immutable during replay** — input state never modified

### Event Log

Append-only log with canonical JSON serialization:

```go
type EventLog struct {
	Events []Event
}
```

- `Append(e Event)` — adds event, validates it first
- `SerializeCanonical()` — returns deterministic JSON (sorted keys, compact format)
- `DeserializeCanonical(data)` — parses canonical JSON back to events

### Replay Engine

Core determinism guarantee:

```go
engine := NewReplayEngine()
finalState, err := engine.Replay(initialState, eventLog)
```

**Guarantees:**
- Same `initialState` + same `eventLog` → always same `finalState`
- No side effects during replay
- Returns detailed error if event cannot be applied (e.g., duplicate resource creation)

**Validation:**
- Each event is validated before application
- State invariants enforced (e.g., cannot update non-existent keys, cannot delete non-existent resources)
- Strict error reporting with event index and ID

**Determinism check:**

```go
// Verify determinism: replay twice, compare states
err := engine.DeterminismCheck(initialState, eventLog)
```

**Hashing:**

```go
// Compute SHA256 of canonical event log
hash, err := engine.Hash(eventLog)
```

- Same log always produces same hash
- Hash can be used for integrity verification and compliance

## Replay Guarantees

### What is Deterministic

1. **Event ordering** — events applied exactly as they appear in the log, in order
2. **State mutations** — applying event N in state S always produces the same state S'
3. **Final state** — replaying the entire log twice produces identical final states
4. **Hashing** — SHA256 of canonical event log is deterministic

### What is NOT Guaranteed

- **Real-time constraints** — events are applied in logical order, not wall-clock timing
- **Concurrent events** — no concurrency control; events are applied sequentially
- **External state** — replay only affects the RIF Runtime state, not external systems

## Usage Examples

### Recording Events

```go
log := NewEventLog()

// Record a policy decision
log.Append(&PolicyDecisionEvent{
    EventID:   "evt-001",
    EventTime: time.Now().UTC(),
    Actor:     "agent:prod-deploy",
    Action:    "execute",
    Target:    "database:primary",
    Decision:  "allow",
    Reason:    "trusted actor",
    Priority:  100,
})

// Create a resource
log.Append(&CreateResourceEvent{
    EventID:      "evt-002",
    EventTime:    time.Now().UTC(),
    ResourceID:   "policy:v1",
    ResourceType: "policy",
    Name:         "Production Policy",
    Version:      "1.0.0",
    Metadata:     map[string]string{"owner": "alice"},
})
```

### Replaying Events

```go
engine := NewReplayEngine()
initial := NewState()

// Replay the log to get final state
state, err := engine.Replay(initial, log)
if err != nil {
    log.Fatal(err) // Invalid event encountered
}

// State now contains:
// - 1 decision (allowed)
// - 1 resource created
// - Updated counters and version
```

### Verifying Determinism

```go
// Critical self-test: verify the same log replays identically
err := engine.DeterminismCheck(initial, log)
if err != nil {
    log.Fatal("replay is not deterministic:", err)
}
```

### Computing Hashes

```go
// Compute SHA256 hash of the event log
hash, err := engine.Hash(log)
if err != nil {
    log.Fatal(err)
}

fmt.Printf("Event log hash: %s\n", hash)

// Later, verify hash matches expected value
currentHash, err := engine.HashAndVerify(initial, log, expectedHash)
if err != nil {
    log.Fatal("hash mismatch:", err)
}
```

### Serialization

```go
// Serialize event log to canonical JSON
data, err := log.SerializeCanonical()
if err != nil {
    log.Fatal(err)
}

// Save to file
err = ioutil.WriteFile("evidence.json", data, 0600)

// Later, load and deserialize
loadedLog, err := DeserializeCanonical(data)
if err != nil {
    log.Fatal(err)
}
```

## Testing

Comprehensive test coverage (21 test cases):

- ✅ Single event replay (policy decision, create, update, delete)
- ✅ Multiple event sequences
- ✅ Determinism (replay twice, verify identical states)
- ✅ Error handling (nil inputs, duplicate creation, non-existent deletion, invalid state mutations)
- ✅ Hashing (deterministic, correct format)
- ✅ Serialization (round-trip, canonical format)
- ✅ Deep copy (independence of copies)
- ✅ Empty log edge case

**Run tests:**

```bash
go test ./...
```

**Expected output:**

```
ok  	github.com/rif-runtime/rif/core	0.456s
```

All tests must pass without errors.

## Verification Checklist

Before deployment:

```bash
# Format code
go fmt ./...

# Static analysis
go vet ./...

# Build (no-op for library)
go build ./...

# Run all tests
go test ./...

# Run determinism test explicitly
go test -run TestDeterminism ./...

# Run hash test explicitly
go test -run TestHash ./...
```

## File Structure

```
rif/
├── go.mod              # Go module definition
│
└── core/
    ├── events.go       # Event types (PolicyDecision, CreateResource, UpdateState, DeleteResource)
    ├── state.go        # State type, Resource, EventLog
    ├── replay.go       # ReplayEngine with Replay(), DeterminismCheck(), Hash()
    └── core_test.go    # 21 comprehensive tests
```

## Assumptions & TODOs

### Assumptions Made (Due to v1.0 Contract Freeze)

1. **Event ID Format** — String UUIDs (v7 recommended but not enforced by core)
2. **Timestamps** — RFC3339 UTC format required
3. **Metadata** — Simple string key-value pairs; no nested structures
4. **Serialization** — JSON only; binary formats deferred to v1.1
5. **Concurrency** — Single-threaded replay; concurrent applications responsibility of caller
6. **Determinism Scope** — Deterministic within RIF Runtime state; external systems not affected

### Future Enhancements (Deferred to v1.1+)

- [ ] Streaming replay for very large logs
- [ ] Snapshot/checkpoint optimization
- [ ] Event compression and deduplication
- [ ] Multi-threaded replay validation
- [ ] Binary serialization (protobuf, CBOR)
- [ ] Event filtering and projection
- [ ] Compliance rule engine integration

## Guarantees & Constraints

### Hard Guarantees

- **Determinism** — Same input → always same output
- **Immutability** — Events never modified after appending
- **Auditability** — Complete trace from each final state back to original events
- **No side effects** — Replay never performs I/O or external effects

### By Design

- **Append-only** — Events can never be removed or reordered
- **Strict validation** — Invalid events rejected with clear errors
- **Deep comparison** — State equality uses deep copy + field-by-field comparison
- **Canonical hashing** — Sorted keys, compact JSON, deterministic SHA256

## Next Steps

1. **Integrate with CLI** — Connect replay engine to `rif run`, `rif replay` commands
2. **Add compliance verification** — Use hashes to verify policy compliance
3. **Build evidence storage** — Implement `rif evidence` commands with determinism checks
4. **Create policy engine** — Add policy matching and decision logic
5. **Deploy to production** — Enable auditability of all governance decisions

---

**Status**: ✅ Complete, tested, ready for CLI integration  
**Version**: 1.0.0  
**License**: TBD
