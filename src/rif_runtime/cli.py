import typer
import uvicorn
from rich import print

from .mcp.metasploit import GovernanceMode, MetasploitIntent
from .replay import ReplayEngine
from .runtime import RIFRuntime
from .schemas import PolicyRequest

app = typer.Typer()


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    uvicorn.run("rif_runtime.api:app", host=host, port=port, reload=True)


@app.command()
def check(actor: str, action: str, target: str) -> None:
    r = RIFRuntime()
    print(
        r.evaluate(
            PolicyRequest(actor=actor, action=action, target=target)
        ).model_dump_json(indent=2)
    )


if __name__ == "__main__":
    app()


@app.command()
def replay(decisions_path: str | None = None) -> None:
    # None → ReplayEngine resolves via get_settings().paths.data_dir (RIF_DATA_DIR).
    state = ReplayEngine(decisions_path).recover()
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
