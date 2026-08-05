# Plugin Architecture

## Design

Plugins are Python classes that implement a typed protocol. The pipeline discovers them at startup from configuration. They run in-process.

There is no plugin runtime isolation. Plugins are trusted components, not sandboxed extensions.

## Discovery

At startup, `ConfigurationEngine` reads all config files with `type: plugin` and constructs a `PluginRegistry`:

```python
class PluginRegistry:
    def __init__(self, configs: list[PluginConfig]) -> None: ...

    def get_loader(self, loader_id: str) -> Loader: ...
    def get_chunker(self, chunker_id: str) -> Chunker: ...
    def get_scorer(self, scorer_id: str) -> Scorer: ...
    def get_exporter(self, exporter_id: str) -> Exporter: ...
    def get_classifier(self, classifier_id: str) -> Classifier: ...
```

Each `get_*` method imports the class at the configured `import_path`, validates that it implements the declared protocol, and instantiates it with the config.

Discovery failures (import errors, protocol violations, config validation errors) are fatal at startup.

## Protocol checking

Protocol compliance is checked structurally (Python `isinstance` with `runtime_checkable` Protocol classes):

```python
@runtime_checkable
class Chunker(Protocol):
    chunker_id: str
    config: ChunkerConfig

    def chunk(self, record: DatasetRecord) -> list[DatasetChunk]: ...
```

If the imported class does not implement the protocol, `PluginRegistry` raises `PluginProtocolError` at startup with the class name and the missing attributes.

## Config injection

Plugin configs are typed Pydantic models. The `ConfigurationEngine` validates the YAML config against the expected model before the plugin is instantiated:

```python
class PluginConfig(BaseModel):
    chunker_id: str
    type: Literal["plugin"]
    import_path: str              # e.g. "my_package.chunkers.MyChunker"
    plugin_version: str
    model_config = ConfigDict(extra="allow")  # extra fields passed to plugin config
```

The plugin's `__init__` receives the full config dict. The plugin is responsible for defining and validating its own config fields.

## Lifecycle

```
Pipeline startup
    │
    ▼
ConfigurationEngine.load()
    │
    ├── Read all configs/plugins/*.yaml
    ├── Validate each PluginConfig
    ├── Import class at import_path
    ├── Check protocol compliance
    └── Instantiate with config
    │
    ▼
PluginRegistry ready
    │
    ▼
Pipeline.run()
    │
    ▼
Stages call PluginRegistry.get_*(id)
    │
    ▼
Plugin method called
    │
    ▼
Result returned to stage
```

Plugin instances are created once at startup and reused across pipeline runs. Plugins must be safe for repeated calls.

## Built-in vs plugin

Built-in components (e.g., `ASTChunker`, `HeuristicScorer`) are registered in the same `PluginRegistry` with `type: builtin`. The distinction is internal; all components are retrieved through the same `get_*` interface.

Built-ins have `import_path: rif_runtime.dataset.chunkers.ast.ASTChunker` (or equivalent). The `type: builtin` tag is purely informational.

## Adding a plugin to the pipeline

1. Implement the protocol in your package.
2. Create `configs/plugins/<id>.yaml` with `type: plugin` and your import path.
3. Ensure your package is installed in the pipeline environment.
4. Run `rif-dataset validate-config` to verify discovery and protocol compliance.
5. Reference the plugin ID in the relevant pipeline config (e.g., `chunker_map.code: my_custom_chunker`).

## Governance in plugins

Plugins that perform I/O must accept `context: BuildContext` and call `context.governance.evaluate(...)`.

The pipeline passes `BuildContext` to all plugin methods that declare it as a parameter. Methods that do not declare it receive only their data arguments.

A plugin that performs I/O without calling governance is a violation of the platform contract. The pipeline cannot detect this at runtime; it is enforced through code review and the Plugin Architecture review checklist.

## Plugin review checklist

Before merging a plugin:

- [ ] Protocol compliance verified (`validate-config` passes)
- [ ] All I/O calls route through `context.governance.evaluate()`
- [ ] Config fields are validated by a Pydantic model
- [ ] `plugin_version` is set
- [ ] Tests cover the protocol contract
- [ ] Tool documentation exists in `docs/tools/<id>.md`
- [ ] No mutable shared state between calls
