# Tool: markdown_chunker

## Extension point

Chunker

## Content type

`document`

## Purpose

Segment Markdown (and RST) documents into section chunks at heading boundaries.

## Input

`DatasetRecord` with `content_type=document` and non-empty `text`.

## Output

`list[DatasetChunk]` — one chunk per document section.

## Effect

None. Pure computation.

## Config

```yaml
chunker_id: markdown_chunker
type: builtin

# Heading levels to split on
split_on_h1: true
split_on_h2: true
split_on_h3: false

# Maximum nesting depth; sections deeper than max_depth are merged into their parent
max_depth: 2

# If true, fenced code blocks (``` ... ```) are never split
preserve_code_blocks: true

# If true, the section heading is included in the chunk text
include_heading: true

max_chunk_tokens: 2048
min_chunk_tokens: 64
```

## Chunking strategy

1. Parse the document for heading markers (`#`, `##`, `###` for Markdown; underline headings for RST).
2. Split at each heading of a level that is in the split set (`split_on_h1`, `split_on_h2`, `split_on_h3`).
3. Sections deeper than `max_depth` are appended to their nearest ancestor that is within the depth limit.
4. If `preserve_code_blocks=true`, a heading marker inside a fenced code block is not treated as a split point.
5. Apply size enforcement (merge undersized, split oversized).

## No-heading fallback

If the document contains no heading markers, the chunker falls back to `SlidingWindowChunker`. This is recorded in the `StageReport` as `chunker_fallback`.

## RST support

RST underline headings are detected by the pattern:

```
Heading Title
=============
```

RST split levels map to Markdown levels:
- `=` underline → H1
- `-` underline → H2
- `~` underline → H3

RST support is best-effort. Complex RST (directives, substitutions) is not parsed; such documents may produce incorrect section boundaries.

## Failure modes

| Condition | Behavior |
| --- | --- |
| No headings found | Falls back to `SlidingWindowChunker` |
| All sections below `min_chunk_tokens` | Merges all sections into a single chunk |
| Section above `max_chunk_tokens` | Section is split with `SlidingWindowChunker` |
| Code block contains heading markers | Heading markers inside ``` blocks are ignored |

## Chunk metadata

Each chunk includes in its `metadata`:

```python
{
    "heading": "Section Title",
    "heading_level": 2,
    "section_index": 3,       # position in document
    "parent_heading": "Parent Section",
}
```
