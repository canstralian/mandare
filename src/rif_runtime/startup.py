"""FastAPI startup hook for configuration validation and governance recovery.

Import and call ``register_config_startup(app)`` from the main API module
to wire in configuration loading, validation, and governance state recovery
at startup.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI

from .config import ConfigError, get_settings
from .governance.posture import PostureThresholds
from .governance.reflexive import restore_from_log

logger = logging.getLogger(__name__)


def register_config_startup(app: FastAPI) -> None:
    """Register a startup event that validates config and restores governance state."""

    @app.on_event("startup")
    def _validate_config() -> None:
        try:
            settings = get_settings()
        except ConfigError as exc:
            logger.critical("Configuration validation failed: %s", exc)
            raise SystemExit(1) from exc

        # Store on app.state so route handlers can access if needed
        app.state.settings = settings

        logger.info(
            "RIF runtime configuration loaded: %s",
            settings.safe_summary(),
        )

        # --- Governance state recovery ---
        governance = settings.governance
        decision_log_path = Path(settings.paths.data_dir) / "decisions.jsonl"

        thresholds = PostureThresholds(
            elevated_at=governance.posture_elevated_at,
            restricted_at=governance.posture_restricted_at,
            locked_at=governance.posture_locked_at,
        )

        posture = restore_from_log(decision_log_path, thresholds)
        app.state.posture = posture  # type: ignore[attr-defined]
        app.state.posture_thresholds = thresholds  # type: ignore[attr-defined]

        logger.info("Governance posture initialized: %s", posture.value)
