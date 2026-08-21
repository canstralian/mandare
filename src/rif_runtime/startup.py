"""Application lifespan: configuration validation at startup.

Pass ``config_lifespan`` to the ``FastAPI`` constructor to validate and cache
configuration before the application accepts requests.

This replaced an ``@app.on_event("startup")`` handler. Beyond the deprecation,
``on_event`` gave the failure path no clear semantics: a ``SystemExit`` raised
inside it was swallowed by anyio's task group and surfaced to callers as
``CancelledError``, so "configuration is invalid" and "startup was cancelled"
were indistinguishable. Under lifespan the exception propagates.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import ConfigError, get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def config_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate configuration, cache it on ``app.state``, then serve.

    Fails fast: invalid configuration aborts startup rather than booting a
    half-configured runtime that would decide policy against defaults nobody
    chose.
    """
    try:
        settings = get_settings()
    except ConfigError:
        logger.critical("Configuration validation failed", exc_info=True)
        raise

    # Stored on app.state so route handlers can reach it without re-loading.
    app.state.settings = settings

    logger.info(
        "RIF runtime configuration loaded: %s",
        settings.safe_summary(),
    )

    yield
