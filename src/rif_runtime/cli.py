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


@app.command()
def replay(
    decisions_path: str = "data/decisions.jsonl",
    verify: bool = typer.Option(
        False,
        "--verify",
        help="Validate every row and confirm recover() is deterministic.",
    ),
) -> None:
    engine = ReplayEngine(decisions_path)
    if verify:
        report = engine.verify()
        print(report.as_dict())
        if report.invalid_rows or not report.deterministic:
            raise typer.Exit(code=1)
        return
    state = engine.recover()
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


if __name__ == "__main__":
    app()
