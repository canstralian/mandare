# Runbook: Add a Dataset

## When to use this

Use when registering a new source dataset for ingestion by the Dataset Foundry pipeline.

## Prerequisites

- Access to the dataset source (HuggingFace Hub or local path)
- License information for the dataset
- A dataset ID (lowercase alphanumeric with hyphens)

## Steps

### 1. Identify the license

Before anything else, identify the dataset's license.

Check:
- The dataset's HuggingFace Hub page (Metadata → License)
- The dataset's README
- The dataset's source repository

If the license is a known SPDX identifier (MIT, Apache-2.0, CC-BY-4.0, etc.), check whether a config already exists under `configs/licenses/`. If not, create one:

```bash
# Check existing licenses
ls configs/licenses/

# If not present, create configs/licenses/<spdx-id>.yaml
```

See `docs/specifications/LICENSE_POLICY.md` for the license config schema.

If the license is custom, proprietary, or unclear: **stop here** and route to the License Governor for review. Do not proceed with registration until the license is classified.

### 2. Create the registry entry

```bash
# Create configs/datasets/<your-id>.yaml
```

Minimum viable entry:

```yaml
id: your-dataset-id
name: Human Readable Name
description: "One sentence describing the dataset."

source_type: huggingface        # or: local, url
source_ref: owner/dataset-name
source_version: null            # set to a HF revision hash for reproducibility

license_id: apache-2.0          # must match a file in configs/licenses/
content_types:
  - conversation                 # one or more: code, conversation, document, trace, structured

config:
  split: train
  trust_remote_code: false
  streaming: true

enabled: true
tags: []

added_by: <your-name-or-agent-id>
added_at: 2026-08-05
```

### 3. Pin the source version (recommended)

For reproducibility, pin the source to a specific HuggingFace dataset revision:

```bash
# Get the current commit hash for the dataset
python3 -c "
from huggingface_hub import dataset_info
info = dataset_info('owner/dataset-name')
print(info.sha)
"
```

Set `source_version: <hash>` in the registry entry.

### 4. Validate the registry entry

```bash
rif-dataset validate-registry your-dataset-id
```

This checks:
- Config is valid YAML and matches the schema
- `license_id` references a valid config file
- `source_ref` format is valid for the `source_type`
- No duplicate ID

Fix any validation errors before proceeding.

### 5. Test ingestion

```bash
rif-dataset ingest --dataset your-dataset-id --limit 100
```

`--limit 100` loads only the first 100 records. Review the output:
- Check that records are well-formed
- Check that `content_type` classification looks correct
- Check that license annotation is `compatible`

If content type classification is wrong, adjust `content_types` in the registry entry.

### 6. Run license validation

```bash
rif-dataset validate-license your-dataset-id --profile sft
```

Review the output. All records should report `license_status=compatible` for the target profile. If any report `review_required`, route to the License Governor before proceeding.

### 7. Commit

```bash
git add configs/datasets/your-dataset-id.yaml
# If you created a new license config:
git add configs/licenses/<license-id>.yaml
git commit -m "feat(registry): add <dataset-name> dataset"
```

## Post-merge

After the PR merges:
- The dataset is available for pipeline builds via `--dataset your-dataset-id`.
- If `enabled: true`, it will be included in builds that use `--all-datasets`.
- Update `docs/research/DATASET_SURVEY.md` if this is a notable dataset worth documenting.

## Disabling a dataset

Do not delete the registry entry. Set `enabled: false`:

```yaml
enabled: false
disabled_reason: "License changed to non-commercial. See issue #XXX."
disabled_at: 2026-09-01
```
