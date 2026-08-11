# Skill: semantic_chunking

## Purpose

Segment normalized `DatasetRecord` objects into `DatasetChunk` objects using content-type-appropriate chunking strategies.

## When to use

- As part of the full build pipeline (dispatched automatically by the Chunking stage)
- When evaluating a new chunker against a sample dataset
- When debugging unexpected chunk size distributions

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `records` | `Iterable[DatasetRecord]` | Normalized, classified records |
| `chunker_map` | `dict[ContentType, str]` | Maps content type to chunker ID |
| `chunker_configs` | `dict[str, ChunkerConfig]` | Config per chunker ID |

## Preconditions

- Records are normalized (canonical schema) and classified (content_type set)
- All chunker IDs in `chunker_map` are registered in `configs/chunkers/`
- Records with `license_status=incompatible` are already excluded

## Execution steps

1. For each record:
   a. Look up the chunker for `record.content_type` from `chunker_map`.
   b. Call `chunker.chunk(record)`.
   c. If the chunker raises `ChunkerParseError`, fall back to `SlidingWindowChunker`.
   d. Apply `min_chunk_tokens` enforcement: merge undersized chunks with the preceding chunk.
   e. Apply `max_chunk_tokens` enforcement: split oversized chunks with `SlidingWindowChunker`.
   f. Collect output chunks.
2. Return all chunks and a `ChunkingReport`.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `chunks` | `Iterable[DatasetChunk]` | Semantic chunks from all records |
| `report` | `ChunkingReport` | Counts, size distribution, fallback rate |

## ChunkingReport

```python
class ChunkingReport(BaseModel):
    input_record_count: int
    output_chunk_count: int
    chunks_per_record_mean: float
    chunks_per_record_p50: float
    chunks_per_record_p90: float
    char_count_p10: int
    char_count_p50: int
    char_count_p90: int
    fallback_count: int               # records that fell back to SlidingWindow
    fallback_fraction: float
    oversized_split_count: int
    undersized_merge_count: int
    chunker_breakdown: dict[str, int] # chunker_id -> chunk count
```

## Validation

After chunking:

- `output_chunk_count >= input_record_count` (at least one chunk per record)
- All chunks have `char_count == len(chunk.text)`
- All chunks reference a valid `record_id` from the input
- Chunk IDs are unique across the output

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| `fallback_fraction > 0.3` | Primary chunker failing on most records | Investigate parse errors; check content type classification |
| `char_count_p90` very high | `max_chunk_tokens` not enforced | Verify chunker config has `max_chunk_tokens` set |
| `char_count_p10` very low | Many small chunks not merged | Verify `min_chunk_tokens` is set; check fallback merge logic |
| Duplicate chunk IDs | Non-deterministic chunker | Chunker violates the determinism contract; fix the chunker |

## Evidence produced

- `TransformationRecord` in `LineageCollector` with chunk counts and fallback rate
- `ChunkingReport` embedded in `DatasetManifest.stage_reports["chunker"]`
