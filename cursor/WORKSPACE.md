# Cursor Workspace Guide — RIF Studio v1

This document defines how Cursor should operate inside the RIF Studio TypeScript
front-end. It covers file organisation, naming conventions, per-file
responsibilities, and the prompt checkpoints that keep Cursor aligned with the
governing architecture.

> **Authoritative references**
>
> * `spec/` — versioned contracts (capability, governance, evidence, replay, skill, state)
> * `CLAUDE.md` — runtime architecture and conventions
> * `cursor/src-layout.md` — every file's single responsibility
> * `cursor/rules.md` — non-negotiable engineering constraints

---

## 1. Repository structure

```
rif-runtime/               ← Python runtime (do not modify from this workspace)
  src/rif_runtime/
  tests/
  spec/

studio/                    ← RIF Studio TypeScript front-end (Cursor's domain)
  src/
    runtime/               ← thin runtime client layer
    components/            ← React panels and widgets
    events/                ← event bus and type definitions
    hooks/                 ← React hooks (read-only subscriptions)
    design/                ← design system tokens
    utils/                 ← pure helpers, no side-effects
  tests/
    unit/
    integration/
    acceptance/
  public/
  index.html
  vite.config.ts
  tsconfig.json
  package.json
```

Cursor **must not** modify anything outside `studio/`. The Python runtime is a
separate process; Cursor's only interface to it is the HTTP API documented in
`docs/API.md` and the WebSocket event stream described in
`studio/docs/014_WEBSOCKETS.md`.

---

## 2. File naming conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Runtime client | `PascalCase.ts` | `RuntimeAPI.ts` |
| React component | `PascalCase/index.tsx` + `PascalCase.tsx` | `GovernancePanel/index.tsx` |
| Event definitions | `PascalCaseEvents.ts` | `RuntimeEvents.ts` |
| Type declarations | `PascalCaseTypes.ts` | `RuntimeTypes.ts` |
| React context | `PascalCaseContext.tsx` | `RuntimeContext.tsx` |
| Store / state | `PascalCaseStore.ts` | `RuntimeStore.ts` |
| Hook | `use + PascalCase.ts` | `usePosture.ts` |
| Design token | `kebab-case.ts` | `color-tokens.ts` |
| Utility | `camelCase.ts` | `formatDecision.ts` |
| Test (unit) | mirrors source + `.test.ts(x)` | `RuntimeAPI.test.ts` |
| Test (acceptance) | `kebab-case.acceptance.ts` | `replay-pass.acceptance.ts` |

---

## 3. Prompt checkpoints

Use these checkpoints as Cursor prompt preambles when creating or editing files
in each layer. They prevent architectural drift.

### 3.1 Runtime layer (`src/runtime/`)

```
You are implementing a thin client for the RIF Runtime HTTP API.
Rules:
- Never hold authoritative state; only fetch and emit.
- Every API response MUST be emitted as a typed event onto the event bus.
- No component imports from this layer directly; they use hooks only.
- Error responses must emit a RuntimeError event, never throw to the caller.
```

### 3.2 Event bus (`src/events/`)

```
You are defining the RIF Studio event bus and its event taxonomy.
Rules:
- All events are immutable value objects (readonly properties only).
- Every event carries: type (string literal), timestamp (ISO 8601), and payload.
- No event carries mutable references.
- Subscribers may not emit events inside a subscription handler (no cycles).
```

### 3.3 Components (`src/components/`)

```
You are implementing a RIF Studio panel or widget.
Rules:
- This component owns NO authoritative state.
- All data comes from a hook that subscribes to the event bus.
- This component never calls the runtime API directly.
- This component never communicates with another component directly.
- Props are display data only; callbacks emit events, never mutate state.
- Every component must have a loading state and an error state.
```

### 3.4 Hooks (`src/hooks/`)

```
You are implementing a React hook for a RIF Studio panel.
Rules:
- The hook subscribes to one or more event bus topics.
- The hook returns a projection derived from received events.
- The hook must unsubscribe on unmount.
- No network calls inside hooks; delegate to the runtime layer.
```

### 3.5 Design system (`src/design/`)

```
You are implementing or consuming RIF Studio design tokens.
Rules:
- Import tokens only from src/design/; never hard-code colours, spacing, or
  typography values inline.
- Token names follow the pattern: --rif-{category}-{variant}-{state}.
- Do not introduce a new visual primitive without a corresponding token.
```

---

## 4. Creation order

Follow `cursor/src-layout.md` for the exact sequence. In summary:

1. `src/events/` — define all event types first (no dependencies)
2. `src/design/` — design tokens (no dependencies)
3. `src/runtime/` — API client + store (depends on event types only)
4. `src/hooks/` — subscriptions (depends on event bus + runtime store)
5. `src/components/` — panels (depends on hooks + design tokens only)
6. `tests/` — write acceptance tests against the running server

Never skip ahead. A component that imports directly from `src/runtime/` instead
of a hook is an architectural violation.

---

## 5. Cursor-specific settings

The `.cursor/` directory at the repository root already contains agent definitions
for documentation, testing, and release engineering. When working in `studio/`,
refer to those agents for:

* **`documentation-engineer.md`** — generating or updating `studio/docs/`
* **`test-engineer.md`** — scaffolding acceptance and integration tests
* **`runtime-architect.md`** — validating that new components comply with the
  event-driven contract

---

## 6. What Cursor must never do

| Prohibited | Why |
|------------|-----|
| Invent runtime state | Violates the "no authoritative state in UI" principle |
| Call the runtime API from a component | Bypasses the event bus |
| Let two panels share a mutable reference | Creates hidden coupling |
| Hard-code colour / spacing values | Breaks the design system |
| Import from `src/rif_runtime/` (Python) | Wrong layer, wrong language |
| Write to `data/decisions.jsonl` | That file belongs to the Python runtime |
| Disable governance hooks in a plugin | Governance is non-negotiable |
| Use `any` types in TypeScript | Every boundary must be typed |

---

## 7. Acceptance gate

Before a Cursor session is considered complete, the following must pass:

```bash
cd studio
pnpm typecheck          # tsc --noEmit
pnpm lint               # eslint src
pnpm test               # vitest run
pnpm test:acceptance    # playwright test
```

These mirror the CI gates defined in `.github/workflows/ci.yml` for the Python
runtime. A green acceptance run is the definition of done.
