# Contributing to RIF Runtime

RIF is intentionally a small project with a sharp boundary: intelligent systems may propose actions, but governance decides what the runtime will accept. Contributions are welcome when they make that boundary clearer, safer, easier to test, or easier to use.

## Before you start

Read [`README.md`](README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`SECURITY.md`](SECURITY.md), and [`docs/README.md`](docs/README.md).

For cross-domain contract changes, check `spec/README.md` for open specification reviews before implementing a competing contract.

## Local setup

```bash
git clone https://github.com/canstralian/rif-runtime.git
cd rif-runtime
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

To reproduce the locked CI dependency environment:

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pip install -e . --no-deps
```

## Make a focused change

Prefer a small branch and a small diff. Useful branch prefixes include `feature/`, `fix/`, `docs/`, `refactor/`, `test/`, and `security/`.

For behavioural changes, consider authority, persistence/replay, security, compatibility, migration/rollback, and documentation impact.

## Validation

Useful local checks are:

```bash
ruff check src tests
ruff format --check src tests
mypy src/rif_runtime --ignore-missing-imports
pytest -q
pip-audit --requirement requirements/runtime.txt --disable-pip
pip-audit --requirement requirements/dev.txt --disable-pip
```

For dependency changes, regenerate the locks rather than editing them manually:

```bash
make lock
```

The repository merge gate also checks lock synchronisation and runs an unconstrained clean-clone test in addition to the locked validation path.

## Tests are part of the design

When you change a security or governance property, add a regression test that demonstrates the property directly. Prefer behavioural tests over assertions tied to incidental implementation details.

Useful examples include denial under a stated policy condition, control-plane authentication failures, posture persistence/recovery, replay reconstruction, secret redaction, and capability-boundary enforcement.

## Pull requests

A useful PR should contain:

1. **Problem** — what is wrong or missing?
2. **Decision** — what changed and why?
3. **Evidence** — how was it tested?
4. **Risk** — what could regress?
5. **Documentation** — what contract or user-facing text changed?

Suggested checklist:

```text
- [ ] Scope is focused
- [ ] Tests added or updated
- [ ] Ruff passes
- [ ] Type checking passes where applicable
- [ ] Security implications reviewed
- [ ] Persistence/replay implications considered
- [ ] Documentation updated
- [ ] No unsupported claims introduced
- [ ] Breaking changes are explicit
```

`CODEOWNERS` currently assigns repository ownership to `@canstralian`. Review and merge requirements should be described by the actual GitHub branch-protection configuration rather than assumed from this document.

## Documentation standard

Documentation is part of the product. Keep these distinctions explicit:

- **Implemented** — demonstrable in current code/tests/workflows;
- **Configured** — present in repository configuration, but a passing run must be verified separately;
- **Specification** — a defined contract or design under review;
- **Planned** — intended future work;
- **Unverified** — insufficient evidence for a stronger claim.

Never use performance numbers, compliance claims, coverage percentages, availability targets, security guarantees, or "production-ready" language unless current repository evidence supports the claim.

When an API or CLI changes, update the corresponding reference documentation in the same change.

## Commit messages

Use a concise imperative subject, preferably in a conventional form such as:

```text
docs: clarify replay limitations
fix(policy): preserve deny precedence
feat(mcp): add governed capability evaluation
```

## Security reporting

Please do not disclose vulnerabilities in public issues.

[Click here to report a security vulnerability](mailto:distortedprojection@gmail.com)

See [`SECURITY.md`](SECURITY.md) for reporting expectations.

## Good places to contribute

RIF has particularly useful work at the seams between implementation and specification:

- executable policy semantics;
- replay and evidence contracts;
- provider egress governance;
- security regression tests;
- API/CLI documentation derived from actual behaviour;
- reproducible development tooling;
- reducing drift between `spec/`, `docs/`, and `src/`.

If you are unsure whether a change belongs in implementation or specification review, document the ambiguity first. A precise question is often more valuable than a premature abstraction.

## License

By contributing, you agree that your contributions are provided under the repository's MIT license, subject to its terms.
