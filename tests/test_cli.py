"""CLI surface: the serve command's defaults are a deployment concern."""

from unittest.mock import patch

from typer.testing import CliRunner

from rif_runtime.cli import app

runner = CliRunner()


def test_serve_does_not_enable_reload_by_default():
    """`rif serve` is the README's start command; it must not auto-reload.

    Reload was previously hardcoded on, so the documented way to start the
    service spawned uvicorn's file-watching supervisor in production.
    """
    with patch("rif_runtime.cli.uvicorn.run") as run:
        result = runner.invoke(app, ["serve"])

    assert result.exit_code == 0, result.output
    assert run.call_args.kwargs["reload"] is False


def test_serve_reload_flag_enables_it():
    with patch("rif_runtime.cli.uvicorn.run") as run:
        result = runner.invoke(app, ["serve", "--reload"])

    assert result.exit_code == 0, result.output
    assert run.call_args.kwargs["reload"] is True


def test_serve_defaults_to_loopback():
    with patch("rif_runtime.cli.uvicorn.run") as run:
        runner.invoke(app, ["serve"])

    assert run.call_args.kwargs["host"] == "127.0.0.1"
    assert run.call_args.kwargs["port"] == 8000


def test_serve_passes_host_and_port_through():
    with patch("rif_runtime.cli.uvicorn.run") as run:
        runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "9001"])

    assert run.call_args.kwargs["host"] == "0.0.0.0"
    assert run.call_args.kwargs["port"] == 9001


def test_every_documented_command_is_registered():
    """CLAUDE.md and docs/cli-reference.md list these four."""
    registered = {
        command.name or command.callback.__name__ for command in app.registered_commands
    }

    assert {"serve", "check", "replay", "msf-check"} <= registered
