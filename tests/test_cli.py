"""CLI command registration and the replay command's output contract."""

import subprocess
import sys

from typer.main import get_command

from rif_runtime.cli import app

EXPECTED_COMMANDS = {"serve", "check", "replay", "msf-check"}


def test_every_command_is_registered():
    registered = set(get_command(app).commands)
    assert EXPECTED_COMMANDS <= registered


def test_module_entrypoint_exposes_every_command():
    # Regression: the `if __name__ == "__main__": app()` block sat above the
    # replay and msf-check definitions, so `python -m rif_runtime.cli` ran
    # Typer before those commands were decorated and silently omitted them.
    result = subprocess.run(
        [sys.executable, "-m", "rif_runtime.cli", "--help"],
        capture_output=True,
        text=True,
        env={"COLUMNS": "200", "PATH": "/usr/bin:/bin", "NO_COLOR": "1"},
    )
    assert result.returncode == 0, result.stderr
    for command in EXPECTED_COMMANDS:
        assert command in result.stdout


def test_replay_command_reports_recovered_state(tmp_path):
    log = tmp_path / "decisions.jsonl"
    log.write_text("", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "rif_runtime.cli", "replay", str(log)],
        capture_output=True,
        text=True,
        env={"COLUMNS": "200", "PATH": "/usr/bin:/bin", "NO_COLOR": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert "historical_decisions" in result.stdout
