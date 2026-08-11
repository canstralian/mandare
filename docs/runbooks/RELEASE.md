# Runbook: Release

## When to use this

Use when cutting a new release of the Dataset Foundry platform (code) or publishing a versioned dataset build.

## Platform release (code)

### 1. Check CI is green

All checks on `main` must be passing before cutting a release:

- `ruff check src tests`
- `ruff format .` (no diff)
- `mypy src/rif_runtime --ignore-missing-imports`
- `pytest -q`

Do not cut a release from a failing CI state.

### 2. Determine the version bump

Follow semver:

| Change type | Bump |
| --- | --- |
| Bug fixes, documentation | `patch` |
| New chunker, exporter, or profile | `minor` |
| Schema change, new pipeline stage, API change | `major` |

The version is defined in `pyproject.toml` (single source of truth).

### 3. Bump the version

```bash
scripts/bump-version.sh X.Y.Z
pip install -e .
```

Verify:

```bash
python3 -c "import rif_runtime; print(rif_runtime.__version__)"
```

### 4. Update the release notes

Create `docs/releases/vX.Y.Z.md`:

```markdown
# vX.Y.Z — YYYY-MM-DD

## What's new

- ...

## Bug fixes

- ...

## Breaking changes

- ...

## Dataset builds included

| Build ID | Profile | Record count |
| --- | --- | --- |
| ... | ... | ... |
```

### 5. Commit and tag

```bash
git add pyproject.toml docs/releases/vX.Y.Z.md
git commit -m "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

### 6. Verify the release

After CI completes on the tag:

```bash
pip install rif-runtime==X.Y.Z
python3 -c "import rif_runtime; print(rif_runtime.__version__)"
```

---

## Dataset build release

A dataset build release publishes a versioned `DatasetBuild` to HuggingFace Hub.

### 1. Produce the build

Follow `docs/runbooks/EXPORT_DATASET.md` to produce a complete, verified build.

### 2. Verify the build

```bash
rif-dataset verify-build <build_id>
rif-dataset verify-lineage <build_id>   # if reproducible=true
```

Both must pass.

### 3. Check license compliance

```bash
rif-dataset license-report <build_id>
```

The report must show:
- No `incompatible` records
- No `review_required` records (unless covered by a `HumanApprovalRecord`)
- Composite license tier recorded in the manifest

### 4. Require human review for publication

Dataset publication to HuggingFace Hub is not automated. A human must:

1. Review the license report
2. Review a sample of the output data
3. Confirm the build is appropriate for the target HF repository's audience
4. Approve the publish command

Record the approval in the manifest before publishing (the `HumanApprovalRecord` field if applicable).

### 5. Publish

```bash
rif-dataset publish \
  --build <build_id> \
  --confirm \
  --message "Dataset Foundry vX.Y.Z: <profile> dataset"
```

The publish command requests a `PUBLISH` policy evaluation from RIF Runtime. If approved, it pushes the artifact to HuggingFace Hub.

### 6. Verify publication

```bash
python3 -c "
from datasets import load_dataset
ds = load_dataset('<hf_repo_id>')
print(len(ds['train']))
"
```

Confirm the record count matches `DatasetBuild.record_count`.

### 7. Update release notes

Add the HF dataset URL and commit hash to `docs/releases/vX.Y.Z.md`.
