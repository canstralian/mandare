from pathlib import Path

from typer.testing import CliRunner

from rif_runtime.cli import app

runner = CliRunner()


def _combined(result) -> str:
    return f"{result.stdout}{result.stderr}"


def test_root_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in ("check", "serve", "replay", "msf-check", "status"):
        assert name in result.stdout


def test_bare_invocation_prints_help() -> None:
    # Click's no_args_is_help prints help and exits 2 (missing command).
    result = runner.invoke(app, [])
    assert result.exit_code == 2
    assert "check" in result.stdout
    assert "serve" in result.stdout


def test_check_help_mentions_network_actions_and_examples() -> None:
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "http.request" in result.stdout
    assert "api.call" in result.stdout
    assert "rif check agent:test" in result.stdout


def test_msf_check_unknown_mode_lists_valid_modes() -> None:
    result = runner.invoke(
        app,
        [
            "msf-check",
            "auxiliary/scanner/http/http_version",
            "https://lab.example.com",
            "--mode",
            "not-a-mode",
        ],
    )
    assert result.exit_code != 0
    combined = _combined(result)
    assert "unknown mode" in combined
    assert "read_only_firewall" in combined
    assert "shadow" in combined
    assert "lab_broker" in combined
    assert "Traceback" not in combined


def test_replay_missing_file_errors(tmp_path: Path) -> None:
    missing = tmp_path / "missing-decisions.jsonl"
    result = runner.invoke(app, ["replay", str(missing)])
    assert result.exit_code != 0
    combined = _combined(result)
    assert "not found" in combined
    assert str(missing) in combined
    assert "Traceback" not in combined


def test_replay_invalid_jsonl_reports_path_and_line(tmp_path: Path) -> None:
    log = tmp_path / "decisions.jsonl"
    log.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")
    result = runner.invoke(app, ["replay", str(log)])
    assert result.exit_code != 0
    combined = _combined(result)
    assert "invalid JSONL" in combined
    assert ":2:" in combined
    assert "Traceback" not in combined


def test_replay_empty_file_notes_and_prints_zeros(tmp_path: Path) -> None:
    log = tmp_path / "decisions.jsonl"
    log.write_text("", encoding="utf-8")
    result = runner.invoke(app, ["replay", str(log)])
    assert result.exit_code == 0
    combined = _combined(result)
    assert "empty" in combined
    assert "historical_decisions" in result.stdout


def test_status_help_and_serve_reload_flag() -> None:
    status = runner.invoke(app, ["status", "--help"])
    assert status.exit_code == 0
    assert "JSON" in status.stdout

    serve = runner.invoke(app, ["serve", "--help"])
    assert serve.exit_code == 0
    assert "--no-reload" in serve.stdout
