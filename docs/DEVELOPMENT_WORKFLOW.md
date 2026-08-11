# Development Workflow

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -r requirements-dev.txt
```

## Quality gates (run before every commit)

```bash
ruff check src tests
ruff format .
mypy src/rif_runtime --ignore-missing-imports
pytest -q
```

CI enforces all four on every push. A change is not done until all four pass.

## Before implementing anything

1. Read the relevant specification in `docs/specifications/`.
2. Read the agent definition that owns the area (see `docs/agents/`).
3. Read any applicable ADRs in `docs/adr/`.
4. If the change introduces a new architecture decision, draft an ADR first.

Architecture before implementation. Configuration before code. Specification before PR.

## Adding a new dataset

Follow `docs/runbooks/ADD_DATASET.md`.

Short version:

1. Add entry to `configs/datasets/<id>.yaml`.
2. Add license entry to `configs/licenses/<id>.yaml`.
3. Run the ingest skill: verify canonical DatasetRecord output.
4. Run the license validation skill: verify compatibility with target profiles.
5. Run quality scoring: verify score meets profile threshold.
6. Commit `configs/` changes and the generated manifest.

Do not modify pipeline logic to accommodate a specific dataset. If the pipeline cannot handle the dataset, extend the configuration schema or add a plugin.

## Adding a new chunker

Follow `docs/runbooks/CREATE_CHUNKER.md`.

Short version:

1. Write the specification in `docs/specifications/CHUNKING_SPEC.md` (extend the relevant section).
2. Implement the chunker under `src/rif_runtime/dataset/chunkers/<name>.py`.
3. Register it in `configs/chunkers/<name>.yaml`.
4. Add a test under `tests/dataset/chunkers/test_<name>.py`.
5. Update `docs/tools/<name>_chunker.md`.

## Adding an export profile

Follow `docs/runbooks/BUILD_PROFILE.md`.

Short version:

1. Define the profile in `configs/profiles/<name>.yaml`.
2. Validate field mapping against `DatasetExportProfile` schema.
3. Run export against a test manifest.
4. Verify output matches the expected format contract in `docs/specifications/EXPORT_PROFILES.md`.

## Branching and commits

- Feature work: `feat/<short-description>`
- Bug fixes: `fix/<short-description>`
- Specification work: `spec/<short-description>`
- ADRs: `adr/<number>-<short-description>`

Every commit message must explain the intent, not just the change. Reference the specification or ADR that governs the work when applicable.

## Pull request requirements

Every PR must:

- Pass all quality gates
- Include or reference a specification for any new behavior
- Include tests for new pipeline stages, chunkers, exporters, or quality models
- Update `docs/` when the change affects contracts, API surface, or workflows
- Not regress existing `ruff check`, `mypy`, or `pytest` results

## Governance

All effectful operations in the Dataset Foundry pipeline (network fetches, file writes, HF Hub pushes) must pass through RIF Runtime policy evaluation.

Adding a new effectful operation requires:

1. Identifying the operation's effect type (READ, WRITE, SNAPSHOT, PUBLISH)
2. Declaring the operation in the relevant tool specification (`docs/tools/`)
3. Routing the operation through `PolicyEngine.evaluate()` before execution
4. Recording the decision in the audit trail

No effectful operation may bypass governance.
