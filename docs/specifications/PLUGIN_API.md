# Plugin API Specification

## Purpose

Define the plugin interface for extending the Dataset Foundry pipeline with custom loaders, chunkers, quality scorers, and exporters.

## Design principle

The plugin API is narrow. Plugins extend one extension point at a time. A plugin cannot modify pipeline control flow, bypass governance, or mutate manifests.

## Extension points

| Extension point | Protocol | Config type |
| --- | --- | --- |
| Loader | `Loader` | `LoaderConfig` |
| Chunker | `Chunker` | `ChunkerConfig` |
| Quality scorer | `Scorer` | `ScorerConfig` |
| Exporter | `Exporter` | `ExporterConfig` |
| Classifier | `Classifier` | `ClassifierConfig` |

## Plugin registration

Plugins are registered in the relevant config file with `type: plugin` and a Python import path:

```yaml
# configs/chunkers/my_custom_chunker.yaml
chunker_id: my_custom_chunker
type: plugin
import_path: my_package.chunkers.MyCustomChunker
max_chunk_tokens: 1024
min_chunk_tokens: 32
```

The import path must be importable in the pipeline's Python environment. The class at the import path must implement the declared protocol.

## Loader protocol

```python
class Loader(Protocol):
    loader_id: str
    config: LoaderConfig

    def load(
        self,
        entry: DatasetRegistryEntry,
        context: BuildContext,
    ) -> Iterable[DatasetRecord]:
        ...
```

The loader must call `context.governance.evaluate(...)` before any network or filesystem read. It must not cache results across calls.

## Chunker protocol

```python
class Chunker(Protocol):
    chunker_id: str
    config: ChunkerConfig

    def chunk(self, record: DatasetRecord) -> list[DatasetChunk]:
        ...
```

The chunker is pure. It must not perform I/O.

## Scorer protocol

```python
class Scorer(Protocol):
    scorer_id: str
    config: ScorerConfig

    def score(
        self,
        chunk: DatasetChunk,
        context: BuildContext,
    ) -> float:
        ...
```

If the scorer requires network access, it must call `context.governance.evaluate(...)` first. The return value is in [0, 1].

## Exporter protocol

```python
class Exporter(Protocol):
    exporter_id: str
    config: ExporterConfig

    def export(
        self,
        chunks: Iterable[DatasetChunk],
        profile: DatasetExportProfile,
        manifest: DatasetManifest,
        context: BuildContext,
    ) -> ExportArtifactRecord:
        ...
```

The exporter must call `context.governance.evaluate(...)` before any write or publish operation.

## Classifier protocol

```python
class Classifier(Protocol):
    classifier_id: str
    config: ClassifierConfig

    def classify(self, record: DatasetRecord) -> ContentType:
        ...
```

The classifier is pure. It must not perform I/O.

## Plugin governance requirements

Plugins that perform I/O must:

1. Accept a `BuildContext` parameter.
2. Call `context.governance.evaluate(request)` before every I/O operation.
3. Raise `GovernanceDenied` if the decision is `deny`.
4. Record the governance decision in their output metadata or stage report.

Plugins that do not perform I/O have no governance requirements.

## Plugin config base classes

All plugin configs extend the base config for their extension point:

```python
class MyChunkerConfig(ChunkerConfig):
    chunker_id: str = "my_custom_chunker"
    my_custom_field: str = "default"
```

Plugin configs are validated by Pydantic at pipeline startup. Invalid configs fail fast.

## Plugin isolation

Plugins run in the same process as the pipeline. There is no sandbox. A plugin that raises an unhandled exception halts the build.

Plugin authors are responsible for:

- Not modifying shared pipeline state
- Not bypassing governance
- Not caching mutable state across calls
- Handling errors gracefully and raising standard pipeline exceptions

## Plugin versioning

Plugin version is tracked via the config file:

```yaml
chunker_id: my_custom_chunker
type: plugin
import_path: my_package.chunkers.MyCustomChunker
plugin_version: "1.2.0"
```

`plugin_version` is recorded in the `DatasetManifest` as part of the pipeline configuration. Changing the version without changing behavior is a no-op for reproducibility purposes. Changing behavior without bumping the version is a reproducibility violation.

## Writing a plugin

1. Implement the relevant protocol in your package.
2. Add a config file under the appropriate `configs/` directory.
3. Add the package to the pipeline's dependencies.
4. Write tests verifying the protocol contract.
5. Document the plugin in `docs/tools/<id>.md`.

Plugin documentation must specify:

- Extension point
- Input and output types
- I/O requirements and governance calls
- Configuration fields
- Failure modes
- Known limitations
