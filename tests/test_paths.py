"""RIF_DATA_DIR relocates every persisted store, and defaults to data/."""

import os

from rif_runtime.configuration.policies import PolicyStore
from rif_runtime.paths import (
    DATA_DIR_ENV,
    DECISIONS_FILE,
    DEFAULT_DATA_DIR,
    data_dir,
    data_path,
)
from rif_runtime.replay import ReplayEngine
from rif_runtime.runtime import RIFRuntime


def test_data_dir_defaults_when_unset(monkeypatch):
    monkeypatch.delenv(DATA_DIR_ENV, raising=False)
    assert data_dir() == DEFAULT_DATA_DIR
    assert data_path(DECISIONS_FILE) == DEFAULT_DATA_DIR / DECISIONS_FILE


def test_data_dir_follows_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    assert data_dir() == tmp_path
    assert data_path(DECISIONS_FILE) == tmp_path / DECISIONS_FILE


def test_runtime_stores_land_under_the_configured_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    runtime = RIFRuntime()
    for store in (
        runtime.decisions_store,
        runtime.posture_store,
        runtime.evidence_store,
    ):
        assert store.path.parent == tmp_path
    assert runtime.policy_store.store.path.parent == tmp_path


def test_replay_engine_defaults_to_the_configured_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    assert ReplayEngine().store.path == tmp_path / DECISIONS_FILE


def test_explicit_path_still_wins(tmp_path):
    explicit = tmp_path / "custom.json"
    assert PolicyStore(str(explicit)).store.path == explicit


def test_suite_runs_against_a_relocated_data_dir():
    # conftest points RIF_DATA_DIR at a tmp dir so the suite never writes into
    # the repository's checked-in data/policies.json or gitignored JSONL logs.
    configured = os.environ.get(DATA_DIR_ENV)
    assert configured, "conftest must set RIF_DATA_DIR"
    assert DEFAULT_DATA_DIR.resolve() != data_dir().resolve()
