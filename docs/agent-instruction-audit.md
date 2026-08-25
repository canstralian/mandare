# Agent Instruction Audit

**Status:** Implementation-backed audit record. **Date:** 2026-08-23. **Baseline:** `282c093`.

This records an audit of the AI-agent instruction files in this repository against the code and tests they describe. Findings are stated as *instruction claimed X / implementation shows Y*, with anchors so each one can be re-checked when the code moves.

This document is a review finding, not a governance ratification. It does not authorize a merge or establish policy.

## Scope

Instruction sources inventoried:

| Source | Kind | Authority |
|---|---|---|
| `AGENTS.md` | Cross-tool baseline | Tier 3 (see `AGENTS.md` § Instruction authority) |
| `CLAUDE.md` | Cross-tool baseline | Tier 3, peer of `AGENTS.md` |
| `docs/README.md`, `spec/README.md` | Documentation / contract authority | Tier 4 |
| `.codex/AGENTS.md`, `.codex/config.toml`, `.codex/agents/*.toml` | Codex CLI baseline and subagents | Tier 5, tool-scoped |
| `.cursor/rules/rif-evidence-first.mdc` | Cursor always-on rule | Tier 5, tool-scoped |
| `.cursor/agents/*.md` | Cursor subagents (12 files) | Tier 5, tool-scoped |
| `.cursor/cli.json`, `sandbox.json`, `environment.json` | Cursor permission/network config | Tier 5, tool-scoped |
| `.claude/skills/*/skill.md` | Claude skills (10 skills) | Tier 5, tool-scoped |
| `.claude/homunculus/instincts/`, `.claude/identity.json`, `.agents/skills/` | Tool-generated hints | Tier 6, not authoritative |

Before this audit no file declared precedence among these. `AGENTS.md` § Instruction authority now does.

## Findings

### F1 — Policy wildcard rules described as inert (blocking, fixed)

`.cursor/agents/rif-quality-gate.md` instructed reviewers that "PolicyStore rule matching is exact-match only" and that wildcard rules "(e.g. seeded `deny_unknown_by_default`) are intentionally inert — flag any change that assumes wildcards are enforced."

Implementation contradicts this. `PolicyEngine.evaluate` (`src/rif_runtime/policy.py:75`) runs selective rules most-specific-first via `ordered_rules` (`policy.py:54`), then environment constraints, then catch-alls via `catch_all_rules` (`policy.py:69`). The shipped `deny_unknown_by_default` catch-all in `data/policies.json` is enforced: `tests/test_policy_store.py:105` asserts `matched_rule == "policy.deny_unknown_by_default"`, and `:205` asserts a catch-all allow does not disable the host allowlist.

With the shipped `data/policies.json` ruleset the effective fallback is **deny**. The qualifier matters: `PolicyEngine.evaluate` still ends in `default.allow` (`policy.py:159`) when no catch-all is configured, so deny-by-default is a property of the shipped ruleset rather than of the engine, and removing the catch-all restores allow-by-default silently. An agent following the stale text would have mis-reviewed policy changes in the direction of weakening deny-by-default. Fixed in `.cursor/agents/rif-quality-gate.md`; restated as Code Review Rule 2 in `AGENTS.md`.

### F2 — Test isolation described backwards (blocking, fixed)

The same file stated tests "instantiate it directly against real `data/` files". `tests/conftest.py:16` sets `RIF_DATA_DIR` to a throwaway temp directory at import time, specifically because restored posture would otherwise let one test's escalation decide the posture every later `RIFRuntime()` starts in. `AGENTS.md` and `CLAUDE.md` already said the opposite of the skill. Fixed.

### F3 — "No database or external service" (fixed)

The same file described the runtime as having no external service. `src/rif_runtime/integrations/supabase.py` exists and is used by `POST /v1/runs` for JWT identity; `AGENTS.md` already carried an explicit instruction not to describe the project this way. Fixed.

### F4 — Validation command drift (fixed)

Four different command sets were in circulation. The merge gate's `verify` job (`.github/workflows/merge-gate.yml`) runs `ruff check .` → `ruff format --check .` → `mypy src/rif_runtime --ignore-missing-imports` → `pytest -q`. `AGENTS.md`, `CLAUDE.md`, and `CONTRIBUTING.md` listed `ruff check src tests`, which lints a narrower tree and can pass while the gate fails; the quality-gate skill listed a fourth ordering. `AGENTS.md`, `CLAUDE.md`, `.cursor/agents/rif-quality-gate.md`, and `.claude/skills/run-rif-runtime/skill.md` now carry the gate's own order and scope, and note that `typecheck-tests` is advisory. `CONTRIBUTING.md` is left as-is: it describes useful local checks for humans, not the gate. The Cursor-facing twin `.claude/skills/run-rif-runtime/SKILL.md` was outside this inventory (see Open items).

### F5 — Phantom "Runtime Constitution" (fixed)

Four instruction files placed a "Runtime Constitution" at the top of an authority ladder. No such document exists anywhere in the repository. The real ladder is `docs/README.md` § Source-of-truth hierarchy, with `spec/README.md` for cross-domain contracts.

Fixed in `.cursor/agents/documentation-engineer.md`, `.claude/skills/documentation-engine/skill.md`, `.claude/skills/run-rif-runtime/skill.md`, and `.claude/skills/constitution-guardian/skill.md`, which now states plainly that the name is shorthand for the invariants it lists. The skill directory name is unchanged because `.claude-plugin/` manifests reference it.

### F6 — Aspirational pipeline stated as a required sequence (fixed)

`.claude/skills/governance-review/skill.md` required every execution to follow `Intent → Planner → Capability Resolution → Policy Evaluation → Execution → Evidence → Replay → Receipts`. Neither *Planner* nor *Receipts* appears anywhere in `src/` or `tests/`. The skill also asserted immutable evidence and deterministic capabilities as properties, and enumerated effect types (READ/WRITE/SNAPSHOT/...) that `CapabilityRecord` does not carry.

This is the failure mode `CLAUDE.md` names directly: specification described as shipped behaviour. The skill now separates the implemented sequence from the unimplemented stages and marks effect classification as design-tier.

### F7 — Governance boundary is the caller, not the kernel (open, documented)

`ExecutionKernel.execute` (`src/rif_runtime/execution/kernel.py:20`) resolves a capability and runs it with no policy evaluation, under the docstring "Governed execution entry point". The governed path is `RIFRuntime.execute_capability` (`src/rif_runtime/runtime.py:179`): evaluate → deny-with-evidence → admit → execute → evidence, covered by `tests/capabilities/test_governed_execution.py`.

So the invariant "no execution path may bypass policy evaluation" is caller-enforced. `ExecutionKernel` is exported from `execution/__init__.py`, and `tests/execution/test_kernel.py` constructs it and executes without policy — legitimately, as a unit test, but it demonstrates that nothing structural prevents an ungoverned production caller.

**This finding is documented, not fixed.** Closing it structurally (moving evaluation into the kernel, or making `Capability.execute` unreachable without a decision) changes an architectural contract and belongs in a specification review under `spec/README.md`, not in an instruction-cleanup change. Until then it is a review rule: `AGENTS.md` Code Review Rule 1, and blocking findings in the governance-review and constitution-guardian skills.

### F8 — Capability execution has no HTTP or CLI surface (documented)

`execute_capability` is reachable from the Python API only. No route in `src/rif_runtime/api.py` and no command in `src/rif_runtime/cli.py` exposes it. Recorded so that no document claims otherwise; no change is implied.

### F9 — Web access: capability vs. policy (clarified)

`.cursor/rules/rif-evidence-first.mdc` (`alwaysApply: true`) forbids open-ended web search for implementation work. `.codex/config.toml` sets `web_search = "live"` and enables the Exa MCP server, and `.cursor/cli.json` / `sandbox.json` allow a list of `WebFetch` hosts.

These are not strictly contradictory — one grants capability, the other constrains use — but nothing said so. `AGENTS.md` § Evidence-first rule now states that availability is not permission, and that external material must be cited with a reason in-repo evidence was insufficient.

### F10 — Generated hint files carry stale inferences (partly fixed)

`.claude/identity.json` listed `domains: ["typescript"]` for a Python-only codebase; corrected to `python`. `.claude/homunculus/instincts/inherited/rif-runtime-instincts.yaml` derives commit-style rules from a stated sample of **one commit** (`confidence: 0.85`, "1 commits analyzed"). Left in place — it is a generated artefact and rewriting it by hand would misrepresent its provenance. Instead, `AGENTS.md` places these files at the bottom of the authority ladder as non-authoritative hints, which is the correct fix for a low-evidence generated input.

## Open items

- **Dual `run-rif-runtime` skill files.** This directory carries both Claude-plugin `skill.md` (audited above) and Cursor-facing `SKILL.md`. The audit inventory matched `*/skill.md` only, so `SKILL.md` was not reconciled: it still quotes a stale "147 tests pass" figure and documents a direct `PolicyEngine` + `ExecutionKernel` demo path (the intentional driver in `drive_capability_layer.py`) without pointing at `RIFRuntime.execute_capability` as the production governed entry. Treat as the same class of drift as F4/F7; out of scope for the tip leftovers fixed alongside this note.

## Not changed

- **Workflows, branch protection, rulesets, CODEOWNERS** — outside an instruction-cleanup change and a human decision.
- **Any security control** — no guard, key requirement, or default was relaxed. F1's correction *strengthens* the reviewer's model of the default policy.
- **`spec/` contracts** — F7 is the one finding that would require a contract change; it is recorded here for review rather than implemented.
- **`CONTRIBUTING.md`** — human-facing local checks, deliberately not rewritten into the CI gate.
- **`.cursor/agents/provider-engineer.md`** — still lists "emit receipts" as a provider rule; same Receipts contradiction class as F6, outside the files this tip touches.

## Re-verification

Every anchor above was checked against the working tree at the stated baseline, with the full suite passing (344 tests). When these files move, re-run:

```bash
ruff check .
ruff format --check .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

and re-read the anchors in `policy.py`, `runtime.py`, `execution/kernel.py`, and `tests/conftest.py`. An instruction whose anchor no longer says what the instruction says is stale by definition.
