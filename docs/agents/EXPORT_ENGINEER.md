# Export Engineer

## Mission

Own the export stage: output formats, field mapping, filtering, and publication governance.

---

## Responsibilities

- Exporter implementations (JSONL, Parquet, Arrow, HuggingFace)
- Export profile config schema
- Field mapping validation
- Publication governance (PUBLISH policy evaluation)
- Artifact integrity verification (hash computation, record count validation)
- Export performance (large dataset throughput)

---

## Exporter implementation checklist

Before merging an exporter:

- [ ] Exporter implements the `Exporter` protocol
- [ ] All write and publish operations route through `context.governance.evaluate()`
- [ ] Artifact hash (SHA-256) is computed and returned in `ExportArtifactRecord`
- [ ] Record count in `ExportArtifactRecord.record_count` matches actual written records
- [ ] Output format matches the profile's `format` and `field_mapping`
- [ ] Records below `min_quality_score` or with `license_status=incompatible` are excluded before writing
- [ ] Tests cover: empty input, single record, large batch, governance denial
- [ ] Documentation in `docs/tools/<name>_exporter.md`

---

## Governance requirements

Every exporter must evaluate governance before writing:

```python
decision = context.governance.evaluate(PolicyRequest(
    actor="pipeline.exporter",
    action="WRITE",    # or "PUBLISH" for HF Hub
    target=artifact_path,
))
if decision.decision == "deny":
    raise GovernanceDenied(stage="exporter", reason=decision.reason)
```

For HuggingFace Hub exports, the action is `PUBLISH` and the target is the HF repo ID.

A governance denial halts the export and records a `BuildFailureRecord`. The pipeline does not retry.

---

## Field mapping

Field mapping translates canonical `DatasetChunk` field names to the output field names required by the export profile:

```python
field_mapping = profile.field_mapping  # {"prompt": "instruction", "completion": "output"}

def apply_mapping(chunk: DatasetChunk, mapping: dict[str, str]) -> dict[str, Any]:
    result = {}
    for canonical_field, output_field in mapping.items():
        value = getattr(chunk, canonical_field, None)
        if value is not None:
            result[output_field] = value
    return result
```

Fields in `field_mapping` that are not present on the chunk are omitted (not null). Fields present on the chunk but not in `field_mapping` are excluded from the output.

---

## Artifact integrity

Every exporter must:

1. Stream-write the output (do not buffer all records in memory).
2. Compute the SHA-256 hash of the written file after writing.
3. Verify the file size matches the expected size (if available).
4. Return the hash in `ExportArtifactRecord.artifact_hash`.

The hash is used by `rif-dataset verify-build` to confirm artifact integrity.

---

## HuggingFace Hub exporter specifics

The HuggingFace Hub exporter:

1. Requires `HF_TOKEN` environment variable.
2. Evaluates a `PUBLISH` policy before pushing.
3. Creates a new dataset revision on push (never force-pushes).
4. Records the HF commit hash in `ExportArtifactRecord.metadata["hf_commit_hash"]`.
5. Verifies the pushed dataset has the expected record count before returning.

The HF token must never be committed to config files. It is read from the environment variable referenced in the exporter config.

---

## Profile validation

Before exporting, the exporter validates the profile's `field_mapping`:

- Every output field name in `field_mapping` must be a non-empty string.
- Every canonical field name in `field_mapping` must exist on `DatasetChunk` or `DatasetRecord`.
- If `profile.min_quality_score` is set, at least one chunk must survive the filter (empty export is an error, not a success).
