# RIF Runtime v1.0 Minimum CLI Specification

**Status:** Frozen design (Track B) — target CLI that demonstrates v1.0 contracts.  
**Depends on:** [`spec/events`](../spec/events/SPEC.md), [`spec/replay`](../spec/replay/SPEC.md), [`spec/governance/GOVERNANCE_AS_CODE.md`](../spec/governance/GOVERNANCE_AS_CODE.md).  
**Today:** [`src/rif_runtime/cli.py`](../src/rif_runtime/cli.py) implements the **0.3 MVP** surface (`serve`, `check`, `replay`, `msf-check`, `status`). This document defines the **v1.0 demo CLI**; MVP commands remain until an implementation slice migrates or aliases them.

## Assumptions

- No TUI/web UI framework — Typer + stdout/stderr only (optional ANSI on TTY; disable with `NO_COLOR` / `--no-color`).
- Human output is the default; `--json` forces machine-readable JSON on **stdout**.
- Diagnostics and `error:` lines go to **stderr**.
- Event log is append-only JSONL (`rif.runtime.event/v1`); evidence is content-addressed.
- Exit codes are stable for CI (see Exit codes below).

## Non-goals

- Replacing `rif serve` in this freeze (API server stays; not required to demo GaC/replay).
- Full agent orchestration UI.
- Interactive prompts in CI (all inputs flags/files/env).

---

## 1. Command specification

### Global options (all commands)

| Flag | Default | Meaning |
| --- | --- | --- |
| `--json` | off | Emit primary result as JSON on stdout |
| `--quiet` / `-q` | off | Suppress human prose; errors still on stderr |
| `--data-dir` | `data` | Root for `events/`, `evidence/`, packs cache |
| `--pack` | `policies/runtime.v1.yaml` | Governance pack path (GaC) |
| `--no-color` | off | Disable ANSI |
| `--help` | | Typer help |

Root: `rif` with `no_args_is_help=True`.

### Exit codes (CI contract)

| Code | Meaning |
| --- | --- |
| `0` | Success (verify matched; policy allow when not using deny-as-failure; replay/inspect ok) |
| `1` | Operational failure (I/O, missing file, invalid JSONL, schema error) |
| `2` | Usage / argument error |
| `3` | **Verify divergence** or integrity failure (`CHAIN_BREAK`, `HASH_MISMATCH`, …) |
| `4` | **Policy deny** (only when `--fail-on-deny` / CI policy check) |
| `5` | **Policy review** required (`--fail-on-review`) |

`rif run` without `--fail-on-deny` exits `0` on deny and puts decision in output (same spirit as today’s `rif check`) so scripts can branch on JSON; CI jobs that must gate use `--fail-on-deny`.

---

### `rif run`

Governed run of an intent: evaluate policy, append events, optionally record evidence refs. **Does not** require the HTTP server.

```text
rif run [OPTIONS] --intent <text>
rif run [OPTIONS] --intent-file <path>
```

| Option | Meaning |
| --- | --- |
| `--intent` / `--intent-file` | User intent (exactly one required) |
| `--actor` | Default `agent:cli` |
| `--action` | Capability action (default from pack/manifest hint, else required) |
| `--target` | Capability target |
| `--mode` | Operating mode (default `governed_execute`) |
| `--risk` | Risk score 0..1 (default `0`) |
| `--evidence KEY=present` | Mark evidence availability keys |
| `--dry-run` | Evaluate + explain; **do not** append events |
| `--fail-on-deny` | Exit `4` if decision is deny |
| `--fail-on-review` | Exit `5` if review |
| `--run-id` | Optional client-supplied `run_`+32 hex |

**Human stdout (abbrev):** run id, decision, reason_code, matched rule, event sequences written.  
**JSON:** `{ run_id, decision, reason_code, matched_rule_id, explanation_id, events_written[], dry_run }`.

Emits at least: `intent.received`, `mode.selected`, `governance.evaluated` (and deny/grant capability events as applicable). Full execution lifecycle is optional in the minimum demo if no executor is wired — `--execute` deferred until kernel integration.

---

### `rif replay`

Pure reconstruction of runtime state (no capability I/O). Aligns with replay SPEC **pure** mode.

```text
rif replay [OPTIONS] <run_id>
rif replay [OPTIONS] --events <path.jsonl>
```

| Option | Meaning |
| --- | --- |
| `--at <N>` | Snapshot after sequence N (default: last) |
| `--events` | Explicit JSONL path (else `data/events/<run_id>.jsonl`) |

**Human:** status, posture, denial_count, head_hash, state_digest.  
**JSON:** `ReplayReport` / snapshot subset (`rif.runtime.replay-report/v1`).

Exit `0` on success; `1` on decode/gap; does **not** use exit `3` (that is verify).

**Compatibility:** Legacy `rif replay [decisions.jsonl]` (file path, no run id) remains until migration; v1.0 prefers `run_id`. Disambiguate: if argument matches `run_[a-f0-9]{32}` treat as run id; if path exists treat as legacy file; else error.

---

### `rif verify`

Verify-only: hash chain, event ids, result hashes, evidence presence. Replay SPEC **verify** mode.

```text
rif verify [OPTIONS] <run_id>
```

| Option | Meaning |
| --- | --- |
| `--at <N>` | Verify prefix through N |
| `--evidence-dir` | Default `<data-dir>/evidence` |
| `--fail-fast` | Stop at first divergence (default true) |

**JSON:** full `ReplayReport` including `divergence` when `ok=false`.  
Exit `0` if ok; **`3`** on divergence/integrity failure; `1` on missing log.

---

### `rif inspect`

Time-travel / inspection for debugging (human-first).

```text
rif inspect run <run_id> [--at N]
rif inspect event <run_id> <sequence>
rif inspect digest <run_id> [--at N]
rif inspect diff <run_id> --from A --to B
```

| Subcommand | Output |
| --- | --- |
| `run` | Snapshot summary at N |
| `event` | Single envelope (redact secrets) |
| `digest` | `state_digest` + `head_hash` only (CI-friendly) |
| `diff` | Field-level diff between two sequences |

Exit `0` / `1` / `2` as usual.

---

### `rif policy`

Governance-as-code operations (no hidden state).

```text
rif policy validate [PACK]
rif policy check [OPTIONS]
rif policy test [OPTIONS]
rif policy explain [OPTIONS]
```

**`validate`:** JSON Schema + lint (catch-all deny present, priority bands). Exit `0`/`1`.

**`check`:** Evaluate `PolicyInput` from flags or `--input-file`.

```text
rif policy check --action http.request --target https://api.anthropic.com/v1/messages \
  --mode governed_execute --risk 0.2 --budget-requests 10
rif policy check --input-file case.json --fail-on-deny
```

**`test`:** Run golden cases under `--cases-dir` (default `tests/fixtures/policy/cases`). Exit `0` if all pass; `1` if any fail.

**JSON:** `PolicyExplanation` (`rif.runtime.policy-explanation/v1`) for check/explain; test summary `{ passed, failed, cases: [...] }`.

---

### `rif evidence`

Content-addressed evidence store helpers.

```text
rif evidence list [--run-id RUN]
rif evidence show <sha256>
rif evidence put <file>
rif evidence export <run_id> <bundle.zip|dir>
```

**list:** hashes referenced by a run’s events (or all under evidence dir).  
**show:** metadata + optional preview (size-capped).  
**put:** write immutable blob; refuse overwrite on digest mismatch.  
**export:** pack events JSONL + referenced blobs for offline verify.

Exit `0`/`1`/`2`. Missing hash → exit `1`.

---

## 2. Example sessions

### Human — allow path

```text
$ rif run --intent "fetch model docs" --action http.request \
    --target https://api.anthropic.com/v1/messages --risk 0.1
run_id   run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
decision allow
reason   NETWORK_HOST_ALLOWED
rule     allow_anthropic
events   1..5 written under data/events/run_aaa….jsonl
```

### JSON — CI policy gate

```text
$ rif policy check --input-file tests/fixtures/policy/cases/allow_anthropic_happy.json --json
{"schema_version":"rif.runtime.policy-explanation/v1","decision":"allow",...}
$ echo $?
0

$ rif policy check --input-file cases/deny_blocked_host.json --json --fail-on-deny
{"decision":"deny","reason_code":"DEFAULT_DENY",...}
$ echo $?
4
```

### Verify after tamper

```text
$ rif verify run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ok       true
events   12
head     e9e9…e9e9

$ rif verify run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
error: HASH_MISMATCH at sequence 4 event evt_…
$ echo $?
3
```

### Replay + inspect time-travel

```text
$ rif replay run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --at 5
status          authorized
posture         normal
state_digest    0303…0303
head_hash       7878…7878

$ rif inspect event run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 5
type     governance.evaluated
decision allow
...

$ rif inspect diff run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --from 4 --to 5
~ posture unchanged
+ last_decision: allow
```

### Evidence export for offline CI

```text
$ rif evidence export run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa /tmp/run_aaa.bundle
wrote  /tmp/run_aaa.bundle (events + 2 blobs)

$ rif verify run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --data-dir /tmp/unpacked
ok  true
```

---

## 3. Error handling

| Situation | stderr | exit |
| --- | --- | --- |
| Missing required flag | `error: …` + hint | 2 |
| Pack schema invalid | `error: policy pack invalid: …` | 1 |
| Events file missing | `error: events not found: …` | 1 |
| JSONL decode | `error: invalid JSONL at path:line: …` | 1 |
| Sequence gap on replay | `error: SEQUENCE_GAP at …` | 1 |
| Verify integrity fail | `error: <REASON_CODE> at sequence N …` | **3** |
| Evidence blob missing | `error: EVIDENCE_MISSING …` | 3 (verify) or 1 (show) |
| Deny with `--fail-on-deny` | human/JSON decision still emitted | **4** |
| Unexpected traceback | only for bugs; CI should fail | 1 |

Rules:

- Never print secrets (tokens) in human or JSON; show `grant_token_hash` only.
- `--json` failures: still print `error:` on stderr; typed reports (`ReplayReport`) preferred for verify/replay.
- Do not soft-wrap paths on stderr (non-rich echo for errors).

---

## 4. CI integration

### Recommended GitHub Actions job

```yaml
policy-gac:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install -e ".[dev]"
    - name: Validate policy pack
      run: rif policy validate policies/runtime.v1.yaml
    - name: Policy golden tests
      run: rif policy test --cases-dir tests/fixtures/policy/cases --json
    - name: Demo run + verify (fixture)
      run: |
        rif run --intent-file tests/fixtures/cli/intent_allow.txt \
          --action http.request --target https://api.anthropic.com/v1/messages \
          --data-dir "$RUNNER_TEMP/rif-data" --json | tee /tmp/run.json
        RUN_ID=$(python -c "import json;print(json.load(open('/tmp/run.json'))['run_id'])")
        rif verify "$RUN_ID" --data-dir "$RUNNER_TEMP/rif-data"
```

### Local targets (suggested)

```text
make policy          # rif policy validate && rif policy test
make verify-fixtures # rif verify over checked-in runs/
```

| Job | Must exit 0 |
| --- | --- |
| Pack validate + `policy test` | yes |
| `rif verify` on golden runs | yes (exit 3 fails the job) |
| `rif run --fail-on-deny` smoke | yes for allow fixtures |

Wire into `.github/workflows/ci.yml` or `quality.yml` once commands exist — do not soft-fail.

---

## 5. Recommended package structure

```text
src/rif_runtime/
  cli/
    __init__.py          # export app
    main.py              # typer.Typer root + global options callback
    _exit.py             # ExitCode enum + die()
    _output.py           # human vs json printers (no UI framework)
    run.py               # rif run
    replay_cmd.py        # rif replay (v1 pure)
    verify_cmd.py        # rif verify
    inspect_cmd.py       # rif inspect (+ subcommands)
    policy_cmd.py        # rif policy validate|check|test
    evidence_cmd.py      # rif evidence list|show|put|export
    legacy.py            # serve, check, status, msf-check, legacy replay path
  policy_eval/           # GaC evaluator (GOVERNANCE_AS_CODE)
  replay_engine/         # DeterministicReplayEngine (replay SPEC)
  events/                # envelope writer, canonical hash
  evidence_store/        # content-addressed blobs

tests/
  test_cli_v1_*.py
  fixtures/policy/
  fixtures/replay/
  fixtures/cli/

policies/
  runtime.v1.yaml

docs/
  cli-v1-spec.md         # this file
  cli-reference.md       # current implemented surface until cutover
```

**Entrypoint:** `pyproject.toml` → `rif = "rif_runtime.cli.main:app"` (migrate from `rif_runtime.cli:app`).

**Dependency rule:** CLI modules call engines; engines must not import Typer.

---

## Migration from 0.3 MVP CLI

| MVP | v1.0 |
| --- | --- |
| `rif check …` | `rif policy check …` or `rif run --dry-run` |
| `rif replay <file>` | Legacy; prefer `rif replay <run_id>` |
| `rif status` | `rif inspect run` / keep as alias |
| `rif serve` | Unchanged (retained; out of demo minimum) |
| `rif msf-check` | Keep under legacy |

**Implementation order:** engines first → `cli/` package → aliases → update `cli-reference.md` → CI job → remove legacy after one release.

---

## Risks

| Risk | Mitigation |
| --- | --- |
| Exit code confusion (deny vs verify) | Document `4` vs `3`; never overload |
| `rif replay` argv ambiguity | Strict `run_` pattern vs filesystem path |
| JSON + human mixed on stdout | `--json` exclusive; prose suppressed |
| CLI before engines | Implement engines first; avoid long-lived stubs |
