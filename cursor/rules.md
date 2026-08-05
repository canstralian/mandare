# Cursor Engineering Rules — RIF Studio v1

These rules are **non-negotiable**. They encode the RIF Runtime architectural
contract into the front-end layer. Every Cursor session must be prefixed with
the relevant rules for the files being edited.

---

## Core invariants

```
Never invent runtime state.
Everything is event-driven.
No component owns authoritative state.
Runtime emits events.
UI renders projections.
Every panel subscribes.
Every execution produces a GovernanceArtifact.
No mutable history.
Replay is deterministic.
```

---

## Rule index

| ID | Rule |
|----|------|
| R-01 | No authoritative state in components |
| R-02 | No direct API calls from components |
| R-03 | No panel-to-panel communication |
| R-04 | All events are immutable |
| R-05 | No cycles in the event bus |
| R-06 | Every execution produces a GovernanceArtifact |
| R-07 | History is append-only |
| R-08 | Replay must be deterministic |
| R-09 | No `any` in TypeScript |
| R-10 | Design tokens only — no inline values |
| R-11 | Governance hooks are mandatory for plugins |
| R-12 | Posture `locked` propagates immediately |

---

## R-01 — No authoritative state in components

Components render **projections** of events. They do not own or mutate state.

```typescript
// ✅ correct — projection from hook
const { posture } = usePosture();

// ❌ wrong — component inventing state
const [posture, setPosture] = useState<string>("normal");
```

---

## R-02 — No direct API calls from components

Components call hooks. Hooks subscribe to the event bus. The event bus is
populated by the runtime layer (`RuntimeAPI`, `RuntimeWebSocket`).

```typescript
// ✅ correct
const { decisions } = useDecisions();

// ❌ wrong — component importing runtime layer
import { RuntimeAPI } from "../runtime/RuntimeAPI";
const decisions = await RuntimeAPI.getAudit();
```

---

## R-03 — No panel-to-panel communication

Panels are siblings in the component tree. They do not hold references to each
other. Shared behaviour is coordinated via the event bus.

```typescript
// ✅ correct — panel emits an event; another panel reacts
emit({ type: "ArtifactSelected", payload: { id } });

// ❌ wrong — panel calling a sibling's method or accepting a ref to it
props.onSelect(artifactId);           // coupling via prop callback
siblingPanelRef.current.select(id);   // coupling via ref
```

---

## R-04 — All events are immutable

Event objects must use `readonly` on every property and must not be mutated
after emission.

```typescript
// ✅ correct
interface DecisionRecorded {
  readonly type: "DecisionRecorded";
  readonly timestamp: string;
  readonly payload: Readonly<PolicyDecision>;
}

// ❌ wrong
interface DecisionRecorded {
  type: string;      // not a literal
  payload: any;      // not typed
}
```

---

## R-05 — No cycles in the event bus

A subscriber handler must not call `emit` inside its own body. Emit in response
to user actions or to API responses — not in response to another event.

```typescript
// ❌ wrong — cycle
eventBus.subscribe("PostureChanged", (event) => {
  eventBus.emit({ type: "PostureChanged", ... }); // infinite loop
});
```

---

## R-06 — Every execution produces a GovernanceArtifact

Every call that passes through `POST /v1/policy/evaluate` must result in an
`ArtifactCommitted` event being emitted on the bus. The `EvidenceLedger`
component is the UI witness of this invariant.

If `ArtifactCommitted` is not emitted, the execution is not governed and must
not proceed.

---

## R-07 — History is append-only

The decisions list, audit log, and evidence ledger grow monotonically. No UI
action may delete or modify a past entry.

```typescript
// ✅ correct
const newDecisions = [...prev, incoming];

// ❌ wrong
prev.splice(index, 1);    // deletion
prev[index] = incoming;   // mutation
```

---

## R-08 — Replay is deterministic

Given the same `decisions.jsonl` input, `ReplayTimeline` must render the
identical sequence of steps regardless of when or how many times it is run.
Replay state is derived solely from the recorded events — never from current
wall-clock time, random values, or live API calls.

```typescript
// ✅ correct — all replay state derived from loaded events
const steps = loadReplaySteps(decisionsJson);

// ❌ wrong — mixing live state into replay
const steps = [...loadReplaySteps(decisionsJson), ...liveDecisions];
```

---

## R-09 — No `any` in TypeScript

Every value that crosses a module boundary must be fully typed. Use `unknown`
for untyped external data and narrow with type guards before use.

```typescript
// ✅ correct
function parseEvent(raw: unknown): RuntimeEvent {
  if (!isRuntimeEvent(raw)) throw new TypeError("...");
  return raw;
}

// ❌ wrong
function parseEvent(raw: any): any { return raw; }
```

---

## R-10 — Design tokens only

No colour, spacing, typography, shadow, or animation value may be written
inline. Import from `src/design/` and apply via CSS variables or the token map.

```typescript
// ✅ correct
import { colorTokens } from "../design/color-tokens";
style={{ color: colorTokens["--rif-color-status-denied"] }}

// ❌ wrong
style={{ color: "#ff4444" }}
```

---

## R-11 — Governance hooks are mandatory for plugins

Every plugin registered in `CapabilityPanel` must declare `governanceHooks` in
its manifest (see `spec/capability/`). A plugin without governance hooks must
not be activated and must be rendered in a `locked` / disabled state.

---

## R-12 — Posture `locked` propagates immediately

When a `PostureLocked` event is received, every panel must reflect the locked
state within the same render cycle. No panel may continue rendering interactive
controls when posture is `locked`.

```typescript
// ✅ correct — checked at render time
if (posture === "locked") return <LockedOverlay />;

// ❌ wrong — async check allows brief interactive window
useEffect(() => {
  if (posture === "locked") setIsLocked(true);
}, [posture]);
```

---

## Enforcement

These rules should be included in `.cursor/rules` (Cursor project rules) so
they are automatically injected into every session. The `runtime-architect`
agent in `.cursor/agents/runtime-architect.md` performs automated review
against these rules before any phase is marked complete.
