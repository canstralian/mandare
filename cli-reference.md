# CLI Reference

The canonical current CLI reference is [`docs/cli-reference.md`](docs/cli-reference.md).

The implementation source of truth is `src/mandare/cli.py`.

Current commands:

```text
rif serve
rif check <actor> <action> <target>
rif replay [decisions_path]
rif msf-check <capability> <target> [--mode ...] [--actor ...] [--scope-id ...]
```

Older `rif execute`, `rif evidence`, `rif telemetry`, `rif validate`, and `rif policy` examples are historical/planned and are not current commands.
