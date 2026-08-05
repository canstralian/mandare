# Tool: jsonl_exporter

## Extension point

Exporter

## Purpose

Write `DatasetChunk` records to a JSONL (newline-delimited JSON) file.

## Input

`Iterable[DatasetChunk]`, `DatasetExportProfile`, `DatasetManifest`, `BuildContext`.

## Output

`ExportArtifactRecord` pointing to the written `.jsonl` file.

## Effect

WRITE — governed. Calls `context.governance.evaluate("WRITE", artifact_path)` before opening the file.

## Config

```yaml
# In DatasetExportProfile:
format: jsonl
compression: null       # null | gz | zst
output_filename: null   # null = <build_id>.jsonl
```

## Output format

One JSON object per line, fields determined by `profile.field_mapping`:

```json
{"prompt": "Write a Python function to...", "completion": "def solve(n):\n    ..."}
{"prompt": "Explain recursion.", "completion": "Recursion is..."}
```

For conversation records (when `messages` is in the field mapping):

```json
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

## Compression

| `compression` | Extension | Notes |
| --- | --- | --- |
| `null` | `.jsonl` | Default; uncompressed |
| `gz` | `.jsonl.gz` | gzip compression; compatible with most tools |
| `zst` | `.jsonl.zst` | Zstandard; faster and better ratio than gzip |

## Artifact hash

The hash is computed by streaming SHA-256 over the compressed or uncompressed file content after writing.

```python
artifact_hash = f"sha256:{sha256_of_file}"
```

## Record count verification

After writing, the exporter re-counts records by reading the file back and counting lines. The count must match the number of chunks that passed filters. A mismatch raises `ExportIntegrityError`.

## Failure modes

| Error | Condition | Behavior |
| --- | --- | --- |
| `GovernanceDenied` | WRITE policy denied | Raises; build halts |
| `DiskFull` | No space on device | Raises `ExportError`; partial file may exist |
| `SerializationError` | Chunk cannot be serialized to JSON | Logs warning; chunk is skipped; raises if >1% of chunks fail |
| `ExportIntegrityError` | Written line count != expected | Raises; artifact is deleted |

## Output filename

```
<output_path>/<build_id>.jsonl          # uncompressed
<output_path>/<build_id>.jsonl.gz       # gzip
<output_path>/<build_id>.jsonl.zst      # zstd
```

If `output_filename` is set in the profile, it overrides `<build_id>`.

## Streaming write

The exporter streams records from the input iterable. It does not buffer all records in memory. Maximum memory usage is one serialized JSON line at a time plus the SHA-256 digest state.
