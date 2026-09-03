# Testing Strategy

Testing in RIF is primarily about proving governance boundaries, persistence behaviour, and compatibility. The current suite is the source of truth for what is actually tested.

## Test layers

The repository uses pytest-based tests across policy, runtime, API, persistence, replay, security, MCP, and integration concerns. Test names and locations may evolve; do not rely on a static directory diagram as an inventory.

Start with:

```bash
pytest -q
```

## Local validation

The main validation path is:

```bash
ruff check src tests
ruff format --check src tests
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

Security/dependency checks include:

```bash
bandit -r src/ -ll
pip-audit --requirement requirements/runtime.txt --disable-pip
pip-audit --requirement requirements/dev.txt --disable-pip
```

Additional repository workflows run CodeQL, Gitleaks, Dependency Review, lock synchronisation, and the unconstrained clean-clone test.

## What to test when changing governance

A governance change should normally cover:

- allow/deny behaviour for the affected policy condition;
- posture transition effects;
- persisted decision/posture state;
- replay/recovery behaviour where state changes;
- API authentication when a control-plane boundary changes;
- redaction when sensitive data handling changes;
- MCP/capability boundaries when integrations change.

The test should demonstrate the security property, not merely the current implementation sequence.

## Persistence isolation

Tests that instantiate `RIFRuntime()` should use isolated data directories. The repository's test configuration is designed to avoid contaminating the working `data/` directory.

For ad hoc experiments:

```bash
export RIF_DATA_DIR="$(mktemp -d)"
```

## Replay tests

Replay is a reconstruction mechanism. A replay test should specify what is expected to be reconstructed — for example posture or graph state — rather than claiming that replay reproduces an external side effect.

## Security tests

Security-sensitive tests should cover both positive and negative paths. Examples include:

- missing/invalid control-plane credentials are rejected;
- secret-bearing fields are redacted;
- policy denial cannot be bypassed by changing an unrelated field;
- persisted state is restored as documented;
- audit hash-chain primitives reject altered records;
- governed MCP paths preserve the intended authority boundary.

## Coverage and performance

The repository does not currently enforce a universal coverage percentage or a maintained policy-latency SLO in the documentation. Do not introduce a numerical target here unless it is backed by an executable CI gate or maintained benchmark.

Performance work should provide a reproducible benchmark, workload, environment, and comparison rather than a single unsupported latency claim.

## CI evidence

A workflow file proves that a check is configured. It does not prove that a particular commit passed.

When reporting validation status, record the exact commit and workflow/run result. Avoid statements such as "all security checks pass" without current run evidence.

## Adding a regression test

Prefer a small test with a clear contract:

```text
Given: a specific policy/runtime state
When:  a defined request or state transition occurs
Then: the authoritative decision/state is exactly the expected result
And:  relevant persistence/replay/security properties remain intact
```

If the desired behaviour is not yet specified, resolve the contract first rather than encoding an assumption in a test.
