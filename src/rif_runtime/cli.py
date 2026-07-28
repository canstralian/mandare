from __future__ import annotations

import typer
import uvicorn
from rich import print

from .runtime import RIFRuntime
from .replay import ReplayEngine
from .schemas import PolicyRequest
from .mcp.metasploit import GovernanceMode, MetasploitIntent

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
    decisions_path: str = typer.Argument(
        "data/decisions.jsonl",
        help="Path to a decisions.jsonl log to rebuild graph and posture from.",
    ),
) -> None:
    # Positional, matching the documented `rif replay [decisions_path]`.
    state = ReplayEngine(decisions_path).recover()
    print(state.as_dict())


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


# Must stay last: Typer registers commands at decoration time, so invoking
# app() above this point would expose only the commands defined before it
# (that is how `python -m rif_runtime.cli` lost `replay` and `msf-check`).
if __name__ == "__main__":
    app()
