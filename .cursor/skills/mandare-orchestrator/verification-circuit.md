# Verification-only circuit for frozen PRs

Verify a PR's evidence without modifying its diff. Every step is read-only
with respect to the PR branch.

Verification executes PR-authored code by design (build hooks, tests), so
run the circuit only in a disposable environment (Cloud Agent VM or
container) holding no credentials beyond the read scopes the hosted-state
readout needs. Never execute shell scripts from the PR worktree on the
verifier host: worktree `scripts/` content is PR-controlled input, not
trusted tooling.

Prerequisites: `git`, `gh`, `grep`, Python 3.12+.

## 1. Isolated worktree

Never leave the current branch. Fetch and mount the PR tip read-only, and
pin the commit being verified:

```bash
git fetch origin <pr-branch>
git worktree add /tmp/pr-verify origin/<pr-branch>
SHA=$(git -C /tmp/pr-verify rev-parse HEAD)
```

All later evidence is bound to `$SHA`, not to the branch name.

## 2. Review execution-relevant changes, then bootstrap with trusted tooling

Before installing anything, review the PR's changes to files that will
execute during bootstrap or test collection:

```bash
git -C /tmp/pr-verify diff origin/main...HEAD -- \
  scripts/ pyproject.toml requirements/ requirements.txt \
  requirements-dev.txt conftest.py
```

Unexpected changes to bootstrap, build, or dependency files stop the
circuit with `NEEDS_HUMAN_DECISION` until a human reviews them.

Create the environment with inline trusted commands — the same locked
install the hosted merge-gate `verify` job uses — instead of running the
worktree's `scripts/cloud-agent-install.sh`. Cloud containers may lack
`ensurepip` (ADR-0027), so fall back to `virtualenv` driven by the system
interpreter:

```bash
cd /tmp/pr-verify
python3 -m venv .venv || { rm -rf .venv && \
  /usr/bin/python3 -m virtualenv .venv 2>/dev/null || { \
  /usr/bin/python3 -m pip install --user virtualenv && \
  /usr/bin/python3 -m virtualenv .venv; }; }
.venv/bin/python -m pip install --require-hashes -r requirements/dev.txt
.venv/bin/python -m pip install -e . --no-deps
```

## 3. Full local gate

Run exactly what the hosted merge-gate `verify` job runs
(`.github/workflows/merge-gate.yml`), so local green and hosted green
measure the same thing:

```bash
cd /tmp/pr-verify && source .venv/bin/activate
ruff check .
ruff format --check .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Optionally re-run pytest with `RIF_DATA_DIR=$(mktemp -d)` as an
*additional* isolation check; it is not a substitute for the hosted-exact
invocation. Record exact pass/fail counts. Local execution is evidence,
not hosted CI.

## 4. Boundary-specific suites

Run verbosely so individual invariants are named in the evidence:

```bash
pytest -v \
  tests/test_policy_store.py \
  tests/test_control_plane_auth.py \
  tests/test_audit_chain.py
```

These cover policy-store behaviour, the fail-closed control plane with no
keys configured, and tamper/deletion/reorder detection on the audit hash
chain. If the PR under verification adds its own boundary suites (for
example, a fail-closed policy suite), include those files from the
worktree's `tests/` as well.

## 5. Compatibility contract (RIF-6)

Distribution `mandare`, namespace `rif_runtime`, CLI `rif`, env vars
`RIF_*`, `rif.toml` preserved:

```bash
.venv/bin/pip list | grep -i mandare              # distribution name
python -c 'import rif_runtime'                     # namespace intact
RIF_DATA_DIR=$(mktemp -d) rif check "agent:verify" "http.request" \
  "https://api.anthropic.com/v1/messages"          # expect allow
RIF_DATA_DIR=$(mktemp -d) rif check "agent:verify" "http.request" \
  "https://blocked.example.com"                    # expect deny, posture elevated
grep -rhoE --include='*.py' 'RIF_[A-Z_]+' src/rif_runtime | sort -u
grep -rE --include='*.py' 'MANDARE_[A-Z_]+' src/ \
  && echo "FAIL: MANDARE_ env vars found" \
  || echo "pass: no MANDARE_ env vars"
ls rif.toml
```

## 6. Hosted-state readout, bound to the commit

Local green does not clear `[UNVERIFIED]` on hosted CI. Read the live
state for the exact commit verified locally, not for whatever the branch
points at now:

```bash
gh pr view <n> --json mergeable,mergeStateStatus,reviewDecision,headRefOid
gh run list --commit "$SHA" --limit 15 \
  --json databaseId,name,status,conclusion,headSha
gh run view <run-id>        # read the ANNOTATIONS section
```

Accept a run as evidence only if its `headSha` equals `$SHA`; if the PR's
`headRefOid` no longer equals `$SHA`, the branch moved and the local
verification must be repeated against the new tip.

Classify failures from evidence, not from timing or step counts.
Distinguish the `failure`, `skipped`, and `cancelled` conclusions, and
read each failed job's annotation text before diagnosing. Only an
annotation that explicitly names an infrastructure or account cause (for
example, "The job was not started because your account is locked due to a
billing issue") justifies an owner-actionable diagnosis; in that verified
case, retain `[UNVERIFIED]` for hosted verification and do not spend
repair cycles on workflow files. Absent such an annotation, treat the
failure as a candidate defect and read the job logs.

## 7. Leave the environment usable

Keep the worktree and venv in place so a human or follow-up agent can
continue from the verified state. Record the worktree path and `$SHA` in
the report.
