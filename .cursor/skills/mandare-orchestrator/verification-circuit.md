# Verification-only circuit for frozen PRs

Verify a PR's evidence without modifying its diff. Every step is read-only
with respect to the PR branch. Executed successfully against the RIF-6
stabilization PR (branch `claude/mandare-stabilization-lead-fgjri6`).

## 1. Isolated worktree

Never leave the current branch. Fetch and mount the PR tip read-only:

```bash
git fetch origin <pr-branch>
git worktree add /tmp/pr-verify origin/<pr-branch>
```

## 2. Bootstrap with the repo-native script

Cloud containers may lack `ensurepip`, so a bare `python3 -m venv` leaves a
broken skeleton (see ADR-0027). Use the repository's own bootstrap, which
falls back through stdlib venv, installed virtualenv, and system-pip
virtualenv, then installs the project and dev requirements:

```bash
bash /tmp/pr-verify/scripts/cloud-agent-install.sh
```

## 3. Full local gate

```bash
cd /tmp/pr-verify && source .venv/bin/activate
ruff check src tests
ruff format --check src tests
mypy src/rif_runtime --ignore-missing-imports
RIF_DATA_DIR=$(mktemp -d) pytest -q
```

Record exact pass/fail counts. This is local evidence only — it never
substitutes for a hosted run.

## 4. Boundary-specific suites

Run verbosely so individual invariants are named in the evidence:

```bash
RIF_DATA_DIR=$(mktemp -d) pytest -v \
  tests/test_policy_fail_closed.py \
  tests/test_control_plane_auth.py \
  tests/test_audit_chain.py
```

These cover: deny-by-default with no policy rules, fail-closed control
plane with no keys configured, and tamper/deletion/reorder detection on
the audit hash chain.

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
rg -o 'RIF_[A-Z_]+' src/rif_runtime --no-filename | sort -u
rg -c 'MANDARE_[A-Z_]+' src/                       # expect no matches
ls rif.toml
```

## 6. Hosted-state readout

Local green does not clear `[UNVERIFIED]` on hosted CI. Read the live
state and the actual failure cause:

```bash
gh pr view <n> --json mergeable,mergeStateStatus,reviewDecision
gh run list --branch <pr-branch> --limit 10 \
  --json databaseId,name,status,conclusion
gh run view <run-id>        # read the ANNOTATIONS section
```

Jobs completing in ~2 seconds with zero steps executed mean the job never
started. The annotation names the real cause (for example, an account
billing lock). That is owner-actionable infrastructure state; retain
`[UNVERIFIED]` for hosted verification and do not spend repair cycles on
workflow files.

## 7. Leave the environment usable

Keep the worktree and venv in place so a human or follow-up agent can
continue from the verified state. Record the worktree path in the report.
