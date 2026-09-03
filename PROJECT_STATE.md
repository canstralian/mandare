# PROJECT_STATE.md

Reconstructed by autonomous reconciliation, 2026-09-03. Supersedes prior conversational
claims. Every line below is either `[VERIFIED]` against the live repository/GitHub state
during this pass, or explicitly marked `[UNVERIFIED]`/`[BLOCKED]`.

## Current architecture

- Distribution/package name on `main` (7c132a7): **still `rif-runtime`** in `pyproject.toml`.
  `[VERIFIED]` — the rename has not landed on `main`.
- Policy engine on `main`: **still contains the `default.allow` fallthrough**
  (`src/rif_runtime/policy.py:137,159`, `matched_rule="default.allow"`). `[VERIFIED]` —
  RIF-5 fail-closed behavior has not landed on `main`.
- Internal identifiers (`rif_runtime` package, `rif` CLI, `RIF_*` env vars) are unchanged.
  `[VERIFIED]`.

## Completed work

- None of the rename or fail-closed work is merged to `main`. `[VERIFIED]`.

## Active work — canonical stabilization boundary

- **#149** (rename `rif-runtime` → `mandare`, docs/tooling only) — **closed, not merged**
  (`merged: false`). `[VERIFIED]` via `pull_request_read`.
- **#170** (`fix(policy): fail closed when no rule applies`, RIF-5/#40) — **closed, not
  merged** (`merged: false`). `[VERIFIED]`.
- **#173** (`stabilization: verified baseline for RIF-6 (#149) and RIF-5 (#170)`) is the
  **sole remaining canonical vehicle** for both changes. #149 and #170 were superseded and
  closed in favor of it (both closed within 2 seconds of each other, 2026-09-01T23:49Z,
  same actor as #173's most recent updates). `[VERIFIED]`.
  - `state: open`, `draft: false`, `mergeable_state: blocked`. `[VERIFIED]`.
  - Combined status on head SHA `f994495`: only two contexts report —
    `Vercel – rif-runtime: failure` ("Deployment has failed" / account-blocked, per PR body)
    and `CodeRabbit: success`. **No merge-gate / CI workflow run appears in the combined
    status at all.** `[VERIFIED]` — corroborates the PR body's claim that GitHub-hosted
    runners are not being allocated for this repository.
  - Local validation evidence (tests/lint/type/security/build) quoted in the PR body
    (351 passed, ruff/mypy/bandit clean, wheel installs cleanly) is `[UNVERIFIED]` by this
    session — it was produced in a different environment and this session did not
    re-run it against #173's branch (out of scope for read-only reconciliation; the
    branch was not checked out here).
  - PR body explicitly flags an unresolved conflict: another branch,
    `claude/mandare-rename-sweep-psgyr2` (not currently open as a PR in the list scanned),
    reportedly renames `src/rif_runtime` → `src/mandare` and `RIFRuntime` →
    `MandareRuntime`, which is architecturally incompatible with #173's decision to
    preserve the `rif_runtime` package/`rif` CLI/`RIF_*` identity. This is a genuine
    human architectural decision, not inferable safely.

- **#171** (governed GitHub MCP read-only gateway) and **#172** (Skill Runtime /
  `execute_capability()` delegation) remain **open, `draft`/non-draft as listed, both
  `mergeable_state: blocked`**, and both are explicitly deferred pending the stabilization
  boundary per prior architectural decision. `[VERIFIED]` (still open, unmerged, no new
  action taken — deferral preserved). Not reopened.

## Deferred / lower-priority open PRs (not touched)

Large backlog of `draft: true` `agent/code-review-debugging-*` and `agent/phase-6-*` PRs
(#89–#138 range) predate the current stabilization boundary and target a different base
history. Left untouched — reopening/triaging this backlog is out of scope for the
stabilization objective and would be entropy-increasing without an owner decision on
which are still relevant.

## Blocked work (external, owner-only)

1. **GitHub Actions runner allocation failure.** Every GitHub-hosted-runner job on #149,
   #170, and #173 fails within 1–3 seconds with no runner assigned (per #173 PR body,
   corroborated here by the combined-status check showing zero CI contexts). Remedy is
   the repository/org Actions spending limit and Actions policy — owner-only, not
   resolvable by this agent. `[BLOCKED]`.
2. **Vercel account block.** The `Vercel – rif-runtime` context fails with "Deployment has
   failed"; Vercel separately reported "Account is blocked" against
   `dejagersa-1111s-projects`/`team_0aV9dnO3IbZA7SGgL9y1rPIG`. Account-level, owner-only.
   `[BLOCKED]`.
3. **#173 merge itself.** `mergeable_state: blocked` with no CI signal available means the
   PR cannot be safely merged by mechanical inspection alone, and this agent's toolset has
   no PR-merge capability regardless. Requires the repository owner to merge (or force an
   admin merge past the broken required checks) once satisfied with the evidence.

## Human decisions required

1. **Rename-boundary conflict**: choose between #173's identity model (rename only the
   distribution name; keep `rif_runtime`/`rif`/`RIF_*`) and
   `claude/mandare-rename-sweep-psgyr2`'s deeper rename (`src/mandare`, `MandareRuntime`).
   These are mutually exclusive. No safe inference exists; this is an architecture/identity
   decision reserved for Stephen.
2. **Runner allocation and Vercel account block** — both require dashboard/billing access
   this agent does not have.
3. **Merging #173** once the above are resolved (or once the owner decides to merge despite
   absent CI, relying on the local evidence already presented in the PR body).

## Next executable action once human gates clear

- If the rename-boundary decision favors #173: rebase/land #173 as-is; then re-run the
  full validation suite against `main` post-merge to re-verify the "351 passed / clean
  lint/type/security" claims in a fresh environment (do not carry them forward as
  ground truth). Then reconsider #171/#172 for un-deferral.
- If the rename-boundary decision favors the deeper rename branch instead: #173 must be
  re-derived on top of that identity model rather than merged as-is.
