package core

import (
	"testing"
	"time"
)

// TestReplaySuccessful verifies that a valid event sequence replays correctly.
func TestReplaySuccessful(t *testing.T) {
	tests := []struct {
		name     string
		events   func() *EventLog
		validate func(*State) error
	}{
		{
			name: "single policy decision",
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&PolicyDecisionEvent{
					EventID:   "evt-1",
					EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					Actor:     "agent:test",
					Action:    "execute",
					Target:    "resource:prod",
					Decision:  "allow",
					Reason:    "trusted actor",
					Priority:  100,
				})
				return log
			},
			validate: func(s *State) error {
				if s.DecisionCount != 1 {
					return errorf("expected 1 decision, got %d", s.DecisionCount)
				}
				if s.AllowDecisionCount != 1 {
					return errorf("expected 1 allow, got %d", s.AllowDecisionCount)
				}
				if s.DenyDecisionCount != 0 {
					return errorf("expected 0 denies, got %d", s.DenyDecisionCount)
				}
				return nil
			},
		},
		{
			name: "create resource",
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&CreateResourceEvent{
					EventID:      "evt-1",
					EventTime:    time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					ResourceID:   "policy:v1",
					ResourceType: "policy",
					Name:         "Production Policy",
					Version:      "1.0.0",
					Metadata:     map[string]string{"owner": "alice"},
				})
				return log
			},
			validate: func(s *State) error {
				if len(s.Resources) != 1 {
					return errorf("expected 1 resource, got %d", len(s.Resources))
				}
				res, ok := s.Resources["policy:v1"]
				if !ok {
					return errorf("resource policy:v1 not found")
				}
				if res.Name != "Production Policy" {
					return errorf("expected name 'Production Policy', got %q", res.Name)
				}
				if res.Version != "1.0.0" {
					return errorf("expected version '1.0.0', got %q", res.Version)
				}
				return nil
			},
		},
		{
			name: "update state and create resource",
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&UpdateStateEvent{
					EventID:   "evt-1",
					EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					Key:       "governance_version",
					OldValue:  "0",
					NewValue:  "1",
					Reason:    "initial setup",
				})
				log.Append(&CreateResourceEvent{
					EventID:      "evt-2",
					EventTime:    time.Date(2025, 1, 15, 10, 31, 0, 0, time.UTC),
					ResourceID:   "policy:v1",
					ResourceType: "policy",
					Name:         "Base Policy",
					Version:      "1.0.0",
					Metadata:     map[string]string{},
				})
				return log
			},
			validate: func(s *State) error {
				if s.Metadata["governance_version"] != "1" {
					return errorf("expected governance_version=1, got %q", s.Metadata["governance_version"])
				}
				if len(s.Resources) != 1 {
					return errorf("expected 1 resource, got %d", len(s.Resources))
				}
				if s.Version != 2 {
					return errorf("expected version 2 after 2 events, got %d", s.Version)
				}
				return nil
			},
		},
		{
			name: "create and delete resource",
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&CreateResourceEvent{
					EventID:      "evt-1",
					EventTime:    time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					ResourceID:   "policy:v1",
					ResourceType: "policy",
					Name:         "Temp Policy",
					Version:      "1.0.0",
					Metadata:     map[string]string{},
				})
				log.Append(&DeleteResourceEvent{
					EventID:    "evt-2",
					EventTime:  time.Date(2025, 1, 15, 10, 31, 0, 0, time.UTC),
					ResourceID: "policy:v1",
					Reason:     "cleanup",
				})
				return log
			},
			validate: func(s *State) error {
				if len(s.Resources) != 0 {
					return errorf("expected 0 resources after delete, got %d", len(s.Resources))
				}
				if s.Version != 3 {
					return errorf("expected version 3 after 2 events, got %d", s.Version)
				}
				return nil
			},
		},
		{
			name: "mixed decisions",
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&PolicyDecisionEvent{
					EventID:   "evt-1",
					EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					Actor:     "agent:trusted",
					Action:    "write",
					Target:    "db:prod",
					Decision:  "allow",
					Reason:    "trusted actor",
					Priority:  100,
				})
				log.Append(&PolicyDecisionEvent{
					EventID:   "evt-2",
					EventTime: time.Date(2025, 1, 15, 10, 31, 0, 0, time.UTC),
					Actor:     "agent:unknown",
					Action:    "read",
					Target:    "secrets:prod",
					Decision:  "deny",
					Reason:    "unknown actor",
					Priority:  50,
				})
				log.Append(&PolicyDecisionEvent{
					EventID:   "evt-3",
					EventTime: time.Date(2025, 1, 15, 10, 32, 0, 0, time.UTC),
					Actor:     "agent:trusted",
					Action:    "delete",
					Target:    "logs:old",
					Decision:  "allow",
					Reason:    "maintenance task",
					Priority:  100,
				})
				return log
			},
			validate: func(s *State) error {
				if s.DecisionCount != 3 {
					return errorf("expected 3 decisions, got %d", s.DecisionCount)
				}
				if s.AllowDecisionCount != 2 {
					return errorf("expected 2 allows, got %d", s.AllowDecisionCount)
				}
				if s.DenyDecisionCount != 1 {
					return errorf("expected 1 deny, got %d", s.DenyDecisionCount)
				}
				return nil
			},
		},
	}

	engine := NewReplayEngine()
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			initial := NewState()
			initial.Metadata["governance_version"] = "0"

			log := tt.events()
			state, err := engine.Replay(initial, log)
			if err != nil {
				t.Fatalf("replay failed: %v", err)
			}

			if err := tt.validate(state); err != nil {
				t.Errorf("validation failed: %v", err)
			}
		})
	}
}

// TestReplayErrors verifies that invalid event sequences are rejected.
func TestReplayErrors(t *testing.T) {
	tests := []struct {
		name      string
		initial   *State
		events    *EventLog
		wantError bool
		errMsg    string
	}{
		{
			name:      "nil initial state",
			initial:   nil,
			events:    NewEventLog(),
			wantError: true,
			errMsg:    "initial state is nil",
		},
		{
			name:      "nil event log",
			initial:   NewState(),
			events:    nil,
			wantError: true,
			errMsg:    "event log is nil",
		},
		{
			name: "update non-existent key",
			initial: NewState(),
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&UpdateStateEvent{
					EventID:   "evt-1",
					EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					Key:       "nonexistent",
					OldValue:  "old",
					NewValue:  "new",
					Reason:    "test",
				})
				return log
			}(),
			wantError: true,
			errMsg:    "does not exist",
		},
		{
			name: "create duplicate resource",
			initial: func() *State {
				s := NewState()
				s.Resources["policy:v1"] = &Resource{
					ID:   "policy:v1",
					Type: "policy",
				}
				return s
			}(),
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&CreateResourceEvent{
					EventID:      "evt-1",
					EventTime:    time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					ResourceID:   "policy:v1",
					ResourceType: "policy",
					Name:         "Duplicate",
					Version:      "1.0.0",
					Metadata:     map[string]string{},
				})
				return log
			}(),
			wantError: true,
			errMsg:    "already exists",
		},
		{
			name:    "delete non-existent resource",
			initial: NewState(),
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&DeleteResourceEvent{
					EventID:    "evt-1",
					EventTime:  time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					ResourceID: "policy:v1",
					Reason:     "cleanup",
				})
				return log
			}(),
			wantError: true,
			errMsg:    "does not exist",
		},
		{
			name:    "invalid policy decision",
			initial: NewState(),
			events: func() *EventLog {
				log := NewEventLog()
				log.Append(&PolicyDecisionEvent{
					EventID:   "evt-1",
					EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
					Actor:     "agent:test",
					Action:    "execute",
					Target:    "resource:prod",
					Decision:  "maybe", // Invalid
					Reason:    "test",
					Priority:  100,
				})
				return log
			}(),
			wantError: true,
			errMsg:    "invalid decision",
		},
	}

	engine := NewReplayEngine()
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := engine.Replay(tt.initial, tt.events)
			if !tt.wantError && err != nil {
				t.Errorf("unexpected error: %v", err)
			}
			if tt.wantError && err == nil {
				t.Error("expected error, got nil")
			}
			if tt.wantError && err != nil && tt.errMsg != "" && !contains(err.Error(), tt.errMsg) {
				t.Errorf("expected error containing %q, got: %v", tt.errMsg, err)
			}
		})
	}
}

// TestDeterminism verifies that replaying the same log twice produces identical states.
func TestDeterminism(t *testing.T) {
	engine := NewReplayEngine()

	// Create a complex event log
	log := NewEventLog()
	log.Append(&UpdateStateEvent{
		EventID:   "evt-1",
		EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
		Key:       "version",
		OldValue:  "0",
		NewValue:  "1",
		Reason:    "setup",
	})
	log.Append(&CreateResourceEvent{
		EventID:      "evt-2",
		EventTime:    time.Date(2025, 1, 15, 10, 31, 0, 0, time.UTC),
		ResourceID:   "policy:v1",
		ResourceType: "policy",
		Name:         "Test Policy",
		Version:      "1.0.0",
		Metadata:     map[string]string{"owner": "alice", "env": "prod"},
	})
	log.Append(&PolicyDecisionEvent{
		EventID:   "evt-3",
		EventTime: time.Date(2025, 1, 15, 10, 32, 0, 0, time.UTC),
		Actor:     "agent:test",
		Action:    "execute",
		Target:    "resource:prod",
		Decision:  "allow",
		Reason:    "approved",
		Priority:  100,
	})

	initial := NewState()
	initial.Metadata["version"] = "0"

	// Verify determinism
	if err := engine.DeterminismCheck(initial, log); err != nil {
		t.Fatalf("determinism check failed: %v", err)
	}

	// Also verify by replaying twice manually
	state1, _ := engine.Replay(initial, log)
	state2, _ := engine.Replay(initial, log)

	if !state1.Equal(state2) {
		t.Error("replay produced different states")
	}
}

// TestHash verifies that the hash of a log is deterministic.
func TestHash(t *testing.T) {
	engine := NewReplayEngine()

	log := NewEventLog()
	log.Append(&PolicyDecisionEvent{
		EventID:   "evt-1",
		EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
		Actor:     "agent:test",
		Action:    "execute",
		Target:    "resource:prod",
		Decision:  "allow",
		Reason:    "approved",
		Priority:  100,
	})

	// Hash twice
	hash1, err := engine.Hash(log)
	if err != nil {
		t.Fatalf("first hash failed: %v", err)
	}

	hash2, err := engine.Hash(log)
	if err != nil {
		t.Fatalf("second hash failed: %v", err)
	}

	if hash1 != hash2 {
		t.Errorf("hash is non-deterministic: %s != %s", hash1, hash2)
	}

	// Verify hash is not empty and looks like SHA256
	if len(hash1) != 64 {
		t.Errorf("expected 64-char hex SHA256, got %d chars", len(hash1))
	}
}

// TestSerialization verifies round-trip JSON serialization.
func TestSerialization(t *testing.T) {
	log := NewEventLog()
	log.Append(&PolicyDecisionEvent{
		EventID:   "evt-1",
		EventTime: time.Date(2025, 1, 15, 10, 30, 0, 0, time.UTC),
		Actor:     "agent:test",
		Action:    "execute",
		Target:    "resource:prod",
		Decision:  "allow",
		Reason:    "approved",
		Priority:  100,
	})
	log.Append(&CreateResourceEvent{
		EventID:      "evt-2",
		EventTime:    time.Date(2025, 1, 15, 10, 31, 0, 0, time.UTC),
		ResourceID:   "policy:v1",
		ResourceType: "policy",
		Name:         "Policy",
		Version:      "1.0.0",
		Metadata:     map[string]string{"key": "value"},
	})

	// Serialize
	data, err := log.SerializeCanonical()
	if err != nil {
		t.Fatalf("serialize failed: %v", err)
	}

	// Deserialize
	log2, err := DeserializeCanonical(data)
	if err != nil {
		t.Fatalf("deserialize failed: %v", err)
	}

	if log2.Length() != 2 {
		t.Errorf("expected 2 events after round-trip, got %d", log2.Length())
	}

	// Serialize again and compare bytes
	data2, _ := log2.SerializeCanonical()
	if string(data) != string(data2) {
		t.Error("serialization is non-deterministic after round-trip")
	}
}

// TestEmptyLog verifies behavior with empty logs.
func TestEmptyLog(t *testing.T) {
	engine := NewReplayEngine()
	initial := NewState()
	log := NewEventLog()

	state, err := engine.Replay(initial, log)
	if err != nil {
		t.Fatalf("replay empty log failed: %v", err)
	}

	if state.DecisionCount != 0 {
		t.Errorf("expected 0 decisions, got %d", state.DecisionCount)
	}

	// Empty log should have a valid hash
	hash, err := engine.Hash(log)
	if err != nil {
		t.Fatalf("hash empty log failed: %v", err)
	}
	if hash == "" {
		t.Error("hash of empty log is empty")
	}
}

// TestDeepCopy verifies that DeepCopy is truly independent.
func TestDeepCopy(t *testing.T) {
	original := NewState()
	original.Metadata["key"] = "value"
	original.Resources["res1"] = &Resource{
		ID:       "res1",
		Type:     "policy",
		Metadata: map[string]string{"owner": "alice"},
	}

	copy := original.DeepCopy()

	// Modify the copy
	copy.Metadata["key"] = "modified"
	copy.Resources["res1"].Metadata["owner"] = "bob"

	// Original should be unchanged
	if original.Metadata["key"] != "value" {
		t.Error("original metadata was modified by copy")
	}
	if original.Resources["res1"].Metadata["owner"] != "alice" {
		t.Error("original resource metadata was modified by copy")
	}
}

// Helper functions

func errorf(format string, args ...interface{}) error {
	return fmt.Errorf(format, args...)
}

func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// Import needed for errorf
import "fmt"
