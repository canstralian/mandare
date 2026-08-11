# Runbook: Build an Export Profile

## When to use this

Use when creating a new export profile (SFT, DPO, RAG, evaluation, or custom) that changes field mapping, filtering, quality thresholds, or format.

## Prerequisites

- Clear understanding of the target training format required by the downstream consumer
- The output field names expected by the training framework
- The license requirements for the intended use
- A profile ID (lowercase alphanumeric with hyphens)

## Steps

### 1. Identify the profile type

Pick the closest built-in type:

| Type | Use when |
| --- | --- |
| `sft` | Prompt/completion or instruction-following data |
| `dpo` | Chosen/rejected preference pairs |
| `rag` | Retrieval corpus (documents with IDs and metadata) |
| `evaluation` | Benchmark data with ground-truth answers |
| `custom` | None of the above |

Custom profiles should extend a built-in type when possible.

### 2. Understand the target field schema

Document the fields your training framework expects. Example for an SFT framework:

```
Required fields: instruction, output
Optional fields: input, system
Format: JSONL, one object per line
```

### 3. Create the profile config

```bash
# Create configs/profiles/<your-id>.yaml
```

Extending a built-in:

```yaml
id: my-sft-v1
name: My SFT Profile v1
extends: sft

format: jsonl
profile_type: sft

field_mapping:
  prompt: instruction
  completion: output
  system: system                  # optional; omit if not needed

filters:
  - exclude_content_type: [trace, structured]
  - min_message_count: 2          # for conversation records

min_quality_score: 0.65
max_token_count: 2048
min_token_count: 32
permit_review_required: false

license_requirements:
  permitted_tiers: [permissive]
  non_commercial_permitted: false
  require_attribution_in_manifest: true
```

From scratch:

```yaml
id: my-rag-corpus
name: Internal RAG Corpus
format: parquet
profile_type: rag

field_mapping:
  id: doc_id
  text: chunk_text
  source_id: source
  token_count: n_tokens
  quality_score: score

filters:
  - exclude_content_type: [trace]
  - min_token_count: 64

min_quality_score: 0.55
max_token_count: 512
permit_review_required: false

license_requirements:
  permitted_tiers: [permissive, copyleft_weak]
```

### 4. Validate the profile config

```bash
rif-dataset validate-profile my-sft-v1
```

Checks:
- Config is valid YAML and matches the `DatasetExportProfile` schema
- All required fields are present
- `field_mapping` references valid canonical field names
- `license_requirements.permitted_tiers` are valid tier names

### 5. Test the profile against a sample manifest

```bash
rif-dataset build \
  --dataset code-alpaca \
  --profile my-sft-v1 \
  --limit 500 \
  --output /tmp/test-export/
```

Review the output:
- Confirm field names match the expected schema
- Confirm records below `min_quality_score` are excluded
- Confirm license filtering is correct
- Confirm format (JSONL, Parquet, etc.) is correct
- Count records; verify against expected exclusion rates

### 6. Validate the output format

Manually inspect the first few records:

```bash
# The JSONL exporter names the output file <build_id>.jsonl by default.
# Capture the build ID from the export output, or set output_filename: data.jsonl
# in the profile to use a predictable name.
BUILD_ID=$(rif-dataset build --config my-sft-v1 --dataset test-dataset --dry-run | grep build_id | awk '{print $2}')
head -5 /tmp/test-export/${BUILD_ID}.jsonl | python3 -m json.tool
```

Confirm the field names and values are correct for the downstream consumer.

### 7. Commit

```bash
git add configs/profiles/my-sft-v1.yaml
git commit -m "feat(profiles): add my-sft-v1 export profile"
```

## Updating an existing profile

Profile changes are versioned:

- Threshold or filter changes: bump `minor` in `DatasetBuild.version`.
- Field mapping changes that are backward-compatible: bump `patch`.
- Format or schema changes: bump `major`.

Changing a profile config without creating a new version means any existing builds that used the old config are no longer reproducible with the new config. If that is acceptable, document it in the commit message. If not, create a new profile ID (e.g., `my-sft-v2`).
