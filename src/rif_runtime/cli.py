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
    """Start the RIF Runtime API server on the specified host and port."""
    uvicorn.run("rif_runtime.api:app", host=host, port=port, reload=True)


@app.command()
def check(actor: str, action: str, target: str) -> None:
    """Evaluate a policy request and print the resulting decision as indented JSON.
    
    Parameters:
        actor (str): Identity requesting the action.
        action (str): Action to evaluate.
        target (str): Resource or target of the action.
    """
    r = RIFRuntime()
    print(
        r.evaluate(
            PolicyRequest(actor=actor, action=action, target=target)
        ).model_dump_json(indent=2)
    )


if __name__ == "__main__":
    app()


@app.command()
def replay(decisions_path: str = "data/decisions.jsonl") -> None:
    """
    Recover and print runtime state from a decisions file.
    
    Parameters:
    	decisions_path (str): Path to the decisions file used for state recovery.
    """
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
    """
    Evaluate a Metasploit capability request under the selected governance mode.
    
    Parameters:
        capability (str): Capability requested by the actor.
        target (str): Target associated with the request.
        mode (str): Governance mode used to evaluate the request.
        actor (str): Identity making the request.
        scope_id (str): Scope in which the request is evaluated.
    """
    r = RIFRuntime()
    intent = MetasploitIntent(
        actor=actor, capability=capability, target=target, scope_id=scope_id
    )
    outcome = r.evaluate_metasploit(intent, mode=GovernanceMode(mode))
    print(outcome.decision.model_dump_json(indent=2))
    print(outcome.evidence.model_dump_json(indent=2))
