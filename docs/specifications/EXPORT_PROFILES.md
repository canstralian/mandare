# Export Profiles Specification

## Purpose

Define the four built-in export profile types and their field mapping, format, and filtering contracts.

## Profile types

| Profile | Use case | Primary format |
| --- | --- | --- |
| `sft` | Supervised fine-tuning | JSONL or Parquet |
| `dpo` | Direct preference optimization | JSONL or Parquet |
| `rag` | Retrieval-augmented generation corpus | Parquet or Arrow |
| `evaluation` | Evaluation benchmark | JSONL |

## SFT profile

Produces prompt/completion pairs or instruction-following conversations.

### Input

`DatasetChunk` records with `content_type` in `{code, document, conversation}`.

### Output schema

Prompt-completion format:

```json
{"prompt": "...", "completion": "..."}
```

Conversation format (when source is `content_type=conversation`):

```json
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

### Config

```yaml
# configs/profiles/sft.yaml
id: sft
name: Supervised Fine-Tuning
format: jsonl
profile_type: sft
field_mapping:
  prompt: text                   # for code/document records
  completion: null               # null = single-turn; populated downstream
  messages: messages             # for conversation records
filters:
  - exclude_content_type: [trace, structured]
min_quality_score: 0.60
max_token_count: 4096
min_token_count: 16
permit_review_required: false
license_requirements:
  permitted_tiers: [permissive, copyleft_weak]
  non_commercial_permitted: false
```

## DPO profile

Produces chosen/rejected pairs for preference learning.

### Input

`DatasetChunk` records from datasets that contain explicit preference signals (ranked completions, human preference labels, reward scores).

### Output schema

```json
{
  "prompt": "...",
  "chosen": "...",
  "rejected": "..."
}
```

Or with full conversation format:

```json
{
  "prompt": [{"role": "user", "content": "..."}],
  "chosen": [{"role": "assistant", "content": "..."}],
  "rejected": [{"role": "assistant", "content": "..."}]
}
```

### Requirements

DPO records require a `preference_pair` annotation on the chunk. The annotation must contain `chosen` and `rejected` fields. Chunks without this annotation are excluded.

### Config

```yaml
id: dpo
name: Direct Preference Optimization
format: jsonl
profile_type: dpo
field_mapping:
  prompt: prompt
  chosen: chosen
  rejected: rejected
filters:
  - require_annotation: preference_pair
min_quality_score: 0.65
permit_review_required: false
license_requirements:
  permitted_tiers: [permissive]
  non_commercial_permitted: false
```

## RAG profile

Produces a retrieval corpus: documents with metadata for embedding and indexing.

### Input

`DatasetChunk` records with `content_type` in `{document, code}`. High chunk density (smaller chunks) preferred.

### Output schema

```json
{
  "id": "chunk-id",
  "text": "...",
  "metadata": {
    "source_id": "...",
    "content_type": "document",
    "token_count": 256,
    "quality_score": 0.82
  }
}
```

### Config

```yaml
id: rag
name: Retrieval-Augmented Generation Corpus
format: parquet
profile_type: rag
field_mapping:
  id: id
  text: text
  source_id: source_id
  content_type: content_type
  token_count: token_count
  quality_score: quality_score
filters:
  - exclude_content_type: [trace]
min_quality_score: 0.55
max_token_count: 512              # smaller chunks preferred for retrieval
min_token_count: 32
permit_review_required: false
license_requirements:
  permitted_tiers: [permissive, copyleft_weak]
```

## Evaluation profile

Produces a benchmark dataset: input + expected output + metadata for evaluation harness use.

### Input

`DatasetChunk` records from datasets with ground-truth annotations (expected answers, reference completions, test cases).

### Output schema

```json
{
  "id": "chunk-id",
  "input": "...",
  "expected_output": "...",
  "metadata": {
    "task_type": "code_completion",
    "difficulty": "medium",
    "source_id": "..."
  }
}
```

### Config

```yaml
id: evaluation
name: Evaluation Benchmark
format: jsonl
profile_type: evaluation
field_mapping:
  id: id
  input: prompt
  expected_output: completion
  task_type: task_type
  difficulty: difficulty
  source_id: source_id
filters:
  - require_annotation: ground_truth
min_quality_score: 0.70           # higher threshold for eval data
permit_review_required: false
license_requirements:
  permitted_tiers: [permissive]
  non_commercial_permitted: false
```

## Custom profiles

Custom profiles extend a built-in profile type:

```yaml
id: my_custom_sft
name: Custom SFT (internal)
extends: sft
format: jsonl
field_mapping:
  prompt: instruction
  completion: response
min_quality_score: 0.75
```

Fields not specified in a custom profile inherit from the base profile.

## HuggingFace export

Any profile may target HuggingFace Hub as the export destination:

```yaml
format: huggingface
hf_repo_id: my-org/my-dataset
hf_private: true
hf_commit_message: "Dataset build v1.2.0"
```

Publishing to HuggingFace Hub is an effectful operation (PUBLISH). It is governed and requires an explicit policy decision before execution.
