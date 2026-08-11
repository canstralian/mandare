# Dataset Survey

## Purpose

Survey of source datasets relevant to the Dataset Foundry pipeline, organized by content type and training objective.

## Code datasets

| Dataset | HF ID | License | Content type | Notes |
| --- | --- | --- | --- | --- |
| CodeAlpaca-20k | sahil2801/CodeAlpaca-20k | Apache-2.0 | conversation | Instruction-following, code generation |
| The Stack | bigcode/the-stack | Custom (RAIL) | code | Large-scale source code; per-language subsets available |
| The Stack v2 | bigcode/the-stack-v2 | Custom (RAIL) | code | Improved filtering vs v1 |
| CodeSearchNet | code_search_net | CCO-1.0 | code | Code + docstring pairs; 6 languages |
| MBPP | google-research-datasets/mbpp | CC-BY-4.0 | code | Python programming problems + solutions |
| HumanEval | openai_humaneval | MIT | code | Function completion benchmark |
| CommitPackFT | bigcode/commitpackft | Custom | code | Code commits with messages |

## Conversation / instruction datasets

| Dataset | HF ID | License | Content type | Notes |
| --- | --- | --- | --- | --- |
| OpenOrca | Open-Orca/OpenOrca | MIT | conversation | GPT-4/3.5 augmented reasoning chains |
| Alpaca | tatsu-lab/alpaca | Apache-2.0 | conversation | Self-instruct generated |
| ShareGPT | anon8231489123/ShareGPT_Vicuna_unfiltered | Apache-2.0 | conversation | Multi-turn ChatGPT conversations |
| UltraChat | stingning/ultrachat | CC-BY-NC-4.0 | conversation | Multi-turn chat; NC license |
| Dolly | databricks/databricks-dolly-15k | CC-BY-SA-3.0 | conversation | Human-written instruction data |
| FLAN | google/flan | Apache-2.0 | conversation | Instruction tuning collection |

## Document / knowledge datasets

| Dataset | HF ID | License | Content type | Notes |
| --- | --- | --- | --- | --- |
| RedPajama | togethercomputer/RedPajama-Data-1T | Various | document | Large-scale text; mixed licenses |
| C4 | allenai/c4 | ODC-BY | document | Cleaned Common Crawl |
| Wikipedia | wikimedia/wikipedia | CC-BY-SA-4.0 | document | Copyleft; attribution required |
| ArXiv | ArXiv papers | CC-BY / arXiv | document | Research papers; verify per-paper license |
| Books3 | books3 | Custom | document | Do not use without legal review |

## Agent trace / tool-use datasets

| Dataset | HF ID | License | Content type | Notes |
| --- | --- | --- | --- | --- |
| ToolBench | ToolBench/ToolBench | Apache-2.0 | trace | Tool-use traces, REST API calls |
| AgentInstruct | THUDM/AgentInstruct | Apache-2.0 | trace | Multi-step agent tasks |
| APIBench | gorilla-llm/APIBench | Apache-2.0 | trace | API call prediction |

## Preference / alignment datasets

| Dataset | HF ID | License | Content type | Notes |
| --- | --- | --- | --- | --- |
| Anthropic HH-RLHF | Anthropic/hh-rlhf | MIT | conversation | Human preference pairs (helpful/harmful) |
| SHP | stanfordnlp/SHP | CC-BY-4.0 | conversation | Reddit-sourced preference data |
| UltraFeedback | openbmb/UltraFeedback | MIT | conversation | GPT-4 preference scores |
| PKU-SafeRLHF | PKU-Alignment/PKU-SafeRLHF | CC-BY-NC-4.0 | conversation | Safety preference data; NC license |

## Evaluation / benchmark datasets

| Dataset | HF ID | License | Content type | Notes |
| --- | --- | --- | --- | --- |
| MMLU | cais/mmlu | MIT | structured | Massive Multitask Language Understanding |
| GSM8K | openai/gsm8k | MIT | structured | Math word problems |
| HellaSwag | Rowan/hellaswag | MIT | structured | Commonsense NLI |
| HumanEval | openai_humaneval | MIT | code | Code correctness benchmark |
| MBPP | google-research-datasets/mbpp | CC-BY-4.0 | code | Python problems |

## Selection criteria

When selecting datasets for a build, consider:

1. **License compatibility** with the export profile (see `docs/specifications/LICENSE_POLICY.md`)
2. **Quality signal**: datasets with known quality issues require higher `min_quality_score` thresholds
3. **Content type coverage**: ensure coverage of relevant content types for the training objective
4. **Deduplication overlap**: datasets derived from the same upstream source (e.g., Alpaca-derived datasets) will have high duplicate rates
5. **Size vs. quality trade-off**: a smaller, high-quality dataset often outperforms a larger, noisy one

## Flagged datasets

The following datasets require additional review before use:

| Dataset | Reason |
| --- | --- |
| Books3 | License unclear; potential copyright issues |
| ShareGPT | Contains real user data; privacy considerations |
| Any GPT-4-generated dataset | OpenAI ToS prohibits using outputs to train competing models; verify use case |
| UltraChat | CC-BY-NC; incompatible with commercial SFT profiles |
| PKU-SafeRLHF | CC-BY-NC; incompatible with commercial DPO profiles |

Do not add flagged datasets to the registry without a documented legal review.
