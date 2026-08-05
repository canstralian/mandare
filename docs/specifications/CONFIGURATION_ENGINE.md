# Configuration Engine Specification

## Core principle

Behavior belongs in configuration. Code executes configuration.

The pipeline does not branch on dataset identity, content type, or profile name in its core logic. It reads configuration and dispatches accordingly.

## Configuration hierarchy

```
configs/
  pipeline/
    default.yaml            # base pipeline configuration
    <name>.yaml             # named overrides (merged onto default)
  datasets/
    <id>.yaml               # DatasetRegistryEntry per dataset
  chunkers/
    <id>.yaml               # chunker configuration
  licenses/
    <id>.yaml               # license tier and compatibility rules
  profiles/
    sft.yaml
    dpo.yaml
    rag.yaml
    evaluation.yaml
    <custom>.yaml
  quality/
    <id>.yaml               # quality scorer configuration
  exporters/
    <id>.yaml               # exporter configuration
  plugins/
    <id>.yaml               # plugin registration and config
```

All files are YAML. All IDs are lowercase alphanumeric with hyphens.

## Configuration loading

The `ConfigurationEngine` loads all YAML files from `configs/` at startup:

1. Validates each file against its Pydantic schema.
2. Checks for duplicate IDs within each category.
3. Verifies all cross-references (e.g., `license_id` in a dataset entry references a valid `configs/licenses/` file).
4. Fails fast on any validation error.

Configuration is immutable once loaded. The pipeline does not reload configuration mid-run.

## Merge semantics

Named pipeline configurations merge onto the default:

```yaml
# configs/pipeline/default.yaml
loader_id: huggingface_loader
license_config_id: default_license_policy
normalizer_id: default_normalizer
classifier_id: heuristic_classifier
deduplicator_id: hash_deduplicator
chunker_map:
  code: ast_chunker
  conversation: conversation_chunker
  document: markdown_chunker
  trace: trace_chunker
  structured: sliding_window_chunker
  unknown: sliding_window_chunker
quality_scorer_id: heuristic_scorer
export_profile_id: sft
fail_on_license_incompatible: true
fail_on_quality_below: null
```

```yaml
# configs/pipeline/code_only.yaml
chunker_map:
  code: ast_chunker
quality_scorer_id: composite_scorer   # overrides default scorer
export_profile_id: sft
```

Merge is key-level: a key in the override replaces the same key in the default entirely. For nested dicts like `chunker_map`, only the specified keys are overridden; unspecified keys inherit from the default.

## Configuration schema validation

Every config file is validated against a Pydantic model at load time. Unknown keys raise a validation error (strict mode).

Validation is run by:

```bash
rif-dataset validate-config
```

CI runs this check on every PR that touches `configs/`.

## Referential integrity

Cross-file references are validated at load time:

| Field | Must reference |
| --- | --- |
| `DatasetRegistryEntry.license_id` | `configs/licenses/<id>.yaml` |
| `PipelineConfig.loader_id` | `configs/` (built-in or plugin) |
| `PipelineConfig.chunker_map.<type>` | `configs/chunkers/<id>.yaml` |
| `PipelineConfig.quality_scorer_id` | `configs/quality/<id>.yaml` |
| `PipelineConfig.export_profile_id` | `configs/profiles/<id>.yaml` |

Missing references fail at startup, not at runtime.

## Runtime configuration selection

The pipeline accepts a configuration name at runtime:

```bash
rif-dataset build --config code_only --dataset code-alpaca
```

`--config code_only` loads `configs/pipeline/code_only.yaml` and merges it onto `configs/pipeline/default.yaml`.

`--dataset code-alpaca` selects `configs/datasets/code-alpaca.yaml` as the source.

Multiple datasets may be combined:

```bash
rif-dataset build --config default --dataset code-alpaca,open-orca
```

Combined datasets produce a single build with a merged manifest. The composite license is the most restrictive of all sources.

## Environment variables

Configuration values may reference environment variables using `${VAR_NAME}` syntax:

```yaml
# configs/exporters/hf_exporter.yaml
hf_token: ${HF_TOKEN}
```

Environment variable references are resolved at load time. Missing required variables fail at startup.

Secrets must never be committed to config files. Use environment variable references.

## Adding a new configuration category

1. Create the directory under `configs/`.
2. Define a Pydantic schema for the config type.
3. Register the schema with `ConfigurationEngine`.
4. Add referential integrity checks if the config is referenced by other configs.
5. Document the schema in the relevant specification file.
6. Add validation to `rif-dataset validate-config`.
