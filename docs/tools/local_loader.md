# Tool: local_loader

## Extension point

Loader

## Purpose

Load datasets from local filesystem paths into `DatasetRecord` objects.

## Input

`DatasetRegistryEntry` with `source_type: local`.

## Output

`Iterable[DatasetRecord]` — one record per row or file in the source.

## Effect

READ — governed. Calls `context.governance.evaluate("READ", source_path)` before reading.

## Config

```yaml
# configs/ entry in DatasetRegistryEntry.config:
format: jsonl        # jsonl | parquet | csv | arrow
glob: "*.jsonl"      # file pattern within source_ref directory
encoding: utf-8      # file encoding (for text formats)
delimiter: ","       # CSV delimiter (for csv format only)
has_header: true     # CSV header row (for csv format only)
```

## Supported formats

| Format | Record source | Notes |
| --- | --- | --- |
| `jsonl` | Each line is a JSON object | Empty lines are skipped |
| `parquet` | Each row is a record | Multiple files supported via glob |
| `arrow` | Each row is a record | Multiple files supported via glob |
| `csv` | Each row is a record | First row treated as header if `has_header: true` |

## Field mapping

All source fields are preserved in `DatasetRecord.metadata`. The Normalizer maps to canonical fields.

The loader sets:

| DatasetRecord field | Value |
| --- | --- |
| `id` | SHA-256 of `f"{source_path}:{file_name}:{line_index}"` |
| `source_id` | Registry entry `id` |
| `source_index` | Global row index across all files |
| `metadata` | All source row fields |
| `metadata["_source_file"]` | Relative file path within `source_ref` |

## Source hash

The hash in `SourceLineage` is computed as SHA-256 over the sorted list of file hashes within the `source_ref` directory matching the glob pattern.

```
hash = sha256(
    sorted([sha256(file_content) for file in glob_matches])
)
```

This means the hash is stable if files are reordered but changes if any file content changes.

## Failure modes

| Error | Condition | Behavior |
| --- | --- | --- |
| `GovernanceDenied` | READ policy denied | Raises; build halts |
| `SourcePathNotFound` | `source_ref` directory does not exist | Raises `LoaderError` |
| `NoFilesMatchGlob` | No files match `glob` pattern | Raises `LoaderError` |
| `ParseError` | File cannot be parsed in declared format | Raises `LoaderError` with file path |
| `EncodingError` | File encoding does not match `encoding` config | Raises `LoaderError` with file path |

## Notes on local data

Local sources should be listed in `.gitignore` if they contain:

- Non-redistributable data
- Data with unclear license
- Large files that should not be committed

The pipeline does not enforce this; it is the responsibility of the person adding the dataset to the registry.

Local datasets with `source_version: null` are not reproducible. They will have `DatasetManifest.reproducible: false`.
