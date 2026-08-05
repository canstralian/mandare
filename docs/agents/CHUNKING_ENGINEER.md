# Chunking Engineer

## Mission

Own the chunking stage: segmentation algorithms, content type coverage, and chunk quality.

---

## Responsibilities

- Built-in chunker implementations (AST, Markdown, Conversation, Trace, SlidingWindow)
- Chunker configuration schemas
- Content type to chunker mapping recommendations
- Fallback behavior when primary chunker fails
- Chunk ID determinism and reproducibility
- Chunker performance (throughput, memory usage)
- Research on new chunking strategies

---

## Chunker implementation checklist

Before merging a chunker implementation:

- [ ] Specification added to `docs/specifications/CHUNKING_SPEC.md`
- [ ] Chunk IDs are `sha256(f"{record.id}:{chunk_index}").hexdigest()[:16]` (deterministic)
- [ ] Chunker is pure (no I/O)
- [ ] Empty input returns an empty list, not an error
- [ ] Chunks below `min_chunk_tokens` are merged or annotated (not silently dropped)
- [ ] Chunks above `max_chunk_tokens` are split (not truncated)
- [ ] Fallback to `SlidingWindowChunker` when primary chunker cannot parse the input
- [ ] `chunker_id` on each output chunk matches `self.chunker_id`
- [ ] Tests: determinism, edge cases (empty, single token, oversized), fallback trigger
- [ ] Documentation in `docs/tools/<name>_chunker.md`

---

## Determinism contract

The chunking output must be deterministic:

```
chunk(record_a) == chunk(record_a)   # same input, same output
```

This is required for reproducibility. Any chunker that uses randomness (e.g., sampling for test/train splits) violates the contract and must not be used in the chunking stage.

---

## Fallback behavior

Every primary chunker must define a fallback. The fallback is always `SlidingWindowChunker` unless explicitly configured otherwise.

A fallback is triggered when the primary chunker:
- Raises a `ChunkerParseError` (e.g., AST parse failure)
- Produces zero chunks from non-empty input
- Is called on a record whose content type does not match the chunker's target

Fallback events are recorded in the `StageReport.exclusion_reasons` with key `"chunker_fallback"` and are visible in the manifest.

---

## Content type gaps

Current coverage:

| Content type | Primary chunker | Status |
| --- | --- | --- |
| code (Python) | ast_chunker | Implemented |
| conversation | conversation_chunker | Implemented |
| document (Markdown) | markdown_chunker | Implemented |
| trace | trace_chunker | Implemented |
| structured | sliding_window_chunker | Fallback only |
| unknown | sliding_window_chunker | Fallback only |

Gaps:

- Non-Python code: no language-aware chunker; falls back to sliding window
- RST documents: markdown_chunker handles RST partially; a dedicated RST chunker would improve quality
- JSON/YAML structured data: no schema-aware chunker

---

## Research obligations

The Chunking Engineer maintains `docs/research/CHUNKING_RESEARCH.md` with:

- Trade-off analysis for each strategy
- Failure mode documentation
- Optimal chunk size recommendations by training objective
- Notes on new chunking strategies worth evaluating
