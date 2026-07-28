"""Execution engine adapters.

Each adapter implements `rif_runtime.execution.ExecutionEngine` for one
provider. Adapters import their SDK lazily and are installed as extras, so
`rif_runtime` itself never depends on a model vendor:

    pip install -e '.[foundry]'

Importing this package pulls in no provider SDK.
"""
