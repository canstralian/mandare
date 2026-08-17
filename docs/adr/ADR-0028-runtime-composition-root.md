# ADR-0028 — Runtime as composition root; transports as adapters

## Status

Accepted — incremental. This slice hardens the existing `RIFRuntime` boundary;
it does not introduce new aggregates or event contracts.

## Context

RIF has crossed the line from “Python project with an API” to a versioned,
deployable runtime artifact (container image + FastAPI + OpenAPI + health).
The next architectural risk is putting more behaviour into HTTP routes.

`RIFRuntime` already wires policy, posture, graph, stores, and Metasploit
governance, and both the FastAPI app and Typer CLI call into it. Gaps remained:

- `ReplayEngine` was constructed inside `api.py` / `cli.py`, not owned by the runtime.
- Posture set/reset mutated `runtime.posture` directly from the transport.
- `/v1/audit` constructed `AuditorAgent` in the route handler.

ADR-0008 already points at a control-plane composition (`runtime`, `lifecycle`,
…). This ADR records the binding rule for the current package layout before any
package move.

## Decision

**`RIFRuntime` is the composition root.** Every transport (HTTP, CLI, future
WebSocket / MCP / agent-to-agent) obtains one runtime instance and delegates.
Routes and commands adapt encoding and auth only; they do not own replay,
posture mutation, or audit assembly.

Concretely in this slice:

- `RIFRuntime` owns `ReplayEngine` (path-coupled to `decisions_store` by default;
  injectable for tests / `rif replay`).
- `set_posture` / `reset_posture` / `recovered_state` / `audit` are runtime
  methods; `api.py` and `cli.py` call through them.
- Optional constructor injection is limited to existing collaborators (`replay=`).
  No new registry or bus types in this PR.

## Explicit non-goals (deferred)

Do **not** introduce in this slice:

| Deferred | Why wait |
| --- | --- |
| `EventBus` / dispatcher | Needs Run-correlated event contracts (ADR-0010 identity spine); overlaps `TelemetryStore` |
| Top-level `ProviderRegistry` | ADR-0026: providers depend on resources; three registries already exist unwired |
| `control_plane/` package move | Structural rename per ADR-0008; separate PR after ownership is clear |
| New `/intent` (or other) endpoints | Stop growing the HTTP surface until internal ownership is stable |
| Image-size / multi-tag Docker policy | Operational packaging; orthogonal to composition |

## Consequences

- Adding a new interface means wiring to `RIFRuntime`, not re-implementing the
  governance circuit.
- Tests that monkeypatched `api.ReplayEngine` must inject or replace
  `runtime.replay` instead.
- Future EventBus / evidence ledger / provider work should attach *as
  collaborators of* `RIFRuntime` (or a successor composition root), after the
  relevant `spec/` contracts and Run aggregate rules are settled.

## Related

- ADR-0008 — AgentOS/RIF v1 governed runtime architecture (direction)
- ADR-0002 — Replayable governance memory
- ADR-0026 — Resource contracts (provider layering)
- `docs/spec-review-identity-spine-migration.md` — Run as sole aggregate root
