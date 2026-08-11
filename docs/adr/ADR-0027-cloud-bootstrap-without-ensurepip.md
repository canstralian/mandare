# ADR-0027 — Cloud bootstrap without ensurepip / apt

## Status

**Proposed** (implements [#55](https://github.com/canstralian/rif-runtime/pull/55);
supersedes [#54](https://github.com/canstralian/rif-runtime/pull/54)).

After merge of #55: set to **Accepted**.

## Context

Cursor Cloud Agents for `rif-runtime` failed setup with `INSTALL_FAILED`.
Setup logs showed the user install command aborting at:

```text
python3 -m venv .venv
→ ensurepip is not available
→ [INSTALL] Exit code: 1
```

before any project `pip install`. The VM image lacked `ensurepip` /
`python3.12-venv`. Restricted egress blocked Ubuntu apt archives (the
recovery path suggested by Python’s error text). System `pip` and PyPI
remained available. Warm leftover `.venv` directories masked severity on
some pods.

`main`’s `.cursor/environment.json` used a bare `python3 -m venv && …`
one-liner. Documentation incorrectly claimed `python3.12-venv` was on the
image and apt-fixable.

## Decision criteria (priority order)

1. Works **today** on the current Cloud image and egress policy
2. **Repo-controlled** (no hard dependency on a platform change to ship)
3. **Deterministic** on cold boot
4. **Portable** across Cloud, CI, and developer workstations
5. **Minimal maintenance**
6. Performance (secondary)

## Confidence

| Claim | Level |
|-------|--------|
| Root cause | Very high (~98%) |
| Repository contribution | Very high |
| Platform contribution | High |
| Recommended fix (Strategy A) | Very high |
| Evidence completeness | High |

**Remaining uncertainty:** Whether future Cloud images will continue
shipping system `pip` without `ensurepip`. If both are removed, bootstrap
needs a further fallback (prebaked snapshot, `uv`, or get-pip).

## Explicit assumptions

| Assumption | Evidence | Confidence | If invalidated |
|------------|----------|------------|----------------|
| System `pip` on Cloud images | Observed `/usr/bin/python3 -m pip` | High | Need ensurepip bake, `uv`, or get-pip |
| PyPI allowlisted | Egress policy + HTTP 200 | High | Cold bootstrap fails; need snapshot/vendor |
| Ubuntu archives blocked | apt Release failures; not on allowlist | High | Apt may become optional, not required |
| JIT / `build: null` continues | This environment-info sample | Medium | Snapshots help latency; script remains fallback |
| Warm `.venv` can mask failure | `INSTALL_FAILED` + usable leftover env | High | Require cold validation |

## Decision

**Merge Strategy A immediately.**

1. `.cursor/environment.json` `install` runs
   `bash scripts/cloud-agent-install.sh` (sole supported entrypoint).
2. Script creates `.venv` via:
   - reuse if **structurally valid** (python + pip + activate; venv prefix OK), else
   - stdlib `venv` when `ensurepip` works, else
   - existing `virtualenv`, else
   - `/usr/bin/python3 -m pip install --user virtualenv` then create.
3. Install `pip install -e .`, `requirements.txt`, `requirements-dev.txt`
   (`pyproject.toml` currently has empty `dependencies`).
4. **Acceptance gate:** required runtime imports must succeed; write
   `.venv/.rif-bootstrap-ok` and a one-line summary for setup logs.

**Healthy `.venv` (two tiers):**

| Tier | Meaning |
|------|---------|
| Structural | Enough to activate and run pip (reuse vs recreate) |
| Accepted | Structural + runtime imports + marker (exit 0) |

### Platform recommendation (independent)

Pursue **Strategy B** as infrastructure hardening: bake `python3.12-venv`
and/or a prebuilt environment snapshot. Improves cold-start performance;
must not be the sole correctness path while JIT boots exist.

### Future evaluation

Revisit **Strategy D (`uv`)** only if the project standardizes on `uv`
for Python tooling generally.

## Alternatives considered

| Alternative | Verdict | Why rejected *for today’s fix* |
|-------------|---------|--------------------------------|
| **B — Image / snapshot bake** | Defer (complement) | Not repo-shippable; this run had `build: null` |
| **D — `uv` bootstrap** | Defer | Extra supply-chain/tooling cost for same root cause |
| **C — apt install `python3.12-venv`** | Rejected | Apt/Ubuntu archives unusable under current egress |
| **E — system-site / `--user` install, no venv** | Rejected | Breaks isolation; conflicts with `.venv` convention |

## Consequences

- Cloud correctness no longer depends on ensurepip or apt.
- Bootstrap depends on **system pip ∨ ensurepip** and **PyPI** (documented).
- Docs and CI should call the same script (or shared install steps) to
  avoid recipe drift.
- `#54` is superseded by `#55`.

## Success criteria

After merge, verification is objective when all of the following hold on a
**cold** Cloud Agent (image without ensurepip, no apt):

- [ ] `setupStatus` / setup log: `INSTALL_SUCCEEDED` (install exit 0)
- [ ] `import ensurepip` fails on the image (constraint still present)
- [ ] Ubuntu apt is not required for success
- [ ] `.venv/.rif-bootstrap-ok` exists
- [ ] Required imports succeed (`fastapi`, `rif_runtime`, …)
- [ ] Editable install present (`importlib.metadata.version("rif-runtime")`)
- [ ] Warm re-run logs structural reuse and still passes acceptance
- [ ] Corrupted (python-symlink-only) `.venv` is recreated, then accepted

## Operational risks

| Risk | Mitigation |
|------|------------|
| New ad-hoc install scripts | Only `scripts/cloud-agent-install.sh` is supported |
| Docs drift | Link the script; do not paste divergent snippets |
| CI diverges from Cloud | Reuse the same bootstrap / deps install |
| Warm pods hide regressions | Cold Cloud + no-ensurepip CI harness |

## Guardrails (layered defense before merge)

See “Automated guardrails” below — CI and policy checks that would have
blocked this regression on `main`.

## Principle

Repository bootstrap should depend only on capabilities that are
guaranteed (or observed and documented) by the execution environment.
Platform optimizations (image packages, snapshots) should improve
**performance**, not be the sole source of **correctness**.

## References

- Incident setup log: ensurepip failure, exit 1 (e.g. agent
  `bc-4e14e565-5ee4-4200-b150-d9ab0f0150f4`)
- PR #55 (implements), PR #54 (superseded)
- Blameless postmortem and FMEA in Cloud Agent investigation thread

---

## Automated guardrails

Layered defenses that catch repository regressions **before merge**.

| Guardrail | Failure detected | Complexity | False-positive risk | Maintenance | Impact |
|-----------|------------------|------------|---------------------|-------------|--------|
| **G1. `environment.json` policy check** — CI fails if `install` contains bare `python3 -m venv` without the script, or omits `cloud-agent-install.sh` / `bootstrap.sh` | Recurrence of this incident’s root config | Low (grep/jq) | Low if allowlisted script names | Low | **Critical** |
| **G2. No-ensurepip container job** — run `cloud-agent-install.sh` in `python:3.12-slim` (or image without `python3-venv`); assert exit 0 + imports + marker | ensurepip assumption; missing PyPI fallback; skip `requirements.txt` | Medium (Docker job) | Medium if slim lacks pip (install pip in Dockerfile) | Medium | **Critical** |
| **G3. Intentional negative** — in that container, bare `python3 -m venv` must fail | Proves constraint still real; documents why script exists | Low | Low | Low | High (documentation-as-code) |
| **G4. Script contract test** — assert script contains acceptance import gate and writes `.rif-bootstrap-ok` | Gate removed in a “simplification” PR | Low | Low | Low | High |
| **G5. Path-filter CI** — harness runs on changes to `environment.json`, install script, `requirements*.txt`, `pyproject.toml` | Silent bootstrap changes | Low | Low (may miss doc-only drift) | Low | High |
| **G6. Doc recipe lint** — fail if README/CLAUDE/SKILL contain `python3 -m venv` without pointing at the script (allowlist exceptions) | Divergent human/agent recipes | Medium | Medium (false hits on historical notes) | Medium | Medium |
| **G7. CODEOWNERS** on `.cursor/environment.json` + `scripts/cloud-agent-install.sh` | Unreviewed bootstrap edits | Low | Low | Low | Medium |
| **G8. Branch protection** — require G1+G2 checks on `main` | Merge without harness | Low (org setting) | Low | Low | **Critical** |

### Recommended layered defense (ship order)

1. **Merge gate (P0):** G1 + G2 + G8 — would have blocked `main`’s bare `venv` install.  
2. **Hardening (P1):** G3 + G4 + G5 — lock fallback and acceptance gate.  
3. **Drift control (P2):** G6 + G7 — docs and review policy.

Platform monitoring (setup_failed + ensurepip in logs) is complementary; it
does not replace pre-merge guardrails.
