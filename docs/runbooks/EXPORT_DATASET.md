# Runbook: Export a Dataset

## When to use this

Use when running the full pipeline against one or more registered datasets to produce a `DatasetBuild` artifact.

## Prerequisites

- One or more datasets registered in `configs/datasets/`
- A pipeline configuration (default or named)
- An export profile
- RIF Runtime running (for governance evaluation)
- Sufficient disk space for the export artifact

## Steps

### 1. Start RIF Runtime

```bash
rif serve &
```

The pipeline routes all effectful operations through RIF Runtime. It must be running before the pipeline starts.

Verify it is up:

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
```

### 2. Validate configuration

```bash
rif-dataset validate-config
rif-dataset validate-registry
```

Fix any validation errors before proceeding.

### 3. Dry run

Preview what the pipeline will do without fetching data or writing artifacts:

```bash
rif-dataset build \
  --dataset code-alpaca \
  --profile sft \
  --dry-run
```

Output shows:
- Which stages will run
- Which chunker will be used per content type
- Estimated record count from the registry entry
- Which governance evaluations will be requested
- Output path

Review the dry-run output and confirm it matches expectations.

### 4. Run the pipeline (sample)

Start with a sample to verify the pipeline produces correct output before running on the full dataset:

```bash
rif-dataset build \
  --dataset code-alpaca \
  --profile sft \
  --limit 1000 \
  --output /data/builds/test/ \
  --verbose
```

Review:
- Log output: check for governance denials, license exclusions, quality exclusions
- Output artifact: inspect the first few records
- Stage reports: check exclusion counts and reasons

### 5. Run the full pipeline

```bash
rif-dataset build \
  --dataset code-alpaca \
  --profile sft \
  --output /data/builds/ \
  --version 1.0.0
```

The command blocks until the build completes. For large datasets, run in a screen or tmux session.

### 6. Verify the build

```bash
rif-dataset verify-build <build_id>
```

This checks:
- Manifest exists and is valid
- Artifact hash matches `DatasetBuild.artifact_hash`
- Record count in the artifact matches the manifest

If the build is flagged as `reproducible: true`, also verify:

```bash
rif-dataset verify-lineage <build_id>
```

### 7. Review the audit trail

```bash
curl -s http://127.0.0.1:8000/v1/audit | python3 -m json.tool
```

Confirm all governance evaluations during the build are recorded and show `allow`.

### 8. Publish to HuggingFace (if applicable)

If the profile is configured with `format: huggingface` and `hf_repo_id`:

```bash
rif-dataset publish \
  --build <build_id> \
  --confirm
```

`--confirm` is required for publish operations. The command will display the target repo and record count before proceeding.

Publication is a governed operation (PUBLISH effect). A policy evaluation is required before the push. If the runtime posture is `elevated` or `restricted`, the publish may be denied; resolve the posture first.

### 9. Record the build

Note the build ID and artifact hash. Update the release notes if this is a versioned release (see `docs/runbooks/RELEASE.md`).

## Combining multiple datasets

```bash
rif-dataset build \
  --dataset code-alpaca,open-orca \
  --profile sft \
  --output /data/builds/ \
  --version 1.0.0
```

The pipeline ingests each dataset in sequence, merges the records, and applies license validation across the combined set. The composite license is the most restrictive tier across all sources.

## Re-running a build

Re-running with the same configuration produces a new build with a new manifest ID and build ID. The new build is reproducible against the same pinned sources.

To reproduce an exact previous build:
1. Check out the same git commit that was used for the original build.
2. Use the same `--version`.
3. Verify the source hashes match the original manifest.

## Troubleshooting

**Governance denial:** Check the posture (`GET /v1/telemetry/summary`) and the policy rules (`GET /v1/policies`). Reset posture if needed (`POST /v1/posture/reset`).

**License exclusions:** Check the license summary in the stage report. Route unexpected exclusions to the License Governor.

**Quality exclusions > 50%:** Lower the `min_quality_score` in the profile, or switch to a more permissive scorer. High exclusion rates may indicate a content type classification problem.

**Build fails partway through:** The `BuildFailureRecord` is in `data/build_attempts/<id>.json`. Review the stage and error message.
