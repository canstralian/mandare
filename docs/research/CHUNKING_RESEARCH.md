# Chunking Research

## Purpose

Research notes on chunking strategies, their trade-offs, and their fit for different training objectives.

## What chunking optimizes for

The optimal chunk is determined by the downstream training objective:

| Objective | Optimal chunk | Key constraint |
| --- | --- | --- |
| SFT (code) | A complete, runnable function or class | Must include docstring and signature |
| SFT (instruction) | A single instruction/response exchange | Must fit in context window |
| DPO | A complete response + its alternative | Both candidates must be from the same prompt |
| RAG (retrieval) | A topically coherent passage | Short enough for dense retrieval (128-512 tokens) |
| RAG (generation) | A passage with enough context to answer a question | Longer acceptable (512-2048 tokens) |
| Evaluation | A complete problem + solution | Must be self-contained |

## Code chunking

### AST-based (recommended for Python)

Chunk at function/class boundaries. Produces semantically meaningful units that correspond to how code is reasoned about.

Strengths:
- Chunks are syntactically complete (parseable)
- Natural boundary for code generation training
- Docstrings stay with their functions

Weaknesses:
- Python-only (current implementation)
- Long functions or classes exceed token limits
- Module-level code without functions is chunked poorly

### Sliding window (fallback)

Character or token-based window with overlap. No semantic awareness.

Use only as fallback when AST parsing fails.

Weaknesses:
- Splits within functions and classes
- Overlap duplicates content and adds noise
- Poor fit for code generation training

### Line-based

Split on blank lines or specific patterns (e.g., `def ` or `class `).

Simpler than AST but more robust across languages. Reasonable for non-Python code until language-specific chunkers are implemented.

## Document chunking

### Heading-based (recommended for Markdown/RST)

Split at heading boundaries. Produces self-contained sections.

Strengths:
- Preserves document structure
- Sections are typically topically coherent
- Works well for both SFT and RAG

Weaknesses:
- Sections vary widely in length
- Very short sections (e.g., stub headings) produce low-quality chunks
- Documents without headings fall back to sliding window

### Sentence-based

Split at sentence boundaries (`.`, `?`, `!` + whitespace).

Better than sliding window for RAG. Weak for SFT (sentences are rarely complete training examples).

### Paragraph-based

Split at double newlines. A reasonable middle ground for prose documents.

## Conversation chunking

### Turn-based (recommended)

Chunk at user-turn boundaries. Each chunk is one complete exchange: system prompt (optional) + user turn + assistant response(s).

Strengths:
- Natural training unit for instruction-following
- Preserves turn structure

Weaknesses:
- Multi-turn conversations must be sliced; earlier context is lost
- Very long turns exceed token limits

### Session-based

Include multiple exchanges per chunk to preserve context.

Better for learning from long dialogues. Worse for instruction-following where each exchange should stand alone.

## Overlap

Overlap (repeating trailing tokens from the previous chunk in the next) is commonly used for RAG corpora to ensure queries that fall near chunk boundaries are still retrievable.

For SFT and DPO, overlap is counterproductive: it introduces near-duplicate training examples and inflates dataset size without adding information.

Recommendation:
- RAG: `overlap_tokens: 50-100`
- SFT/DPO/Evaluation: `overlap_tokens: 0`

## Optimal chunk size by objective

Based on research on retrieval and generation quality:

| Objective | Recommended token range | Rationale |
| --- | --- | --- |
| RAG (retrieval) | 64–256 | Shorter = more precise retrieval |
| RAG (generation) | 256–512 | Enough context for generation |
| SFT | 64–2048 | Constrained by model context window |
| DPO | 128–4096 | Pairs must fit together in context |
| Evaluation | 32–2048 | Problem + solution must fit |

## Quality signals by content type

The heuristic scorer weights differ by content type:

| Signal | Code | Conversation | Document | Trace |
| --- | --- | --- | --- | --- |
| Well-formedness | High | Low | Low | Medium |
| Repetition | Medium | Medium | High | Low |
| Length within range | High | Medium | Medium | High |
| Compression ratio | Low | Medium | High | Low |
| Language detection | N/A | Medium | High | N/A |

## Known chunking failure modes

1. **Code with no function definitions**: AST chunker falls through to sliding window. Mitigate with a minimum function density check before applying AST chunker.

2. **Long docstrings in classes**: The class body chunk can be very large if the class has a multi-page docstring. Mitigate with `max_chunk_tokens` enforcement.

3. **Conversation records with very long system prompts**: System prompt prepended to every chunk bloats the token count. Mitigate by trimming system prompts over a configurable length threshold.

4. **Markdown with deeply nested headers**: Heading-based chunker respects `max_depth`. Content under deeply nested headers collapses into the parent chunk, which can become oversized.

5. **Non-UTF-8 source data**: Chunk IDs are SHA-256 of the text encoded as UTF-8. Non-UTF-8 content must be decoded to a consistent encoding before chunking.
