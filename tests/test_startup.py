"""Startup configuration validation.

startup.py was at 53% coverage with the failure branch entirely unexercised,
which is how it went unnoticed that a SystemExit raised inside the old
@app.on_event("startup") handler never reached the caller: anyio's task group
swallowed it and surfaced CancelledError instead.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rif_runtime.config import ConfigError, RifSettings
from rif_runtime.startup import config_lifespan


def _app() -> FastAPI:
    return FastAPI(lifespan=config_lifespan)


def test_startup_caches_settings_on_app_state():
    app = _app()

    with TestClient(app):
        assert isinstance(app.state.settings, RifSettings)


def test_startup_aborts_on_invalid_configuration(monkeypatch: pytest.MonkeyPatch):
    """Invalid configuration must stop startup, not boot on unchosen defaults.

    Asserting ConfigError specifically is the point of the lifespan migration:
    under the old on_event handler this surfaced as CancelledError, so
    "configuration is invalid" was indistinguishable from "startup was
    cancelled".
    """

    def _raise() -> RifSettings:
        raise ConfigError("unknown key: rif_totally_made_up")

    monkeypatch.setattr("rif_runtime.startup.get_settings", _raise)

    with pytest.raises(ConfigError, match="rif_totally_made_up"):
        with TestClient(_app()):
            pass


def test_failed_startup_leaves_no_settings_on_state(monkeypatch: pytest.MonkeyPatch):
    def _raise() -> RifSettings:
        raise ConfigError("bad config")

    monkeypatch.setattr("rif_runtime.startup.get_settings", _raise)
    app = _app()

    with pytest.raises(ConfigError):
        with TestClient(app):
            pass

    assert not hasattr(app.state, "settings")


def test_startup_failure_is_logged_critical(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    def _raise() -> RifSettings:
        raise ConfigError("bad config")

    monkeypatch.setattr("rif_runtime.startup.get_settings", _raise)

    with caplog.at_level("CRITICAL", logger="rif_runtime.startup"):
        with pytest.raises(ConfigError):
            with TestClient(_app()):
                pass

    assert any(record.levelname == "CRITICAL" for record in caplog.records)


def test_startup_logs_a_secret_safe_summary():
    """The startup log must not carry a provider endpoint verbatim."""
    endpoint = "https://provider.example.com/v1?token=super-secret-value"
    settings = RifSettings.model_validate({"provider": {"endpoint": endpoint}})

    summary = settings.safe_summary()

    assert summary["provider"]["endpoint"] == "***"
    assert "super-secret-value" not in str(summary)


def test_startup_runs_for_the_real_api_app():
    """The wiring in api.py is what actually matters."""
    from rif_runtime.api import app as api_app

    with TestClient(api_app):
        assert isinstance(api_app.state.settings, RifSettings)


def test_no_module_calls_the_deprecated_on_event_hook():
    """Guard against a revert to the deprecated hook.

    Walks the AST rather than grepping: startup.py's docstring names
    `@app.on_event("startup")` while explaining why it no longer uses it, so a
    text match reports its own explanation as a violation.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    offenders = []
    for path in (root / "src" / "rif_runtime").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "on_event"
            ):
                offenders.append(f"{path.relative_to(root)}:{node.lineno}")

    assert not offenders, f"deprecated on_event hook called at: {offenders}"
