# CLI Reference

Binary entrypoint: `rif` (see `src/rif_runtime/cli.py`).

Run `rif --help` or `rif <command> --help` for the authoritative flag list and
examples. Usage and validation errors print `error: …` on stderr and exit
non-zero. Policy decisions from `rif check` always exit `0` (allow and deny);
the decision is in the JSON on stdout.

## Commands

### serve

Run the FastAPI policy API via uvicorn.

```bash
rif serve
rif serve --host 0.0.0.0 --port 8000
rif serve --no-reload
```

`--reload` is the default (interactive development). Prefer `--no-reload` for
scripted or agent-driven runs so the server is a single killable process.

### check

Evaluate one policy request without starting a server. Prints a
`PolicyDecision` as JSON.

```bash
rif check <actor> <action> <target>
rif check agent:test http.request https://api.anthropic.com/v1/messages
rif check agent:test http.request https://blocked.example.com
```

Network actions checked against `allowed_hosts`: `api.call`, `http.request`,
`mcp.invoke`, `package.install`.

### replay

Rebuild graph/posture summary from a `decisions.jsonl` **file path** (not an
execution id). Prints a recovered-state dict.

```bash
rif replay
rif replay data/decisions.jsonl
```

Missing files and invalid JSONL lines exit with `error: …` on stderr.

### msf-check

Evaluate a Metasploit MCP intent under a governance mode. Prints decision JSON
then evidence JSON.

```bash
rif msf-check <capability> <target>
rif msf-check auxiliary/scanner/http/http_version https://lab.example.com
rif msf-check exploit/unix/ftp/vsftpd_234_backdoor https://lab.example.com --mode shadow
```

Governance modes: `read_only_firewall`, `shadow`, `lab_broker`.

### status

Print a local JSON summary: environment, live posture, persisted counts, and
recovered state from `data/decisions.jsonl`.

```bash
rif status
```

Read-only with respect to policy mutation; uses the same local `data/` paths as
the API.

## Planned (v1.0 demo CLI — not yet implemented)

Authoritative design: [cli-v1-spec.md](cli-v1-spec.md).

Target commands: `rif run`, `rif replay` (run id), `rif verify`, `rif inspect`,
`rif policy`, `rif evidence`, plus global `--json` / CI exit codes (`0–5`).

Until that surface ships, the commands below remain **unimplemented** on the
current binary (do not confuse with today’s `rif replay` file-path command):

- `rif run` / `rif verify` / `rif inspect` / `rif policy` / `rif evidence`
- Global flags such as `--json`, `--verbose`, `--profile`, `--offline`
