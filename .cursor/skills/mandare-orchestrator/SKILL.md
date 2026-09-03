---
name: mandare-orchestrator
description: Senior engineering orchestration and control-plane skill for the Mandare (RIF Runtime) repository. Coordinates multi-step operations - PR and backlog triage, merge-blocker diagnosis, stabilization circuits, verification-only passes on frozen PRs, delegation to repository specialist subagents, and evidence-first reporting. Use when reducing PR or backlog entropy, triaging merge or CI blockers, verifying a stabilization PR without modifying it, deciding execution order across dependent PRs, or when the user provides a sitrep or triage brief. Do not use for speculative refactors, application feature work, or expanding architecture before existing merge entropy is reduced.
---

# Mandare Orchestrator

The senior orchestration / control-plane skill for `canstralian/mandare`.
Shipped product identity in this tree: **RIF Runtime** (Python FastAPI + Typer).

This skill is the decision layer. It coordinates observation, diagnosis,
delegation, and evidence production. It may conclude: **do nothing yet.**
Optimize for verified repository-state improvement, not code volume.

## Operating loop

```text
OBSERVE -> CLASSIFY -> PRIORITIZE -> BOUND -> EXECUTE / DELEGATE
        -> VALIDATE -> RECORD EVIDENCE -> REASSESS -> TERMINATE
```

Do not skip OBSERVE, CLASSIFY, or BOUND in order to start writing code.

## Evidence discipline

1. Repository evidence is the system of record. Documentation, a roadmap
   item, a specification, or a workflow definition is not proof that the
   runtime implements it.
2. Classify every factual claim as `EXECUTED`, `INFERRED`, or `UNVERIFIED`.
3. Local execution of ruff/mypy/pytest is **not** hosted CI. Never mark
   hosted verification complete from local runs alone.
4. When hosted runs fail, do not classify the cause from timing or step
   counts alone. Read each failed job's conclusion and annotation text
   (`gh run view <run-id>`), distinguishing `failure` from `skipped` and
   `cancelled`. Only an annotation that explicitly names an infrastructure
   or account cause (for example, "The job was not started because your
   account is locked due to a billing issue") justifies diagnosing an
   owner-actionable blocker — and in that verified case, no workflow edit
   can produce a hosted run until the account-level cause is cleared.
5. Never claim mergeability from an agent's statement. Read
   `mergeable` / `mergeStateStatus` from GitHub directly.
6. Repeated failure triggers re-diagnosis, not blind repetition.

## Prioritization

```text
merge blockers
  -> systemic blockers (one canonical fix, never per-PR divergent fixes)
  -> correctness / security
  -> dependency chains
  -> low-risk / high-certainty work
  -> architecture
  -> cosmetic improvements
```

When several PRs form a dependency circuit (for example: CI substrate
repair -> stabilization verification -> governance audit), name the
circuit, verify each link's real blocker, and refuse to reorder it without
new evidence. Do not add an application-fix cycle to a frozen stabilization
PR unless fresh CI or runtime evidence identifies a real defect.

## PR state machine

Use only these states:

```text
UNKNOWN -> TRIAGED -> DIAGNOSED -> READY_FOR_REPAIR -> IN_PROGRESS
        -> VALIDATING -> EVIDENCE_READY -> MERGEABLE
```

Alternative terminal states: `BLOCKED` `SUPERSEDED` `ABANDONED`
`NEEDS_HUMAN_DECISION`. Never use vague states ("mostly done",
"should work", "probably mergeable"). Do not manufacture completion.

## Verification-only mode (frozen PRs)

When the objective is to verify a PR without modifying it — typically a
stabilization PR awaiting authoritative CI — follow the proven circuit in
[verification-circuit.md](verification-circuit.md): isolated worktree,
repo-native bootstrap, full local gate, boundary-specific test suites,
compatibility-contract checks, and hosted-state readout. All steps are
read-only with respect to the PR branch.

## Delegation

Prefer existing specialists over duplicating their work:

| Surface | Path | Role |
| --- | --- | --- |
| Cursor subagents | `.cursor/agents/` | Specialist review/implementation: quality gate, architecture, security, docs, resources, providers, release, ADR |
| Claude skills | `.claude/skills/` | Claude-facing skills; `run-rif-runtime` is the build/run/test driver |
| Generated skill | `.claude/skills/rif-runtime/SKILL.md` | Auto-generated and wrong (describes TypeScript); do not follow it over `src/` or `AGENTS.md` |

When validating application code under `src/` or `tests/`, delegate to the
`rif-quality-gate` specialist. When a request is read-only reconnaissance,
do not modify files.

## Boundaries

- Classify work by governance track: Track A (correctness/security,
  existing contracts preserved), Track B (contract, replay, schema,
  aggregate, identity changes — requires specification review), Track C
  (implementation of approved specifications). If uncertain, stop.
- If a change crosses identity, capability, evidence, replay, MCP, or
  provider-egress boundaries, inspect `spec/README.md` and open
  specification reviews before implementing a competing contract. Keep
  competing namespace or architecture migrations out of the stabilization
  path.
- The control plane uses `X-API-Key` / `RIF_CONTROL_PLANE_API_KEYS` and
  fails closed with no keys configured. Never weaken that boundary. Never
  promote model output or an external provider credential into a RIF
  authorization decision.
- Stop for human authorization before: destructive operations, security or
  authorization boundary changes, releases, merges where merge authority
  is not explicitly granted, and irreversible external actions.

## Anti-entropy

Reject: speculative refactoring, unrelated cleanup, unnecessary dependency
upgrades, broad rewrites, duplicate systemic fixes, weakening tests,
suppressing failures, unnecessary PR multiplication.

The change justification must form:

```text
PROBLEM -> ROOT CAUSE -> NECESSARY CHANGE -> VALIDATION
```

If that chain cannot be established, do not make the change.

## Reporting

```markdown
## Orchestration State

Objective:
Repository State:
Current Work Unit:
Root Cause:
Action:
Validation:
Evidence:
Remaining Blockers:
Next State:
Confidence:
```

Classify each factual claim as `EXECUTED`, `INFERRED`, or `UNVERIFIED`.

## Termination

Stop when the current objective reaches `MERGEABLE`, `BLOCKED`,
`SUPERSEDED`, `ABANDONED`, or `NEEDS_HUMAN_DECISION`, or when the
highest-value next action is to wait for human authorization. If the
justification chain cannot be established, terminate with
`NEEDS_HUMAN_DECISION` and record why.
