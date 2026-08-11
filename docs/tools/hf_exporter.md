# Tool: hf_exporter

## Extension point

Exporter

## Purpose

Publish a `DatasetBuild` artifact to HuggingFace Hub as a dataset repository.

## Input

`Iterable[DatasetChunk]`, `DatasetExportProfile`, `DatasetManifest`, `BuildContext`.

## Output

`ExportArtifactRecord` with the HF repo URL and commit hash.

## Effect

PUBLISH — governed. Calls `context.governance.evaluate("PUBLISH", hf_repo_id)` before pushing.

This is the highest-stakes operation in the pipeline. A PUBLISH policy denial halts the export and records the denial in the audit trail.

## Config

```yaml
# In DatasetExportProfile:
format: huggingface
hf_repo_id: my-org/my-dataset    # required
hf_private: true                  # true = private repo; false = public
hf_commit_message: null           # null = auto-generated from build metadata
hf_branch: main                   # target branch
upload_format: parquet            # internal format: parquet | jsonl
compression: snappy               # for parquet upload; see parquet_exporter
```

## HF token

The HF token is read from the `HF_TOKEN` environment variable. It must never be set in the config file.

The token must have write access to `hf_repo_id`.

## Upload flow

1. Evaluate `PUBLISH` governance.
2. Write the export artifact to a local temp file (using `parquet_exporter` or `jsonl_exporter`).
3. Create or verify the HF dataset repository at `hf_repo_id`.
4. Upload the data file(s) to the repository.
5. Upload the `DatasetManifest` as `manifest.json` in the repository.
6. Upload the `dataset_info.json` (HF dataset card metadata) derived from the manifest.
7. Verify the upload: fetch the dataset and count rows.
8. Return `ExportArtifactRecord` with the HF commit hash.

## HF dataset card

The exporter auto-generates a `README.md` (dataset card) from the manifest:

```markdown
---
license: apache-2.0
language:
  - en
tags:
  - code
  - sft
---

# My Dataset

Built with Dataset Foundry v1.0.0.

**Build ID**: `<build_id>`
**Manifest**: [manifest.json](manifest.json)
**Records**: 19,500
**Quality threshold**: 0.60
**Sources**: code-alpaca (Apache-2.0)
```

The dataset card is not authoritative. Always refer to `manifest.json` for the full lineage.

## Failure modes

| Error | Condition | Behavior |
| --- | --- | --- |
| `GovernanceDenied` | PUBLISH policy denied | Raises; build halts; no upload |
| `HfHubHTTPError: 401` | Invalid HF token | Raises `ExportError` |
| `HfHubHTTPError: 403` | No write access to repo | Raises `ExportError` |
| `RepositoryNotFoundError` | Repo does not exist and cannot be created | Raises `ExportError` |
| `UploadError` | Network failure during upload | Raises `ExportError`; partial upload may exist on HF Hub |
| `VerificationError` | Row count on HF Hub != expected | Raises `ExportIntegrityError` after upload |

## Recovery from partial upload

If the upload fails partway through, the HF repository may be in a partial state. To recover:

1. Delete the partial commit on HF Hub (via the HF Hub web UI or API).
2. Re-run the export. The exporter does not resume partial uploads; it restarts.

## Requirements

- `huggingface_hub` library installed (`pip install huggingface_hub`)
- `HF_TOKEN` environment variable with write access to `hf_repo_id`
- RIF Runtime's PUBLISH policy permits `hf_repo_id` as a target

## Governance note

Publishing to HuggingFace Hub makes data publicly available (if `hf_private: false`) or accessible to all members of the HF organization (if `hf_private: true`). This is an irreversible operation from a data-distribution perspective; even if the repository is later deleted, copies may exist.

Only publish datasets that have:
- Passed license validation
- Passed quality benchmarks
- Received human review approval (License Governor and Quality Reviewer sign-off)
