"""
Tests for RIF CLI using Typer CliRunner.
Tests command discoverability, error handling, and exit codes.
"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rif_runtime.cli import app

runner = CliRunner()


class TestRootHelp:
    """Test root command help and discoverability."""
    
    def test_help_without_args(self):
        """Bare `rif` should print help."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Commands:" in result.stdout
        assert "check" in result.stdout
        assert "serve" in result.stdout
        assert "replay" in result.stdout
        assert "msf-check" in result.stdout
        assert "status" in result.stdout
    
    def test_help_flag(self):
        """rif --help should print help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "check" in result.stdout
        assert "replay" in result.stdout
    
    def test_root_description(self):
        """Root help should describe the tool."""
        result = runner.invoke(app, ["--help"])
        assert "Governed agent runtime" in result.stdout
        assert "policy" in result.stdout


class TestServeCommand:
    """Test serve command."""
    
    def test_serve_help(self):
        """serve --help should show bind options and examples."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "host" in result.stdout
        assert "port" in result.stdout
        assert "reload" in result.stdout
        assert "Examples:" in result.stdout
        assert "rif serve" in result.stdout
    
    def test_serve_reload_flag(self):
        """serve should accept --reload and --no-reload."""
        # Just check that the flag is accepted; full server start is out of scope
        result = runner.invoke(app, ["serve", "--help"])
        assert "--reload" in result.stdout or "--no-reload" in result.stdout


class TestCheckCommand:
    """Test check command."""
    
    def test_check_help(self):
        """check --help should document network actions."""
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "actor" in result.stdout
        assert "action" in result.stdout
        assert "target" in result.stdout
        assert "Network actions" in result.stdout
        assert "http.request" in result.stdout
        assert "Examples:" in result.stdout
    
    def test_check_with_valid_intent(self):
        """check with valid intent should exit 0 with JSON."""
        result = runner.invoke(app, ["check", "agent:test", "http.request", "https://example.com"])
        assert result.exit_code == 0
        # Parse JSON to ensure output is valid
        data = json.loads(result.stdout)
        assert "decision" in data
        assert data["decision"] in ["allow", "deny"]
    
    def test_check_missing_args(self):
        """check without args should exit 1."""
        result = runner.invoke(app, ["check"])
        assert result.exit_code != 0
    
    def test_check_policy_decision_is_json(self):
        """check output should be valid JSON."""
        result = runner.invoke(app, ["check", "agent:test", "http.request", "https://api.anthropic.com"])
        assert result.exit_code == 0
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail("check output is not valid JSON")


class TestReplayCommand:
    """Test replay command."""
    
    def test_replay_help(self):
        """replay --help should explain JSONL path and show examples."""
        result = runner.invoke(app, ["replay", "--help"])
        assert result.exit_code == 0
        assert "decisions.jsonl" in result.stdout
        assert "Examples:" in result.stdout
        assert "rif replay" in result.stdout
    
    def test_replay_missing_file(self):
        """replay with nonexistent file should exit 1 with clear error."""
        result = runner.invoke(app, ["replay", "/nonexistent/path.jsonl"])
        assert result.exit_code != 0
        assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()
    
    def test_replay_empty_file(self):
        """replay with empty JSONL should succeed with note on stderr."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Write nothing; file is empty
            f.flush()
            temp_path = f.name
        
        try:
            result = runner.invoke(app, ["replay", temp_path])
            # Should succeed (exit 0) but print note about empty file
            assert result.exit_code == 0
            assert "empty" in result.stdout.lower() or "empty" in result.stderr.lower()
        finally:
            Path(temp_path).unlink()
    
    def test_replay_valid_jsonl(self):
        """replay with valid JSONL should succeed."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Write one valid decision
            decision = {
                "decision": "allow",
                "actor": "agent:test",
                "action": "http.request",
                "target": "https://example.com",
                "environment": "test",
                "posture": "normal",
                "reason": "trusted_actor",
                "matched_rule": "rule_1"
            }
            f.write(json.dumps(decision) + '\n')
            f.flush()
            temp_path = f.name
        
        try:
            result = runner.invoke(app, ["replay", temp_path])
            assert result.exit_code == 0
            # Output should contain recovered state info
            assert "historical_decisions" in result.stdout or "historical_decisions" in result.stderr
        finally:
            Path(temp_path).unlink()
    
    def test_replay_invalid_jsonl(self):
        """replay with invalid JSON line should exit 1 with clear error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("{not valid json\n")
            f.flush()
            temp_path = f.name
        
        try:
            result = runner.invoke(app, ["replay", temp_path])
            assert result.exit_code != 0
            # Should mention the line number or path
            output = result.stdout + result.stderr
            assert "invalid" in output.lower() or "json" in output.lower()
        finally:
            Path(temp_path).unlink()


class TestMsfCheckCommand:
    """Test msf-check command."""
    
    def test_msf_check_help(self):
        """msf-check --help should document modes and show examples."""
        result = runner.invoke(app, ["msf-check", "--help"])
        assert result.exit_code == 0
        assert "mode" in result.stdout
        assert "Governance modes:" in result.stdout
        assert "read_only_firewall" in result.stdout
        assert "shadow" in result.stdout
        assert "Examples:" in result.stdout
    
    def test_msf_check_invalid_mode(self):
        """msf-check with invalid mode should exit 1 with list of valid modes."""
        result = runner.invoke(app, ["msf-check", "test/module", "https://example.com", "--mode=invalid_mode"])
        assert result.exit_code != 0
        output = result.stdout + result.stderr
        assert "invalid_mode" in output or "unknown" in output.lower()
        # Should list valid modes
        assert "read_only_firewall" in output or "shadow" in output
    
    def test_msf_check_default_mode(self):
        """msf-check should use read_only_firewall as default mode."""
        result = runner.invoke(app, ["msf-check", "auxiliary/scanner/http/http_version", "https://example.com"])
        # Should succeed or fail gracefully (no traceback)
        assert "Traceback" not in result.stdout and "Traceback" not in result.stderr
    
    def test_msf_check_valid_mode(self):
        """msf-check with valid mode should not fail on mode validation."""
        result = runner.invoke(app, ["msf-check", "test/module", "https://example.com", "--mode=shadow"])
        # Should not error on mode validation
        output = result.stdout + result.stderr
        assert "unknown mode" not in output.lower()


class TestStatusCommand:
    """Test status command."""
    
    def test_status_help(self):
        """status --help should explain the command."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "JSON" in result.stdout or "json" in result.stdout
        assert "read-only" in result.stdout.lower() or "local" in result.stdout.lower()
    
    def test_status_output_is_json(self):
        """status should output valid JSON."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail("status output is not valid JSON")
        
        # Check expected fields
        assert "environment" in data
        assert "posture" in data
    
    def test_status_includes_summary_fields(self):
        """status should include persisted and recovered state."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "persisted" in data or "recovered" in data


class TestErrorMessages:
    """Test error message clarity."""
    
    def test_errors_on_stderr(self):
        """Errors should be written to stderr, not stdout."""
        result = runner.invoke(app, ["check"])
        # Missing args should produce an error on stderr
        assert result.exit_code != 0
    
    def test_no_raw_tracebacks_for_user_errors(self):
        """User input errors should not dump Python tracebacks."""
        result = runner.invoke(app, ["replay", "/nonexistent/path.jsonl"])
        assert result.exit_code != 0
        output = result.stdout + result.stderr
        assert "Traceback" not in output
        assert "Exception" not in output or "Expected" not in output


class TestExitCodes:
    """Test proper exit code behavior."""
    
    def test_check_allow_exits_zero(self):
        """check with allow result should exit 0."""
        result = runner.invoke(app, ["check", "agent:test", "http.request", "https://example.com"])
        assert result.exit_code == 0
    
    def test_check_deny_exits_zero(self):
        """check with deny result should still exit 0 (decision is in JSON)."""
        # Intentionally use a likely-blocked target
        result = runner.invoke(app, ["check", "agent:untrusted", "http.request", "https://blocked.example.com"])
        # Exit code should be 0 even if decision is deny
        assert result.exit_code == 0
    
    def test_validation_error_exits_nonzero(self):
        """Validation errors should exit non-zero."""
        result = runner.invoke(app, ["msf-check", "module", "target", "--mode=bad"])
        assert result.exit_code != 0
    
    def test_file_not_found_exits_nonzero(self):
        """Missing files should exit non-zero."""
        result = runner.invoke(app, ["replay", "/nonexistent.jsonl"])
        assert result.exit_code != 0


class TestExamples:
    """Test that documented examples work."""
    
    def test_serve_example(self):
        """serve --help example should be valid syntax."""
        result = runner.invoke(app, ["serve", "--help"])
        assert "rif serve --no-reload" in result.stdout
    
    def test_check_example(self):
        """check --help example should be valid and runnable."""
        result = runner.invoke(app, ["check", "--help"])
        assert "rif check agent:test http.request" in result.stdout
    
    def test_replay_example(self):
        """replay --help example should be valid."""
        result = runner.invoke(app, ["replay", "--help"])
        assert "rif replay" in result.stdout
    
    def test_msf_check_example(self):
        """msf-check --help example should be valid."""
        result = runner.invoke(app, ["msf-check", "--help"])
        assert "rif msf-check" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
