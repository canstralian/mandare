# Tool: parquet_exporter

## Extension point

Exporter

## Purpose

Write `DatasetChunk` records to a Parquet file.

## Input

`Iterable[DatasetChunk]`, `DatasetExportProfile`, `DatasetManifest`, `BuildContext`.

## Output

`ExportArtifactRecord` pointing to the written `.parquet` file.

## Effect

WRITE — governed. Calls `context.governance.evaluate("WRITE", artifact_path)` before writing.

## Config

```yaml
# In DatasetExportProfile:
format: parquet
compression: snappy     # snappy | gzip | zstd | none
row_group_size: 1000    # rows per Parquet row group
output_filename: null   # null = <build_id>.parquet
```

## Output schema

Parquet schema is derived from `profile.field_mapping`. Each mapped field becomes a column.

Column types:

| Canonical field | Parquet type |
| --- | --- |
| `id` | STRING |
| `text` | STRING (LARGE_STRING for large datasets) |
| `source_id` | STRING |
| `content_type` | STRING (dictionary-encoded) |
| `quality_score` | FLOAT |
| `token_count` | INT32 |
| `char_count` | INT32 |
| `chunker_id` | STRING (dictionary-encoded) |
| `messages` | JSON STRING (serialized) |
| `metadata.*` | STRING (JSON-serialized dict) |

## Compression

| `compression` | Notes |
| --- | --- |
| `snappy` | Default; fast, moderate ratio; widely supported |
| `gzip` | Better ratio; slower write; compatible with older tools |
| `zstd` | Best ratio; fast decompression; recommended for large datasets |
| `none` | Uncompressed; largest file; fastest write |

## Artifact hash

SHA-256 of the written Parquet file content.

## Requirements

- `pyarrow` library installed (`pip install pyarrow`)

## Row group tuning

`row_group_size` controls how many rows are buffered in memory before flushing to disk. Smaller values reduce memory usage; larger values improve query performance on the output file.

For datasets > 1M rows, use `row_group_size: 10000` for a balance of memory and query efficiency.

## Failure modes

| Error | Condition | Behavior |
| --- | --- | --- |
| `GovernanceDenied` | WRITE policy denied | Raises; build halts |
| `ArrowTypeError` | Field value cannot be cast to declared Parquet type | Logs warning; chunk is skipped |
| `DiskFull` | No space on device | Raises `ExportError`; partial file may exist |

## Output filename

```
<output_path>/<build_id>.parquet
```

If `output_filename` is set in the profile, it overrides `<build_id>`.
