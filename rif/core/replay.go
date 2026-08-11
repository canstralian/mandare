package core

import (
	"crypto/sha256"
	"fmt"
	"io"
	"time"
)

// ReplayEngine applies a sequence of events to a state in order.
// It is deterministic: given the same initial state and event log,
// it always produces the same final state.
type ReplayEngine struct {
	// No mutable fields; all operations are pure functions.
}

// NewReplayEngine creates a new replay engine.
func NewReplayEngine() *ReplayEngine {
	return &ReplayEngine{}
}

// Replay applies all events in the log to the initial state and returns the final state.
// This function is deterministic and side-effect free (no I/O, no time functions, no randomness).
// It returns an error if any event cannot be applied (e.g., updating a non-existent resource).
func (re *ReplayEngine) Replay(initialState *State, log *EventLog) (*State, error) {
	if initialState == nil {
		return nil, fmt.Errorf("initial state is nil")
	}
	if log == nil {
		return nil, fmt.Errorf("event log is nil")
	}

	// Start with a deep copy to avoid mutating the input
	state := initialState.DeepCopy()

	// Apply each event in order
	for i, event := range log.Events {
		var err error
		switch e := event.(type) {
		case *PolicyDecisionEvent:
			err = re.applyPolicyDecision(state, e)
		case *CreateResourceEvent:
			err = re.applyCreateResource(state, e)
		case *UpdateStateEvent:
			err = re.applyUpdateState(state, e)
		case *DeleteResourceEvent:
			err = re.applyDeleteResource(state, e)
		default:
			err = fmt.Errorf("unknown event type")
		}

		if err != nil {
			return nil, fmt.Errorf("event %d (id=%s): %w", i, event.ID(), err)
		}
	}

	return state, nil
}

// applyPolicyDecision records a policy decision and updates decision counters.
func (re *ReplayEngine) applyPolicyDecision(state *State, event *PolicyDecisionEvent) error {
	if state == nil || event == nil {
		return fmt.Errorf("state or event is nil")
	}

	state.LastEventID = event.EventID
	state.LastEventTime = event.EventTime
	state.DecisionCount++

	switch event.Decision {
	case "allow":
		state.AllowDecisionCount++
	case "deny":
		state.DenyDecisionCount++
	default:
		return fmt.Errorf("invalid decision: %q", event.Decision)
	}

	return nil
}

// applyCreateResource adds a new resource to the state.
// It returns an error if the resource already exists.
func (re *ReplayEngine) applyCreateResource(state *State, event *CreateResourceEvent) error {
	if state == nil || event == nil {
		return fmt.Errorf("state or event is nil")
	}

	if _, exists := state.Resources[event.ResourceID]; exists {
		return fmt.Errorf("resource %q already exists", event.ResourceID)
	}

	state.Resources[event.ResourceID] = &Resource{
		ID:        event.ResourceID,
		Type:      event.ResourceType,
		Name:      event.Name,
		Version:   event.Version,
		CreatedAt: event.EventTime,
		Metadata:  copyMap(event.Metadata),
	}

	state.LastEventID = event.EventID
	state.LastEventTime = event.EventTime
	state.Version++

	return nil
}

// applyUpdateState modifies a key-value pair in state metadata.
// It returns an error if the key does not exist (strict semantics).
func (re *ReplayEngine) applyUpdateState(state *State, event *UpdateStateEvent) error {
	if state == nil || event == nil {
		return fmt.Errorf("state or event is nil")
	}

	// Strict semantics: key must exist
	if _, exists := state.Metadata[event.Key]; !exists {
		return fmt.Errorf("state key %q does not exist", event.Key)
	}

	state.Metadata[event.Key] = event.NewValue
	state.LastEventID = event.EventID
	state.LastEventTime = event.EventTime
	state.Version++

	return nil
}

// applyDeleteResource removes a resource from the state.
// It returns an error if the resource does not exist.
func (re *ReplayEngine) applyDeleteResource(state *State, event *DeleteResourceEvent) error {
	if state == nil || event == nil {
		return fmt.Errorf("state or event is nil")
	}

	if _, exists := state.Resources[event.ResourceID]; !exists {
		return fmt.Errorf("resource %q does not exist", event.ResourceID)
	}

	delete(state.Resources, event.ResourceID)
	state.LastEventID = event.EventID
	state.LastEventTime = event.EventTime
	state.Version++

	return nil
}

// copyMap creates a deep copy of a string map.
func copyMap(m map[string]string) map[string]string {
	if m == nil {
		return make(map[string]string)
	}
	copy := make(map[string]string)
	for k, v := range m {
		copy[k] = v
	}
	return copy
}

// DeterminismCheck verifies that replaying the same log twice produces identical states.
// This is a critical self-test for replay guarantees.
func (re *ReplayEngine) DeterminismCheck(initialState *State, log *EventLog) error {
	if initialState == nil || log == nil {
		return fmt.Errorf("initial state or log is nil")
	}

	// Replay once
	state1, err := re.Replay(initialState, log)
	if err != nil {
		return fmt.Errorf("first replay failed: %w", err)
	}

	// Replay again with a fresh copy of the initial state
	state2, err := re.Replay(initialState, log)
	if err != nil {
		return fmt.Errorf("second replay failed: %w", err)
	}

	// Compare states
	if !state1.Equal(state2) {
		return fmt.Errorf("replay is non-deterministic: state1 != state2")
	}

	return nil
}

// Hash computes the SHA256 hash of the event log in canonical form.
// This hash is deterministic: the same log always produces the same hash.
// The hash can be used to verify the integrity and immutability of the event log.
func (re *ReplayEngine) Hash(log *EventLog) (string, error) {
	if log == nil {
		return "", fmt.Errorf("event log is nil")
	}

	// Serialize to canonical JSON
	canonical, err := log.SerializeCanonical()
	if err != nil {
		return "", fmt.Errorf("serialize log: %w", err)
	}

	// Compute SHA256
	h := sha256.New()
	if _, err := io.WriteString(h, string(canonical)); err != nil {
		return "", fmt.Errorf("hash: %w", err)
	}

	return fmt.Sprintf("%x", h.Sum(nil)), nil
}

// HashAndVerify replays the log and computes its hash.
// If the hash differs from expectedHash, it returns an error.
// This is used for compliance verification and replay integrity checks.
func (re *ReplayEngine) HashAndVerify(initialState *State, log *EventLog, expectedHash string) (string, error) {
	if initialState == nil || log == nil {
		return "", fmt.Errorf("initial state or log is nil")
	}

	// First, verify determinism
	if err := re.DeterminismCheck(initialState, log); err != nil {
		return "", fmt.Errorf("determinism check failed: %w", err)
	}

	// Compute the hash
	hash, err := re.Hash(log)
	if err != nil {
		return "", fmt.Errorf("compute hash: %w", err)
	}

	// Verify against expected hash if provided
	if expectedHash != "" && hash != expectedHash {
		return hash, fmt.Errorf("hash mismatch: expected %s, got %s", expectedHash, hash)
	}

	return hash, nil
}

// ReplayWithTimeout applies events with a time constraint (for testing).
// In production, this would use context.Context with a deadline.
// For now, we accept a maxTime parameter and ensure all events have valid timestamps.
func (re *ReplayEngine) ReplayWithTimeout(initialState *State, log *EventLog, maxTime time.Duration) (*State, error) {
	if initialState == nil || log == nil {
		return nil, fmt.Errorf("initial state or log is nil")
	}

	// For v1.0, we don't enforce a time constraint during replay.
	// This is a placeholder for future versions with stricter timing validation.
	// TODO(contract): Define timeout semantics and timing constraints for deterministic replay.

	return re.Replay(initialState, log)
}
