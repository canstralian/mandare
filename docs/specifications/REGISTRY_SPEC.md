# Registry Specification

## Purpose

Define the dataset registry: the authoritative list of source datasets the pipeline is permitted to ingest.

## What the registry is

The registry is a directory of YAML configuration files. One file per dataset. Files are checked into git. The pipeline may only ingest datasets present in the registry.

No registry entry → no ingestion. The pipeline does not accept arbitrary source references at runtime.

## Registry layout

```text
configs/datasets/
  <id>.yaml         # one file per dataset
```

The `id` matches the filename without the `.yaml` extension. IDs are lowercase alphanumeric with hyphens (`[a-z0-9-]+`).

## Registry entry schema

```yaml
# configs/datasets/code-alpaca.yaml

id: code-alpaca
name: Code Alpaca
description: "Code instruction-following dataset derived from Alpaca."

source_type: huggingface
source_ref: sahil2801/CodeAlpaca-20k
source_version: null              # null = latest; set to a HF revision for pinning

license_id: apache-2.0           # references configs/licenses/apache-2.0.yaml
content_types:
  - conversation
  - code

config:
  split: train
  trust_remote_code: false
  streaming: true

enabled: true
tags:
  - code
  - instruction-following
  - alpaca-derived

added_by: dataset-architect
added_at: 2026-08-05
```

## Source types

### huggingface

```yaml
source_type: huggingface
source_ref: <owner>/<dataset-id>   # HF Hub dataset identifier
source_version: <revision>          # git commit hash or branch; null = latest
config:
  split: train                      # required
  name: <config-name>               # optional HF dataset config
  trust_remote_code: false          # never true without explicit approval
  streaming: true                   # default; false loads entire dataset into memory
```

### local

```yaml
source_type: local
source_ref: data/raw/<id>/          # relative to repository root
source_version: null                # not applicable
config:
  format: jsonl                     # jsonl | parquet | csv | arrow
  glob: "*.jsonl"                   # file pattern within source_ref directory
```

Local sources must be listed in `.gitignore` if they contain non-redistributable data. The pipeline does not enforce this; it is a human responsibility.

### url

```yaml
source_type: url
source_ref: https://example.com/dataset.jsonl
source_version: null
config:
  format: jsonl
  expected_hash: sha256:<hash>      # required for reproducibility
```

URL sources require an `expected_hash` for reproducibility. Fetches that don't match the hash fail the build.

## Enabled flag

`enabled: false` prevents the dataset from being included in any build. It remains in the registry for historical reference.

## Adding a dataset

Follow `docs/runbooks/ADD_DATASET.md`. Short checklist:

1. Create `configs/datasets/<id>.yaml`.
2. Create or reference `configs/licenses/<license_id>.yaml`.
3. Set `source_version` to a pinned revision if reproducibility is required.
4. Set `enabled: true`.
5. Run `rif-dataset validate-registry <id>` to verify the entry.
6. Commit both files.

## Removing a dataset

Do not delete registry entries. Set `enabled: false` and add a `disabled_reason` field:

```yaml
enabled: false
disabled_reason: "License changed to non-commercial in v2. See ADR-XXXX."
disabled_at: 2026-09-01
```

Historical builds that used the dataset retain their lineage references to the entry.

## Registry validation

The registry is validated at pipeline startup:

- All referenced `license_id` values must have corresponding config files.
- `source_ref` format is validated per `source_type`.
- `source_version` is validated as a non-empty string if present.
- Duplicate `id` values across files fail validation.

Validation is enforced by `rif-dataset validate-registry` and by the CI pipeline check.
