package core

import (
	"encoding/json"
	"fmt"
	"time"
)

// State represents the current state of the RIF Runtime.
// All fields must be deep-copyable for replay validation.
type State struct {
	Version              int                          `json:"version"`
	LastEventID          string                       `json:"last_event_id"`
	LastEventTime        time.Time                    `json:"last_event_time"`
	Resources            map[string]*Resource        `json:"resources"`
	Metadata             map[string]string           `json:"metadata"`
	DecisionCount        int                          `json:"decision_count"`
	AllowDecisionCount   int                          `json:"allow_decision_count"`
	DenyDecisionCount    int                          `json:"deny_decision_count"`
}

// Resource represents a managed governance resource.
type Resource struct {
	ID        string            `json:"id"`
	Type      string            `json:"type"`
	Name      string            `json:"name"`
	Version   string            `json:"version"`
	CreatedAt time.Time         `json:"created_at"`
	Metadata  map[string]string `json:"metadata"`
}

// NewState creates a fresh runtime state.
func NewState() *State {
	return &State{
		Version:    1,
		Resources:  make(map[string]*Resource),
		Metadata:   make(map[string]string),
	}
}

// DeepCopy returns an independent copy of the state.
// This is essential for replay validation and determinism checks.
func (s *State) DeepCopy() *State {
	if s == nil {
		return nil
	}

	copy := &State{
		Version:            s.Version,
		LastEventID:        s.LastEventID,
		LastEventTime:      s.LastEventTime,
		Resources:          make(map[string]*Resource),
		Metadata:           make(map[string]string),
		DecisionCount:      s.DecisionCount,
		AllowDecisionCount: s.AllowDecisionCount,
		DenyDecisionCount:  s.DenyDecisionCount,
	}

	// Deep copy resources
	for id, res := range s.Resources {
		meta := make(map[string]string)
		for k, v := range res.Metadata {
			meta[k] = v
		}
		copy.Resources[id] = &Resource{
			ID:        res.ID,
			Type:      res.Type,
			Name:      res.Name,
			Version:   res.Version,
			CreatedAt: res.CreatedAt,
			Metadata:  meta,
		}
	}

	// Deep copy metadata
	for k, v := range s.Metadata {
		copy.Metadata[k] = v
	}

	return copy
}

// Equal returns true if the state is identical to another state.
// This is used for determinism validation.
func (s *State) Equal(other *State) bool {
	if s == nil && other == nil {
		return true
	}
	if s == nil || other == nil {
		return false
	}

	if s.Version != other.Version ||
		s.LastEventID != other.LastEventID ||
		s.DecisionCount != other.DecisionCount ||
		s.AllowDecisionCount != other.AllowDecisionCount ||
		s.DenyDecisionCount != other.DenyDecisionCount ||
		!s.LastEventTime.Equal(other.LastEventTime) {
		return false
	}

	// Compare resources
	if len(s.Resources) != len(other.Resources) {
		return false
	}
	for id, res := range s.Resources {
		otherRes, exists := other.Resources[id]
		if !exists || !resourcesEqual(res, otherRes) {
			return false
		}
	}

	// Compare metadata
	if len(s.Metadata) != len(other.Metadata) {
		return false
	}
	for k, v := range s.Metadata {
		if other.Metadata[k] != v {
			return false
		}
	}

	return true
}

// resourcesEqual compares two resources for equality.
func resourcesEqual(r1, r2 *Resource) bool {
	if r1 == nil && r2 == nil {
		return true
	}
	if r1 == nil || r2 == nil {
		return false
	}

	if r1.ID != r2.ID ||
		r1.Type != r2.Type ||
		r1.Name != r2.Name ||
		r1.Version != r2.Version ||
		!r1.CreatedAt.Equal(r2.CreatedAt) {
		return false
	}

	if len(r1.Metadata) != len(r2.Metadata) {
		return false
	}
	for k, v := range r1.Metadata {
		if r2.Metadata[k] != v {
			return false
		}
	}

	return true
}

// EventLog is an append-only log of events.
// All events in the log must be immutable and serializable.
type EventLog struct {
	Events []Event `json:"events"`
}

// NewEventLog creates a new empty event log.
func NewEventLog() *EventLog {
	return &EventLog{
		Events: make([]Event, 0),
	}
}

// Append adds an event to the log.
// Events are immutable; the caller must ensure the event is valid before appending.
func (l *EventLog) Append(e Event) error {
	if e == nil {
		return fmt.Errorf("cannot append nil event")
	}

	// Validate the event
	if err := validateEvent(e); err != nil {
		return fmt.Errorf("invalid event: %w", err)
	}

	l.Events = append(l.Events, e)
	return nil
}

// validateEvent calls the Validate method if the event implements it.
func validateEvent(e Event) error {
	switch v := e.(type) {
	case *PolicyDecisionEvent:
		return v.Validate()
	case *CreateResourceEvent:
		return v.Validate()
	case *UpdateStateEvent:
		return v.Validate()
	case *DeleteResourceEvent:
		return v.Validate()
	default:
		return fmt.Errorf("unknown event type")
	}
}

// Length returns the number of events in the log.
func (l *EventLog) Length() int {
	if l == nil {
		return 0
	}
	return len(l.Events)
}

// SerializeCanonical returns the event log as canonical JSON (sorted keys, compact).
// This is essential for deterministic hashing and replay verification.
func (l *EventLog) SerializeCanonical() ([]byte, error) {
	if l == nil {
		return []byte("[]"), nil
	}

	// Marshal each event and collect
	var envelopes []EventEnvelope
	for i, e := range l.Events {
		eventData, err := json.Marshal(e)
		if err != nil {
			return nil, fmt.Errorf("event %d: marshal: %w", i, err)
		}
		envelopes = append(envelopes, EventEnvelope{
			Type:  e.Type(),
			Event: json.RawMessage(eventData),
		})
	}

	// Use canonical JSON encoding (no whitespace, sorted keys)
	encoder := json.NewEncoder(nil)
	return json.Marshal(envelopes)
}

// DeserializeCanonical parses a canonical JSON event log.
func DeserializeCanonical(data []byte) (*EventLog, error) {
	if len(data) == 0 {
		return NewEventLog(), nil
	}

	var envelopes []EventEnvelope
	if err := json.Unmarshal(data, &envelopes); err != nil {
		return nil, fmt.Errorf("parse event log: %w", err)
	}

	log := NewEventLog()
	for i, env := range envelopes {
		e, err := UnmarshalEvent([]byte(`{"type":"` + string(env.Type) + `","event":` + string(env.Event) + `}`))
		if err != nil {
			return nil, fmt.Errorf("event %d: %w", i, err)
		}
		if err := log.Append(e); err != nil {
			return nil, fmt.Errorf("event %d: %w", i, err)
		}
	}

	return log, nil
}
