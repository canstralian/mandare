# ADR-0009: RIF Runtime as an execution kernel

## Status

Accepted. Implemented in `src/rif_runtime/kernel.py` and the stage modules it
composes.

## Context

RIF Runtime began as a policy engine that mediated individual actions. The
natural next step was to let it drive a model-backed agent. The tempting shape
is to make the agent the runtime and hang governance off it.

That inverts the trust model. An agent that owns the loop decides when to
consult policy; a runtime that owns the loop decides when to invoke an agent.

## Decision

**The agent is not the runtime. An execution engine is one capability the
runtime manages.** The kernel owns the pipeline:

```
Intent -> Context -> Governance -> State -> Budget -> Capability Router
      -> Execution -> Evidence -> Telemetry -> Evolution
```

The Microsoft Agent Framework — or any provider — plugs into the *Execution*
stage only, behind the `ExecutionEngine` protocol.

### Stage ownership

| Stage | Module | Notes |
| --- | --- | --- |
| Intent | `intent.py` | Records what arrived. Decides nothing. |
| Identity | `identity.py` | Actor → trust tier. Unknown resolves `untrusted`. |
| Context | `context.py` | Assembles instructions; fences untrusted text. |
| Governance | `governance/engine.py` | Wraps the existing `PolicyEngine`. |
| State | `state.py` | Posture, environment, runtime mode. |
| Budget | `budget.py` | Per-intent ceilings by trust tier. |
| Router | `capabilities.py` | Narrows what is offered. Not authorisation. |
| Execution | `execution.py` | `ExecutionEngine` protocol + approval gate. |
| Evidence | `evidence.py` | Hash-chained ledger over `audit.py`. |
| Telemetry | `telemetry.py` | Tokens, latency, calls, success. |
| Evolution | `evolution.py` | Queues proposals; never self-applies. |

## Consequences

### Governance is per-call, not pre-flight

This is the load-bearing decision, and it is where the design departs from the
obvious reading of the Agent Framework sample.

A pre-flight check judges the **intent**. The tool calls are chosen
**afterwards**, by a model, from text that may itself be adversarial. Approving
the intent and then auto-approving every resulting tool call —
`SkillsProvider.all_tools_auto_approval_rule` — places the model's chosen
actions outside governance entirely, which is precisely the boundary prompt
injection crosses.

So the kernel does both:

* `GovernanceEngine.evaluate(context)` — admission.
* `GovernanceEngine.evaluate_capability(...)` via `CapabilityApprovalGate` —
  once per tool invocation, during execution.

Every capability name is mapped into the `mcp.` action namespace before
evaluation (`capability_action`). Without that, a capability like `exploit.run`
reaches the policy engine as an action matching no rule and no built-in
constraint, and falls through to `default.allow` — silently ungoverned. This
was a real defect during implementation, caught by test, and is now covered by
`test_every_capability_lands_in_the_governed_action_namespace`.

### Evidence is recorded on every path, including denials

A denied intent is appended to the ledger *before* the safe response returns.
Recording only successes would drop exactly the events that drive posture
escalation and feed the evolution queue.

Per-call denials are committed through `RIFRuntime.record_decision`, so a tool
call the model chose and policy refused counts toward posture the same way a
denied HTTP request does. The reflexive loop, the graph, and the decision log
stay in agreement with the HTTP control plane.

### Model-agnostic in practice

`rif_runtime` depends on no model vendor. `ExecutionEngine` is a Protocol;
`EchoExecutionEngine` is a dependency-free reference implementation that
exercises the whole pipeline in CI. Provider adapters live in
`adapters/` and import their SDK lazily:

```bash
pip install -e '.[foundry]'
```

`AgentFrameworkEngine.check_mcp_egress` validates the MCP server URL against
the active environment profile before opening a session. Reading
`RIF_MCP_SERVER` straight from the environment would bypass the runtime's own
`allowed_hosts` and `allow_mcp_server_network_access` — the capability source
is itself subject to policy.

### Instructions are assembled, not hardcoded

`ContextAssembler` composes the system prompt from constitution, identity,
runtime mode, policies, and intent — in that order, so invariants precede any
request-derived text. The user request is *fenced*
(`UNTRUSTED_FENCE`), never interpolated into the instruction body.

### Evolution is queued, never automatic

Posture tightens automatically because it only ever tightens. Policy changes
can loosen, so they require an operator: the queue records a proposal and stops
there. Traffic never rewrites its own governance.

## Alternatives rejected

**Agent Framework as the orchestrator.** Would have made governance advisory —
consulted when the agent chose to. Rejected: the runtime must decide, not ask.

**Azure Foundry as a core dependency.** Contradicts model-agnostic execution
and couples the kernel to one cloud. Rejected in favour of the protocol seam.

**Auto-applying evolution proposals.** A runtime that widens its own policy in
response to denials can be walked open by generating denials. Rejected.

## References

- `docs/ARCHITECTURE.md` — the pre-kernel action-mediation design
- `docs/adr-0003-mcp-security-model.md` — capability classification
- `docs/adr-0006-ai-safety-rationale.md` — replay and audit rationale
