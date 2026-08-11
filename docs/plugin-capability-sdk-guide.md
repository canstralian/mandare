# Plugin and Capability SDK Guide

> **Note:** The plugin SDK described here (`class Capability`, manifest YAML, lifecycle
> hooks) is **planned** and does not exist in the current codebase. This document
> describes the intended design for a future capability extension system.

## Goal

Provide a standard way to build runtime capabilities.

## Capability Lifecycle

- declare
- initialize
- authorize
- execute
- record
- teardown

## Example Manifest

```yaml
id: network.fetch
version: 1
risk: R2
```

## Python Skeleton

```python
class Capability:
    id = "example.echo"

    def execute(self, request):
        return {"echo": request}
```

## Required Behaviors

- deterministic request handling
- structured errors
- telemetry emission
- evidence recording
- timeout support

## Error Model

```json
{
  "error": "TIMEOUT",
  "message": "operation exceeded limit"
}
```

## Telemetry

Emit:

- duration_ms
- success
- retries
- bytes_in
- bytes_out

## Evidence Hook

Capabilities must return evidence-safe outputs.
