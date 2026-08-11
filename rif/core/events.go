// Package core defines the event types and replay engine for RIF Runtime.
package core

import (
	"encoding/json"
	"fmt"
	"time"
)

// EventType distinguishes the type of event.
type EventType string

const (
	EventTypePolicyDecision EventType = "policy_decision"
	EventTypeCreateResource EventType = "create_resource"
	EventTypeUpdateState    EventType = "update_state"
	EventTypeDeleteResource EventType = "delete_resource"
)

// Event is the base interface for all events.
// All events are immutable and must be serializable to JSON.
type Event interface {
	Type() EventType
	Timestamp() time.Time
	ID() string
}

// PolicyDecisionEvent records a policy evaluation result.
type PolicyDecisionEvent struct {
	EventID   string    `json:"event_id"`
	EventTime time.Time `json:"timestamp"`
	Actor     string    `json:"actor"`
	Action    string    `json:"action"`
	Target    string    `json:"target"`
	Decision  string    `json:"decision"` // "allow" or "deny"
	Reason    string    `json:"reason"`
	Priority  int       `json:"priority"`
}

func (e *PolicyDecisionEvent) Type() EventType   { return EventTypePolicyDecision }
func (e *PolicyDecisionEvent) Timestamp() time.Time { return e.EventTime }
func (e *PolicyDecisionEvent) ID() string        { return e.EventID }

// Validate checks that the event is well-formed.
func (e *PolicyDecisionEvent) Validate() error {
	if e.EventID == "" {
		return fmt.Errorf("PolicyDecisionEvent: event_id is required")
	}
	if e.Actor == "" {
		return fmt.Errorf("PolicyDecisionEvent: actor is required")
	}
	if e.Decision != "allow" && e.Decision != "deny" {
		return fmt.Errorf("PolicyDecisionEvent: decision must be 'allow' or 'deny', got %q", e.Decision)
	}
	return nil
}

// CreateResourceEvent records the creation of a governance resource.
type CreateResourceEvent struct {
	EventID      string    `json:"event_id"`
	EventTime    time.Time `json:"timestamp"`
	ResourceID   string    `json:"resource_id"`
	ResourceType string    `json:"resource_type"` // e.g., "policy", "capability", "rule"
	Name         string    `json:"name"`
	Version      string    `json:"version"`
	Metadata     map[string]string `json:"metadata"`
}

func (e *CreateResourceEvent) Type() EventType   { return EventTypeCreateResource }
func (e *CreateResourceEvent) Timestamp() time.Time { return e.EventTime }
func (e *CreateResourceEvent) ID() string        { return e.EventID }

// Validate checks that the event is well-formed.
func (e *CreateResourceEvent) Validate() error {
	if e.EventID == "" {
		return fmt.Errorf("CreateResourceEvent: event_id is required")
	}
	if e.ResourceID == "" {
		return fmt.Errorf("CreateResourceEvent: resource_id is required")
	}
	if e.ResourceType == "" {
		return fmt.Errorf("CreateResourceEvent: resource_type is required")
	}
	return nil
}

// UpdateStateEvent records a state mutation.
type UpdateStateEvent struct {
	EventID   string            `json:"event_id"`
	EventTime time.Time         `json:"timestamp"`
	Key       string            `json:"key"` // e.g., "governance_version", "audit_count"
	OldValue  string            `json:"old_value"`
	NewValue  string            `json:"new_value"`
	Reason    string            `json:"reason"`
}

func (e *UpdateStateEvent) Type() EventType   { return EventTypeUpdateState }
func (e *UpdateStateEvent) Timestamp() time.Time { return e.EventTime }
func (e *UpdateStateEvent) ID() string        { return e.EventID }

// Validate checks that the event is well-formed.
func (e *UpdateStateEvent) Validate() error {
	if e.EventID == "" {
		return fmt.Errorf("UpdateStateEvent: event_id is required")
	}
	if e.Key == "" {
		return fmt.Errorf("UpdateStateEvent: key is required")
	}
	return nil
}

// DeleteResourceEvent records the deletion of a resource.
type DeleteResourceEvent struct {
	EventID    string    `json:"event_id"`
	EventTime  time.Time `json:"timestamp"`
	ResourceID string    `json:"resource_id"`
	Reason     string    `json:"reason"`
}

func (e *DeleteResourceEvent) Type() EventType   { return EventTypeDeleteResource }
func (e *DeleteResourceEvent) Timestamp() time.Time { return e.EventTime }
func (e *DeleteResourceEvent) ID() string        { return e.EventID }

// Validate checks that the event is well-formed.
func (e *DeleteResourceEvent) Validate() error {
	if e.EventID == "" {
		return fmt.Errorf("DeleteResourceEvent: event_id is required")
	}
	if e.ResourceID == "" {
		return fmt.Errorf("DeleteResourceEvent: resource_id is required")
	}
	return nil
}

// EventEnvelope is used for JSON serialization with type discrimination.
// TODO(contract): This envelope is a convention; the actual serialization format
// may need to be defined in the contract.
type EventEnvelope struct {
	Type  EventType       `json:"type"`
	Event json.RawMessage `json:"event"`
}

// UnmarshalEvent decodes an event from JSON.
func UnmarshalEvent(data []byte) (Event, error) {
	var envelope EventEnvelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		return nil, fmt.Errorf("unmarshal event envelope: %w", err)
	}

	switch envelope.Type {
	case EventTypePolicyDecision:
		var e PolicyDecisionEvent
		if err := json.Unmarshal(envelope.Event, &e); err != nil {
			return nil, fmt.Errorf("unmarshal PolicyDecisionEvent: %w", err)
		}
		return &e, nil

	case EventTypeCreateResource:
		var e CreateResourceEvent
		if err := json.Unmarshal(envelope.Event, &e); err != nil {
			return nil, fmt.Errorf("unmarshal CreateResourceEvent: %w", err)
		}
		return &e, nil

	case EventTypeUpdateState:
		var e UpdateStateEvent
		if err := json.Unmarshal(envelope.Event, &e); err != nil {
			return nil, fmt.Errorf("unmarshal UpdateStateEvent: %w", err)
		}
		return &e, nil

	case EventTypeDeleteResource:
		var e DeleteResourceEvent
		if err := json.Unmarshal(envelope.Event, &e); err != nil {
			return nil, fmt.Errorf("unmarshal DeleteResourceEvent: %w", err)
		}
		return &e, nil

	default:
		return nil, fmt.Errorf("unknown event type: %s", envelope.Type)
	}
}

// MarshalEvent encodes an event to JSON.
func MarshalEvent(e Event) ([]byte, error) {
	eventData, err := json.Marshal(e)
	if err != nil {
		return nil, fmt.Errorf("marshal event: %w", err)
	}

	envelope := EventEnvelope{
		Type:  e.Type(),
		Event: json.RawMessage(eventData),
	}

	return json.Marshal(envelope)
}
