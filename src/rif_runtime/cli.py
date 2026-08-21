import typer
import uvicorn
from rich import print

from .mcp.metasploit import GovernanceMode, MetasploitIntent
from .replay import ReplayEngine
from .runtime import RIFRuntime
from .schemas import PolicyRequest

app = typer.Typer()


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Restart the server when source files change (development only).",
    ),
) -> None:
    """Run the HTTP API.

    Auto-reload is off by default. It used to be unconditional, which meant
    the start command the README documents spawned uvicorn's file-watching
    reloader in production.
    """
    uvicorn.run("rif_runtime.api:app", host=host, port=port, reload=reload)


@app.command()
def check(actor: str, action: str, target: str) -> None:
    r = RIFRuntime()
    print(
        r.evaluate(
            PolicyRequest(actor=actor, action=action, target=target)
        ).model_dump_json(indent=2)
    )


@app.command()
def replay(decisions_path: str = "") -> None:
    """Rebuild graph and posture state from a decisions log.

    Defaults to decisions.jsonl under the configured data directory
    (RIF_DATA_DIR, or [paths] data_dir in rif.toml).
    """
    state = ReplayEngine(decisions_path or None).recover()
    print(state.__dict__)


@app.command("msf-check")
def msf_check(
    capability: str,
    target: str,
    mode: str = "read_only_firewall",
    actor: str = "agent:metasploit",
    scope_id: str = "unscoped",
) -> None:
    r = RIFRuntime()
    intent = MetasploitIntent(
        actor=actor, capability=capability, target=target, scope_id=scope_id
    )
    outcome = r.evaluate_metasploit(intent, mode=GovernanceMode(mode))
    print(outcome.decision.model_dump_json(indent=2))
    print(outcome.evidence.model_dump_json(indent=2))


# Must stay last: Typer registers commands as the @app.command() decorators run,
# so calling app() above `replay`/`msf-check` left them off `python -m
# rif_runtime.cli` entirely (the `rif` console script was unaffected — it
# imports the module fully before calling app).
if __name__ == "__main__":
    app()
