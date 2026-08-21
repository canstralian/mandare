"""Packaged environments.yaml must stay in sync with config/environments.yaml.

``load_config()`` falls back to the bundled copy when the configured path is
absent (Vercel / site-packages cold starts). Drift between the two files would
silently ship stale host allowlists.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from rif_runtime.config import load_config, reset_settings
from rif_runtime.runtime import RIFRuntime

ROOT = Path(__file__).resolve().parent.parent
REPO_ENVIRONMENTS = ROOT / "config" / "environments.yaml"
PACKAGED_ENVIRONMENTS = (
    ROOT / "src" / "rif_runtime" / "bundled_config" / "environments.yaml"
)


@pytest.fixture(autouse=True)
def _reset_settings() -> Generator[None, None, None]:
    reset_settings()
    yield
    reset_settings()


def test_packaged_environments_matches_repo_config() -> None:
    assert PACKAGED_ENVIRONMENTS.is_file(), (
        f"missing packaged environments at {PACKAGED_ENVIRONMENTS}; "
        "copy config/environments.yaml into src/rif_runtime/bundled_config/"
    )
    assert REPO_ENVIRONMENTS.read_text() == PACKAGED_ENVIRONMENTS.read_text(), (
        "src/rif_runtime/bundled_config/environments.yaml drifted from "
        "config/environments.yaml — copy the repo file into the package"
    )


def test_missing_config_dir_uses_packaged_rif_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Vercel-style cold start: no CWD config/, RIF_ENVIRONMENT=RIF_Runtime."""
    monkeypatch.setenv("RIF_CONFIG_DIR", str(tmp_path / "no-such-config"))
    monkeypatch.setenv("RIF_ENVIRONMENT", "RIF_Runtime")
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path / "data"))
    reset_settings()

    cfg = load_config()
    assert "RIF_Runtime" in cfg.environments
    assert "api.anthropic.com" in cfg.environments["RIF_Runtime"].allowed_hosts

    runtime = RIFRuntime(data_dir=tmp_path / "data")
    assert runtime.environment_name == "RIF_Runtime"
    assert "api.github.com" in runtime.profile.allowed_hosts


def test_unknown_explicit_rif_environment_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RIF_CONFIG_DIR", str(tmp_path / "no-such-config"))
    monkeypatch.setenv("RIF_ENVIRONMENT", "NotARealEnv")
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path / "data"))
    reset_settings()

    with pytest.raises(ValueError, match="unknown environment from RIF_ENVIRONMENT"):
        RIFRuntime(data_dir=tmp_path / "data")


def test_unset_rif_environment_falls_back_to_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Settings default 'production' may miss the map when env var is unset."""
    monkeypatch.delenv("RIF_ENVIRONMENT", raising=False)
    monkeypatch.setenv("RIF_CONFIG_DIR", str(tmp_path / "no-such-config"))
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path / "data"))
    reset_settings()

    runtime = RIFRuntime(data_dir=tmp_path / "data")
    # Packaged yaml default_environment is RIF_Runtime
    assert runtime.environment_name == "RIF_Runtime"
