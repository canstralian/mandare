# Chunking Specification

## Purpose

Define the chunking stage: input contract, chunker selection, output contract, and the built-in chunking strategies.

## What chunking does

Chunking transforms a `DatasetRecord` into one or more `DatasetChunk` objects.

A chunk is a semantically coherent unit of content suitable for a specific training objective. The definition of "semantically coherent" is chunker-dependent and configured per content type.

## Chunker selection

Chunker selection is config-driven. The pipeline configuration maps each `ContentType` to exactly one `chunker_id`:

```yaml
# configs/pipeline/default.yaml
chunker_map:
  code: ast_chunker
  conversation: conversation_chunker
  document: markdown_chunker
  trace: trace_chunker
  structured: sliding_window_chunker
  unknown: sliding_window_chunker
```

A record's `content_type` annotation (set by the Classification stage) determines which chunker runs.

## Chunker interface

```python
class Chunker(Protocol):
    chunker_id: str
    config: ChunkerConfig

    def chunk(self, record: DatasetRecord) -> list[DatasetChunk]:
        ...
```

- `chunk()` is pure and deterministic.
- `chunk()` must return at least one `DatasetChunk` per call.
- `chunk()` must not modify the input `DatasetRecord`.
- Each returned `DatasetChunk` must reference the parent `record_id`.

## ChunkerConfig base fields

```python
class ChunkerConfig(BaseModel):
    chunker_id: str
    max_chunk_tokens: int = 2048
    min_chunk_tokens: int = 32
    overlap_tokens: int = 0
    preserve_boundaries: bool = True
```

Individual chunkers extend `ChunkerConfig` with strategy-specific fields.

## Built-in chunkers

### ast_chunker

For `content_type=code`.

Parses Python source with the `ast` module. Produces one chunk per top-level definition:

- Module-level constants and assignments: one chunk
- Functions: one chunk per function (including docstring)
- Classes: one chunk per class body (class def + all methods)
- Methods extracted separately when `extract_methods=true`

Config:

```yaml
chunker_id: ast_chunker
language: python                 # only python supported currently
extract_methods: false           # if true, methods become separate chunks
include_imports: true            # if true, import block prepended to each chunk
max_chunk_tokens: 1024
min_chunk_tokens: 32
```

Fallback: if parsing fails, the record is rechunked with `sliding_window_chunker`.

### markdown_chunker

For `content_type=document`.

Splits on Markdown heading boundaries. Each section (from one heading to the next) becomes a chunk. Nested headings produce nested chunks; `max_depth` limits nesting.

Config:

```yaml
chunker_id: markdown_chunker
max_depth: 2                     # headings deeper than H2 are merged into H2 chunk
split_on_h1: true
split_on_h2: true
split_on_h3: false
max_chunk_tokens: 2048
min_chunk_tokens: 64
preserve_code_blocks: true       # never split inside a fenced code block
```

Fallback: if no headings are found, the record is chunked with `sliding_window_chunker`.

### conversation_chunker

For `content_type=conversation`.

Operates on `DatasetRecord.messages`. Produces one chunk per complete exchange. An exchange is defined by the `exchange_boundary` config.

Config:

```yaml
chunker_id: conversation_chunker
exchange_boundary: user_turn     # chunk starts at each user turn
max_turns_per_chunk: 4           # max turns before forcing a split
include_system_prompt: true      # if true, system message prepended to every chunk
max_chunk_tokens: 4096
min_chunk_tokens: 32
```

Output format: each chunk's `text` field is a JSON-serialized list of `Message` objects. The `messages` sub-field of the chunk is not used; serialization into `text` allows uniform quality scoring.

### trace_chunker

For `content_type=trace`.

Segments agent execution traces at tool call boundaries. Each chunk is one tool call plus its surrounding context (preceding assistant turn and tool result).

Config:

```yaml
chunker_id: trace_chunker
include_preceding_turns: 1       # assistant turns to include before the tool call
include_following_turns: 0       # turns after the tool result
max_chunk_tokens: 2048
min_chunk_tokens: 32
```

### sliding_window_chunker

Fallback for all content types. Character-based sliding window with configurable overlap.

Config:

```yaml
chunker_id: sliding_window_chunker
max_chunk_chars: 4000
overlap_chars: 200
split_on: "\n\n"                 # preferred split boundary; fallback to any whitespace
```

## Chunk ID generation

Chunk IDs are deterministic:

```python
chunk_id = sha256(f"{record.id}:{chunk_index}").hexdigest()[:16]
```

Re-running the pipeline over the same input produces the same chunk IDs. This is a reproducibility invariant.

## Minimum and maximum size enforcement

Chunks below `min_chunk_tokens` are merged with the preceding chunk if possible. If a record produces only one chunk and it is below `min_chunk_tokens`, it is not excluded — it is emitted as-is with a `small_chunk` annotation.

Chunks above `max_chunk_tokens` are split with `sliding_window_chunker` using the parent chunker's `max_chunk_tokens` as the window size. This is the only case where a secondary chunker runs on material already processed by a primary chunker.

## Overlap

Overlap is disabled by default. When `overlap_tokens > 0`, consecutive chunks share the last `overlap_tokens` tokens of the preceding chunk. Overlap is applied after size enforcement.

## Plugin chunkers

A plugin chunker implements the `Chunker` protocol and is registered in `configs/chunkers/<id>.yaml` with `type: plugin` and a Python import path. See `docs/specifications/PLUGIN_API.md`.
