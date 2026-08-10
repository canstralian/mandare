from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, NoReturn

import typer
import uvicorn
from rich import print

from .mcp.metasploit import GovernanceMode, MetasploitIntent
from .policy import NETWORK_ACTIONS
from .replay import ReplayDecodeError, ReplayEngine
from .runtime import RIFRuntime
from .schemas import PolicyRequest

_NETWORK_ACTIONS_HELP = ", ".join(sorted(NETWORK_ACTIONS))
_GOVERNANCE_MODES_HELP = ", ".join(m.value for m in GovernanceMode)

app = typer.Typer(
    help="Governed agent runtime: evaluate policy, serve the API, replay decisions.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _die(message: str, code: int = 1) -> NoReturn:
    # Use typer.secho (not rich.print) so paths are not soft-wrapped mid-string.
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


@app.command(
    help="Run the FastAPI policy API (uvicorn).",
    epilog=(
        "Examples:\n"
        "  rif serve\n"
        "  rif serve --host 0.0.0.0 --port 8000\n"
        "  rif serve --no-reload"
    ),
)
def serve(
    host: Annotated[
        str,
        typer.Option(help="Bind host"),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(help="Bind port"),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option(
            "--reload/--no-reload",
            help=(
                "Enable auto-reload (default on for interactive use). "
                "Use --no-reload for scripted or agent-driven runs so the "
                "server is a single killable process."
            ),
        ),
    ] = True,
) -> None:
    uvicorn.run("rif_runtime.api:app", host=host, port=port, reload=reload)


@app.command(
    help="Evaluate one policy request (no server required).",
    epilog=(
        "Examples:\n"
        "  rif check agent:test http.request "
        "https://api.anthropic.com/v1/messages\n"
        "  rif check agent:test http.request https://blocked.example.com\n"
        "\n"
        f"Network actions (host checked against allowed_hosts): {_NETWORK_ACTIONS_HELP}"
    ),
)
def check(
    actor: Annotated[
        str,
        typer.Argument(help="Acting agent id, e.g. agent:test"),
    ],
    action: Annotated[
        str,
        typer.Argument(
            help=(
                "Action name. Network actions "
                f"({_NETWORK_ACTIONS_HELP}) are checked against allowed_hosts."
            ),
        ),
    ],
    target: Annotated[
        str,
        typer.Argument(help="Target URL, host, or resource"),
    ],
) -> None:
    r = RIFRuntime()
    print(
        r.evaluate(
            PolicyRequest(actor=actor, action=action, target=target)
        ).model_dump_json(indent=2)
    )


@app.command(
    help="Rebuild graph/posture summary from a decisions.jsonl.",
    epilog=(
        "Examples:\n"
        "  rif replay\n"
        "  rif replay data/decisions.jsonl\n"
        "\n"
        "The path is a decisions.jsonl file, not an execution id."
    ),
)
def replay(
    decisions_path: Annotated[
        str,
        typer.Argument(help="Path to decisions.jsonl"),
    ] = "data/decisions.jsonl",
) -> None:
    path = Path(decisions_path)
    if not path.exists():
        _die(f"decisions file not found: {path}")
    try:
        state = ReplayEngine(str(path)).recover()
    except ReplayDecodeError as exc:
        _die(str(exc))
    if state.historical_decisions == 0:
        typer.secho(
            f"note: decisions file is empty: {path}",
            fg=typer.colors.YELLOW,
            err=True,
        )
    print(state.__dict__)


@app.command(
    "msf-check",
    help="Evaluate a Metasploit MCP intent under a governance mode.",
    epilog=(
        "Examples:\n"
        "  rif msf-check auxiliary/scanner/http/http_version "
        "https://lab.example.com\n"
        "  rif msf-check exploit/unix/ftp/vsftpd_234_backdoor "
        "https://lab.example.com --mode shadow\n"
        "\n"
        f"Governance modes: {_GOVERNANCE_MODES_HELP}"
    ),
)
def msf_check(
    capability: Annotated[
        str,
        typer.Argument(help="Metasploit module/capability name"),
    ],
    target: Annotated[
        str,
        typer.Argument(help="Target URL or host"),
    ],
    mode: Annotated[
        str,
        typer.Option(
            help=f"Governance mode. One of: {_GOVERNANCE_MODES_HELP}",
        ),
    ] = "read_only_firewall",
    actor: Annotated[
        str,
        typer.Option(help="Acting agent id"),
    ] = "agent:metasploit",
    scope_id: Annotated[
        str,
        typer.Option(help="Scope identifier for the intent"),
    ] = "unscoped",
) -> None:
    try:
        governance_mode = GovernanceMode(mode)
    except ValueError:
        _die(f"unknown mode {mode!r}; expected one of: {_GOVERNANCE_MODES_HELP}")
    r = RIFRuntime()
    intent = MetasploitIntent(
        actor=actor, capability=capability, target=target, scope_id=scope_id
    )
    outcome = r.evaluate_metasploit(intent, mode=governance_mode)
    print(outcome.decision.model_dump_json(indent=2))
    print(outcome.evidence.model_dump_json(indent=2))


@app.command(
    help="Print a local runtime status summary (JSON).",
    epilog=(
        "Examples:\n"
        "  rif status\n"
        "\n"
        "Read-only summary of environment, live posture, persisted counts, "
        "and recovered state from decisions.jsonl. Constructing the runtime "
        "uses the same local data/ paths as the API."
    ),
)
def status() -> None:
    r = RIFRuntime()
    try:
        recovered = asdict(ReplayEngine().recover())
    except ReplayDecodeError as exc:
        _die(str(exc))
    payload = {
        "environment": r.environment_name,
        "posture": r.posture.value,
        "persisted": r.persisted_summary(),
        "recovered": recovered,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    app()
