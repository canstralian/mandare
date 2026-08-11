# CLI Reference

> **Note:** Most commands described here (`execute`, `evidence`, `telemetry`, `validate`,
> `policy`) are **planned** and not yet implemented. The current CLI commands are
> `rif serve`, `rif check <actor> <action> <target>`, `rif replay [decisions_path]`,
> and `rif msf-check <capability> <target>` — see `src/rif_runtime/cli.py`.
> `rif replay` takes a file path, not an execution ID. Global flags are also planned.

## Binary

```bash
rif
```

## Execute

```bash
rif execute --intent "hello"
```

## Replay

```bash
rif replay exec_123
```

## Evidence

```bash
rif evidence export exec_123 bundle.zip
```

## Telemetry

```bash
rif telemetry tail
```

## Validate

```bash
rif validate config runtime.yaml
```

## Policy

```bash
rif policy check request.json
```

## Global Flags

- --config
- --json
- --verbose
- --profile
- --offline
