import pytest


pytest.importorskip("mcp")

from rif_runtime.mcp.github import GITHUB_READ_ONLY_TOOLS, _target  # noqa: E402


def test_github_gateway_pins_read_only_tools():
    assert "get_file_contents" in GITHUB_READ_ONLY_TOOLS
    assert "pull_request_read" in GITHUB_READ_ONLY_TOOLS
    assert "create_pull_request" not in GITHUB_READ_ONLY_TOOLS
    assert "merge_pull_request" not in GITHUB_READ_ONLY_TOOLS
    assert "create_or_update_file" not in GITHUB_READ_ONLY_TOOLS


def test_github_gateway_targets_repo_api_host():
    assert _target({"owner": "canstralian", "repo": "mandare"}) == (
        "https://api.github.com/repos/canstralian/mandare"
    )


def test_github_gateway_defaults_to_api_host():
    assert _target({}) == "https://api.github.com"
