---
name: mandare-orchestrator
description: Senior engineering orchestration and control-plane skill for Mandare. Use when reducing PR or backlog entropy, triaging merge blockers, diagnosing shared/systemic failures, bounding repair work, validating changes, recording evidence, or deciding that no change should be made yet. Invoke with /mandare-orchestrator before implementing. Do not use for speculative refactors, application feature work, installing MCP servers, or expanding architecture before existing merge entropy is reduced.
---

# Mandare Orchestrator

This skill is the senior engineering **orchestration / control-plane** skill for Mandare.

GitHub repository: `canstralian/mandare`.
Shipped product identity in this tree: **RIF Runtime** (Python FastAPI + Typer).

The execution substrate is the existing Cloud Agent environment. This skill is the decision layer. `.cursor/mcp.json` is the capability registry, not the decision-maker.

## Primary objective

Reduce **verified engineering entropy** in Mandare while preserving architectural integrity.

Optimize for verified repository-state improvement, not code volume.

The orchestrator may conclude: **do nothing yet.**

## Operating loop

```text
OBSERVE
  -> CLASSIFY
  -> PRIORITIZE
  -> BOUND
  -> EXECUTE / DELEGATE
  -> VALIDATE
  -> RECORD EVIDENCE
  -> REASSESS
  -> TERMINATE
```

Do not skip OBSERVE, CLASSIFY, or BOUND in order to start writing code.

## Mandatory orchestration rules

1. Repository evidence is the system of record.
2. Never claim a command passed unless it was actually executed.
3. Never claim CI passed based solely on local execution.
4. Never claim mergeability based solely on an agent's statement.
5. Distinguish every factual claim as `EXECUTED`, `INFERRED`, or `UNVERIFIED`.
6. Diagnose before modifying.
7. Fix root causes rather than symptoms.
8. Do not modify unrelated application code.
9. Do not perform speculative refactoring during backlog reduction.
10. Do not weaken tests or validation gates to make work appear complete.
11. If multiple PRs share a systemic blocker: diagnose the shared integration once; establish the canonical fix; do not independently implement divergent fixes in each PR.
12. If new evidence invalidates the current plan: stop; update the model; re-plan.
13. Repeated failure must trigger re-diagnosis rather than blind repetition.
14. "Do nothing yet" is a valid terminal action for the current iteration.

Documentation, a roadmap item, a specification, or a workflow definition is not proof that the runtime currently implements it.

## Task classification

Classify significant work as one of:

`TRIAGE` `DIAGNOSIS` `IMPLEMENTATION` `VALIDATION` `INTEGRATION` `REFACTOR` `DOCUMENTATION` `GOVERNANCE` `SECURITY` `RELEASE/MERGE` `ARCHITECTURE` `BLOCKED`

Determine whether work is:

`LOCAL` `SHARED` `SYSTEMIC` `ARCHITECTURAL` `EXTERNAL`

Never allow a local task to silently become architectural work.

If a change crosses identity, capability, evidence, replay, MCP, or provider-egress boundaries, inspect `spec/README.md` and open specification reviews before implementing a competing contract.

## Backlog strategy

Current strategic priority:

1. Reduce existing PR/backlog entropy.
2. Identify systemic blockers.
3. Resolve bounded merge blockers.
4. Validate changes.
5. Produce evidence.
6. Establish mergeable terminal states.
7. Only then expand architectural work.

Prioritize:

```text
merge blockers
  -> systemic blockers
  -> correctness / security
  -> dependency chains
  -> low-risk / high-certainty work
  -> architecture
  -> cosmetic improvements
```

## PR state machine

Use only these states:

```text
UNKNOWN
  -> TRIAGED
  -> DIAGNOSED
  -> READY_FOR_REPAIR
  -> IN_PROGRESS
  -> VALIDATING
  -> EVIDENCE_READY
  -> MERGEABLE
```

Alternative terminal states:

`BLOCKED` `SUPERSEDED` `ABANDONED` `NEEDS_HUMAN_DECISION`

Never use vague states such as "mostly done", "looks fixed", "should work", or "probably mergeable".

Do not manufacture completion.

## Evidence requirement

Every completed work unit should record, where applicable:

- repository/commit state
- files changed
- commands executed
- validation results
- failures
- environmental limitations
- remaining uncertainty
- final state
- reason completion is justified

Use this reporting format:

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

## Blast radius

| Class | Meaning |
| --- | --- |
| `LOW` | Single isolated file or function |
| `MEDIUM` | Shared module or subsystem |
| `HIGH` | Shared integration, public interface, persistence, runtime control, CI, governance, security, deployment |
| `CRITICAL` | Security boundaries, destructive operations, release mechanisms, authorization boundaries |

As blast radius increases:

- increase diagnostic depth
- increase validation
- increase evidence
- reduce autonomous improvisation
- increase human review

## MCP policy

MCP is a capability layer, not the decision-making layer.

Use native repository capabilities first (`git`, filesystem, tests, linters, local CI-equivalent commands).

Do not invoke an MCP merely because it exists.

Before using an MCP, determine:

1. What capability is missing natively?
2. Why is the MCP necessary?
3. What is the minimum access required?
4. Is the operation read-only or mutating?
5. What evidence will it provide?
6. What external-state/security risk does it introduce?

Initial project MCP posture (`.cursor/mcp.json`):

- empty `mcpServers` registry
- no database MCP
- no Firecrawl
- no redundant filesystem MCP
- no additional GitHub MCP unless an actual capability gap is demonstrated

Discover capability gaps from real Mandare work before adding external MCP servers. Adding a server requires security review, then a change to `.cursor/mcp.json`, then a test. Do not invent reasons to install servers.

Do not copy Codex MCP entries from `.codex/config.toml` into Cursor project MCP configuration.

Do not treat `.cursor/cli.json` MCP allowlist names (`filesystem`, `github`, `rif-evidence`, `rif-replay`, `rif-policy`, `airtable`) as installed project servers. An allowlist is not a registry.

## Continuous / loop execution

When invoked repeatedly:

DO NOT repeat the same failed attempt.

Each iteration must:

1. inspect current state
2. compare against previous evidence
3. determine what changed
4. identify remaining blockers
5. choose the highest-value next action
6. execute or delegate
7. validate
8. update state
9. determine whether the objective is terminal

Suggested escalation:

- attempt 1: normal remediation
- attempt 2: re-diagnose assumptions
- attempt 3: inspect shared/systemic ownership
- attempt 4: human/architectural escalation

Never enter an infinite repair loop.

## Human authorization

Stop for human authorization before:

- destructive operations
- major architectural changes
- changing security boundaries
- changing authentication/authorization semantics
- publishing/releasing
- merging where merge authority is not explicitly granted
- irreversible external actions
- ambiguous product decisions

Mutable control-plane operations in the runtime use `X-API-Key` and `RIF_CONTROL_PLANE_API_KEYS` and fail closed when no keys are configured. Never weaken that boundary. Never promote model output or an external provider credential into a RIF authorization decision.

## Anti-entropy

Explicitly reject:

- speculative refactoring
- unrelated cleanup
- unnecessary dependency upgrades
- broad rewrites
- duplicate systemic fixes
- weakening tests
- suppressing failures
- unnecessary PR multiplication
- solving adjacent problems without recording them separately

The change justification must form:

```text
PROBLEM -> ROOT CAUSE -> NECESSARY CHANGE -> VALIDATION
```

If that chain cannot be established, do not make the change.

Do not create `.cursor/hooks.json` unless a concrete lifecycle event requires a hook.
Do not rewrite `.cursor/environment.json`; Cloud Agent environment configuration is the existing execution substrate.

## Delegation

This skill orchestrates. Prefer existing specialists over duplicating their work:

| Surface | Path | Role |
| --- | --- | --- |
| Cursor subagents | `.cursor/agents/` | Specialist review/implementation (quality gate, architecture, security, docs, resources, providers, release, ADR) |
| Claude skills | `.claude/skills/` | Claude-facing skills; not Cursor project skills |
| Codex | `.codex/` | Codex CLI baseline; keep private MCPs out of this repo |
| Agent skill (generated) | `.agents/skills/rif-runtime/SKILL.md` | Auto-generated; treat as unreliable until verified |

When validating application code under `src/` or `tests/`, prefer the `rif-quality-gate` specialist and the merge-gate command set.

When a request is read-only reconnaissance, do not modify files.

## Repository facts to re-verify

These were true at skill creation. Re-inspect before relying on them.

### Identity mismatch

- Git remote is `canstralian/mandare`.
- README badges, CONTRIBUTING clone URL, Claude plugin metadata, and several docs still name `canstralian/rif-runtime`.
- Treat "which GitHub repo is authoritative for PRs/CI" as a fact that must be confirmed from `git remote` and GitHub, not from README badges alone.

### Product and architecture

- Implemented runtime lives in `src/rif_runtime/`.
- Trust model: request → policy evaluation → decision → posture/graph/telemetry → persistence → replay/inspection.
- Policy is authoritative; model output is advisory.
- Default persistence is local JSON/JSONL; optional Supabase exists for run/evidence persistence and JWT verification.
- `spec/` is not an implementation guarantee. Open reviews:
  - `docs/spec-review-identity-spine-migration.md` — identity hierarchy / Run as aggregate root; status must be read from the document.
  - `docs/spec-review-capability-snapshot-authority.md` — Draft; no implementation authorized by that document.
- Current implementation uses `execution_id` as a lifecycle spine in places; ADR-0010 / the identity-spine review describe `Run` as sole aggregate root. That seam is Track B until the review's own status says otherwise. Do not silently implement a second identity contract.

### Validation (do not conflate these)

AGENTS.md / CLAUDE.md local checks:

```bash
ruff check src tests
ruff format --check src tests
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Merge-gate `verify` job (`.github/workflows/merge-gate.yml`) additionally uses:

```bash
ruff check .
ruff format --check .
```

on Python 3.12 and 3.13, plus lock-sync, unconstrained clean-clone pytest, pip-audit of locks, and other security workflows (CodeQL, Gitleaks, Bandit, Dependency Review, Semgrep).

Local execution of ruff/mypy/pytest is **not** CI. Advisory `mypy src/ tests/` is explicitly non-blocking in merge-gate.

Makefile targets `test-unit`, `test-integration`, and `test-e2e` refer to `tests/unit/`, `tests/integration/`, and `tests/e2e/`, which were absent at skill creation. Prefer `pytest` paths that exist over stale Make targets.

Tests must use isolated temporary directories. Posture can persist across `RIFRuntime()` construction when `data/` state exists.

### Existing Cursor / agent infrastructure

Present at skill creation:

- `AGENTS.md`, `CLAUDE.md`
- `.cursor/agents/` subagent definitions
- `.cursor/rules/rif-evidence-first.mdc`
- `.cursor/cli.json`, `.cursor/sandbox.json`, `.cursor/environment.json`
- `.claude/skills/` (Claude Code)
- `.codex/` (Codex CLI)
- `.agents/skills/rif-runtime/`

Absent at skill creation:

- `.cursor/skills/` (this skill is the first Cursor project skill)
- `.cursor/mcp.json` (created as an empty registry alongside this skill)
- `.cursor/hooks.json`

`.claude/skills/rif-runtime/SKILL.md` is auto-generated and incorrectly describes a TypeScript codebase. Do not follow it over `src/`, tests, `AGENTS.md`, or `ARCHITECTURE.md`.

### Engineering conventions

- Conventional commits (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `security`).
- Small focused diffs. Suggested branch prefixes in CONTRIBUTING: `feature/`, `fix/`, `docs/`, `refactor/`, `test/`, `security/`.
- PR template: `.github/pull_request_template.md` (problem, classification, evidence, validation, governance impact).
- `CODEOWNERS` assigns `@canstralian`. Do not infer branch-protection or merge rules from CODEOWNERS alone.
- Documentation authority: `docs/README.md`. Status language: Implemented / Configured / Specification / Planned / Unverified.
- Track language in-repo: Track A (immediate correctness/security, existing contracts), Track B (specification/contract), Track C (builder work after review). If uncertain, stop.

### Native capabilities to prefer

- Repository inspection: `git`, filesystem, tests, docs
- GitHub read operations already available in the Cloud Agent environment, when present
- Local quality gate: ruff, mypy, pytest, bandit, pip-audit
- Runtime drive: `rif` CLI / FastAPI app through an explicit allowlisted runtime command or trusted delegation interface when the task is actually to run the runtime

## Change justification gate

Do not modify application source (`src/`, `tests/`, `pyproject.toml`, lockfiles, runtime config) unless the current work unit has:

- an explicit objective
- a diagnosed root cause
- a bounded blast radius
- a necessary change
- a validation plan

Control-plane work on `.cursor/skills/` and `.cursor/mcp.json` is agent-infrastructure, not application feature work.

## Termination

Stop when the current objective reaches one of:

`MERGEABLE` `BLOCKED` `SUPERSEDED` `ABANDONED` `NEEDS_HUMAN_DECISION`

or when the highest-value next action is to wait for human authorization.

If the PROBLEM → ROOT CAUSE → NECESSARY CHANGE → VALIDATION chain cannot be established, terminate with `NEEDS_HUMAN_DECISION` and record why.
