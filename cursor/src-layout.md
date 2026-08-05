# Source Layout — RIF Studio v1

Every file listed here has exactly one responsibility. Create them in the order
shown. Files in later sections may only import from sections above them.

---

## Section 0 — Project configuration (create first, no imports)

| File | Responsibility |
|------|---------------|
| `studio/package.json` | Dependencies, scripts (`dev`, `build`, `typecheck`, `lint`, `test`, `test:acceptance`) |
| `studio/tsconfig.json` | Strict TypeScript config; `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` |
| `studio/vite.config.ts` | Vite + React plugin; proxy `/v1` to `http://127.0.0.1:8000` |
| `studio/index.html` | Entry HTML; mounts `<div id="rif-root">` |

---

## Section 1 — Event bus and type definitions (`src/events/`)

**Rule:** no imports from any other `src/` subdirectory.

| File | Responsibility |
|------|---------------|
| `src/events/EventBus.ts` | Singleton pub/sub bus: `subscribe(topic, handler)`, `emit(event)`, `unsubscribe(id)`. All events are delivered synchronously in emission order. No cycles: a handler may not call `emit` inside a `subscribe` callback. |
| `src/events/RuntimeEvents.ts` | Typed event definitions for the runtime connection lifecycle: `RuntimeConnected`, `RuntimeDisconnected`, `RuntimeError`, `PostureChanged`, `EnvironmentSwitched` |
| `src/events/GovernanceEvents.ts` | `DecisionRecorded`, `PostureLocked`, `PostureReset`, `PolicyAdded`, `PolicyRemoved` |
| `src/events/ExecutionEvents.ts` | `IntentReceived`, `PlanningStarted`, `EvidenceFound`, `GovernanceApproved`, `ExecutionStarted`, `ExecutionFinished`, `ArtifactCommitted` |
| `src/events/TelemetryEvents.ts` | `TelemetryUpdated`, `BudgetUpdated` |
| `src/events/ReplayEvents.ts` | `ReplayStarted`, `ReplayStepApplied`, `ReplayFinished`, `ReplayFailed` |
| `src/events/index.ts` | Re-exports all event types and the `EventBus` singleton |

---

## Section 2 — Design system tokens (`src/design/`)

**Rule:** no imports from any other `src/` subdirectory.

| File | Responsibility |
|------|---------------|
| `src/design/color-tokens.ts` | All colour values keyed as `--rif-color-*`; includes status colours (`allowed`, `denied`, `locked`, `elevated`, `restricted`) |
| `src/design/typography-tokens.ts` | Font families, sizes, weights, line-heights as `--rif-text-*` |
| `src/design/spacing-tokens.ts` | Spacing scale as `--rif-space-{n}` (4 px base unit) |
| `src/design/elevation-tokens.ts` | Box-shadow levels as `--rif-elevation-{0..5}` |
| `src/design/motion-tokens.ts` | Duration and easing values as `--rif-motion-*` |
| `src/design/grid-tokens.ts` | Panel grid columns, gutter, max-width as `--rif-grid-*` |
| `src/design/index.ts` | Re-exports all token maps; also exports `applyTokens()` which injects CSS variables into `:root` |

---

## Section 3 — Runtime client (`src/runtime/`)

**Rule:** may import from `src/events/` only.

| File | Responsibility |
|------|---------------|
| `src/runtime/RuntimeTypes.ts` | TypeScript interfaces mirroring the Python Pydantic models: `PolicyRequest`, `PolicyDecision`, `EnvironmentProfile`, `RuntimeConfig`, `PostureValue`, `GraphSummary`, `TelemetrySummary`, `AuditEntry`, `PolicyRule` |
| `src/runtime/RuntimeAPI.ts` | Thin fetch wrapper for every HTTP route in `docs/API.md`. Each method emits the appropriate typed event on success and a `RuntimeError` event on failure. Never throws. Returns `void`. |
| `src/runtime/RuntimeWebSocket.ts` | Opens a WebSocket to `/v1/events` (or equivalent). Parses incoming JSON frames, validates against `RuntimeTypes`, emits typed events. Handles reconnect with exponential back-off (max 30 s). Emits `RuntimeConnected` / `RuntimeDisconnected`. |
| `src/runtime/RuntimeStore.ts` | Subscribes to `RuntimeEvents` and `GovernanceEvents`. Maintains a read-only snapshot of: current posture, active environment, last N decisions (ring buffer, max 500). Exposes `getSnapshot()` — returns a frozen object. Never mutates returned values. |
| `src/runtime/RuntimeContext.tsx` | React context that provides the `RuntimeStore` snapshot to the component tree. Updated whenever the store emits a change notification. |

---

## Section 4 — React hooks (`src/hooks/`)

**Rule:** may import from `src/events/` and `src/runtime/` only.

| File | Responsibility |
|------|---------------|
| `src/hooks/useRuntime.ts` | Returns the current `RuntimeStore` snapshot from `RuntimeContext`. Re-renders on every store change. |
| `src/hooks/usePosture.ts` | Subscribes to `PostureChanged` and `PostureLocked`. Returns `{ posture, lockedAt, history }`. |
| `src/hooks/useDecisions.ts` | Subscribes to `DecisionRecorded`. Returns paginated decision list with `{ decisions, total, hasMore }`. |
| `src/hooks/useTelemetry.ts` | Subscribes to `TelemetryUpdated` and `BudgetUpdated`. Returns the current telemetry summary. |
| `src/hooks/useReplay.ts` | Subscribes to `ReplayStarted`, `ReplayStepApplied`, `ReplayFinished`, `ReplayFailed`. Returns `{ status, steps, currentStep, error }`. |
| `src/hooks/useGovernanceGraph.ts` | Polls `GET /v1/graph/summary` on a configurable interval (default 5 s) and emits results as `GraphSummary` events. Returns the latest summary. |
| `src/hooks/useAudit.ts` | Subscribes to `ArtifactCommitted`. Returns the ordered list of audit entries since mount. |

---

## Section 5 — Components (`src/components/`)

**Rule:** may import from `src/hooks/`, `src/design/`, and `src/events/` only.
Components must never import from `src/runtime/` directly.

### Shell and layout

| Component | Responsibility |
|-----------|---------------|
| `RuntimeShell/` | Root layout: mounts `TopBar`, `Sidebar`, `main panel area`, `StatusBar`. Provides `RuntimeContext`. Renders a full-screen error boundary if `RuntimeDisconnected` fires. |
| `TopBar/` | Displays: runtime version, active environment name, connection status indicator. No actions — display only. |
| `Sidebar/` | Navigation rail listing available panels. Highlights the active panel. Emits a `NavigationChanged` event when user selects a panel. Renders denied panels as locked when posture is `locked`. |
| `StatusBar/` | Displays: current posture (with status colour), last decision timestamp, event-bus message count. Updates in real time. |

### Governance panels

| Component | Responsibility |
|-----------|---------------|
| `GovernancePanel/` | Primary governance view: posture gauge, recent decisions table, policy rule list. Each row in the decisions table links to `ArtifactViewer`. Uses `usePosture` and `useDecisions`. |
| `PostureGauge/` | Visual indicator for `normal \| elevated \| restricted \| locked`. Uses status colour tokens. Animates transitions using motion tokens. |
| `DecisionTable/` | Paginated, filterable table of `PolicyDecision` records. Columns: timestamp, actor, action, target, decision, posture at time. |
| `PolicyList/` | Reads policy rules from `GET /v1/policies` (via hook). Renders each rule. Emits `PolicyAdded` / `PolicyRemoved` events when user adds/removes rules. |

### Replay panels

| Component | Responsibility |
|-----------|---------------|
| `ReplayTimeline/` | Horizontal scrubber over a loaded replay session. Each tick is a `DecisionRecorded` event in the replay. Uses `useReplay`. Supports play, pause, step-forward, step-back. |
| `ReplayControls/` | Transport buttons (play/pause/stop/step) that emit `ReplayStarted`, `ReplayStepApplied`, `ReplayFinished`. Never modify replay data. |

### Evidence and audit

| Component | Responsibility |
|-----------|---------------|
| `EvidenceLedger/` | Ordered list of `GovernanceArtifact` records emitted during the current session. Entries are append-only — no editing. Uses `useAudit`. |
| `ArtifactViewer/` | Detail view for a single `GovernanceArtifact`. Shows: actor, action, target, decision, evidence chain, posture at time, raw JSON toggle. Read-only. |

### Telemetry and models

| Component | Responsibility |
|-----------|---------------|
| `TelemetryPanel/` | Rolling time-series charts for: decisions/min, allow rate, deny rate, posture transitions. Uses `useTelemetry`. Renders sparklines with motion tokens for updates. |
| `ModelPanel/` | Lists registered model providers, their status, and inference budget consumption. Uses `useGovernanceGraph`. |
| `CapabilityPanel/` | Reads `GET /v1/environments` and the capability manifest from `spec/capability/`. Displays which capabilities are allowed / denied per environment. |

### Developer tools

| Component | Responsibility |
|-----------|---------------|
| `Terminal/` | Read-only event log stream. Subscribes to all event bus topics and appends formatted lines. Supports filtering by event type. Never sends commands to the runtime. |

---

## Section 6 — Utilities (`src/utils/`)

**Rule:** pure functions only; no side-effects; no imports from other `src/` subdirectories.

| File | Responsibility |
|------|---------------|
| `src/utils/formatDecision.ts` | Formats a `PolicyDecision` into a human-readable string |
| `src/utils/formatTimestamp.ts` | ISO 8601 → locale-aware display string |
| `src/utils/postureColor.ts` | Maps a `PostureValue` to a design token key |
| `src/utils/ringBuffer.ts` | Fixed-size append-only ring buffer (used by `RuntimeStore`) |
| `src/utils/backoff.ts` | Exponential back-off calculator (used by `RuntimeWebSocket`) |

---

## Section 7 — Tests (`studio/tests/`)

| Directory | Contents |
|-----------|----------|
| `tests/unit/` | Vitest unit tests mirroring `src/` structure; one test file per source file |
| `tests/integration/` | Tests that spin up `RuntimeAPI` against a live `rif serve` process using MSW or direct fetch |
| `tests/acceptance/` | Playwright end-to-end acceptance tests; scenarios defined in `studio/docs/016_TESTING.md` |

Every acceptance scenario must correspond to a named test in `tests/acceptance/`.
A passing acceptance run is the final gate before any phase is marked complete.
