# Tool: huggingface_loader

## Extension point

Loader

## Purpose

Load datasets from the HuggingFace Hub into `DatasetRecord` objects.

## Input

`DatasetRegistryEntry` with `source_type: huggingface`.

## Output

`Iterable[DatasetRecord]` — one record per row in the source dataset.

## Effect

READ — governed. Calls `context.governance.evaluate("READ", "hf://<source_ref>")` before fetching.

## Config

```yaml
# configs/ entry in DatasetRegistryEntry.config:
split: train          # required; the HF dataset split to load
name: null            # optional; HF dataset config name (e.g., "python" for the-stack)
trust_remote_code: false   # must be false unless explicitly approved
streaming: true       # true = streaming mode (recommended for large datasets)
num_proc: null        # parallelism for non-streaming loads; null = single process
```

## Field mapping

The loader produces records with source fields preserved verbatim in `DatasetRecord.metadata`. The `Normalizer` stage maps these to canonical fields.

The loader does set:

| DatasetRecord field | Value |
| --- | --- |
| `id` | SHA-256 of `f"{source_ref}:{split}:{source_index}"` |
| `source_id` | Registry entry `id` |
| `source_index` | Row index in the split |
| `content_type` | `unknown` (set by Classifier stage) |
| `license_status` | `unknown` (set by LicenseValidator stage) |
| `metadata` | All source row fields |
| `created_at` | Fetch timestamp |

## SourceLineage produced

```python
SourceLineage(
    registry_entry_id=entry.id,
    source_ref=entry.source_ref,
    source_version=entry.source_version,
    fetch_timestamp=datetime.now(timezone.utc),
    record_count=<count>,
    hash=<sha256 of all row content>,
)
```

The hash is computed by streaming all rows and updating a SHA-256 digest. It is the integrity anchor for reproducibility.

## Failure modes

| Error | Condition | Behavior |
| --- | --- | --- |
| `GovernanceDenied` | READ policy denied | Raises; build halts |
| `DatasetNotFound` | Source ref not found on HF Hub | Raises `LoaderError`; build halts |
| `RevisionNotFound` | `source_version` not found | Raises `LoaderError`; build halts |
| `TrustRemoteCodeRequired` | Dataset requires `trust_remote_code=True` | Raises `LoaderError`; do not set `trust_remote_code=True` without approval |
| `RateLimitError` | HF Hub rate limit | Raises `LoaderError`; retry with backoff (caller's responsibility) |

## Streaming vs batch mode

**Streaming (recommended):** `streaming: true`

- Records are yielded lazily; only the current record is in memory.
- The source hash is computed incrementally.
- Does not require a local dataset cache.
- Required for datasets too large to fit in memory.

**Batch:** `streaming: false`

- All rows are downloaded to the HF cache before yielding.
- Faster for small datasets.
- Not suitable for datasets > available memory.

## Requirements

- `datasets` library installed (`pip install datasets`)
- `HF_TOKEN` environment variable set for private or gated datasets
- `trust_remote_code: false` (default; do not override without security review)
