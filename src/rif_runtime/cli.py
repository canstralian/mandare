import typer
import uvicorn
from rich import print

from .runtime import RIFRuntime
from .replay import ReplayEngine
from .schemas import PolicyRequest

app = typer.Typer()


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run("rif_runtime.api:app", host=host, port=port, reload=True)


@app.command()
def check(actor: str, action: str, target: str):
    r = RIFRuntime()
    print(
        r.evaluate(
            PolicyRequest(actor=actor, action=action, target=target)
        ).model_dump_json(indent=2)
    )


if __name__ == "__main__":
    app()


@app.command()
def replay(decisions_path: str = "data/decisions.jsonl"):
    state = ReplayEngine(decisions_path).recover()
    print(state.__dict__)
