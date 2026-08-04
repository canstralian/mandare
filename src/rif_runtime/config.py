"""Runtime configuration contract for RIF.

Loads settings from ``rif.toml`` (project root) with environment-variable
overrides prefixed ``RIF_``.  Env vars take precedence over file values.

Env-var mapping (section flattened with underscore, uppercased):
  [runtime] posture        -> RIF_POSTURE
  [runtime] environment    -> RIF_ENVIRONMENT
  [runtime] cloud_egress   -> RIF_CLOUD_EGRESS
  [server]  host           -> RIF_SERVER_HOST
  [server]  port           -> RIF_SERVER_PORT
  [server]  root_path      -> RIF_SERVER_ROOT_PATH
  [provider] mode          -> RIF_PROVIDER_MODE
  [provider] model         -> RIF_PROVIDER_MODEL
  [provider] endpoint      -> RIF_PROVIDER_ENDPOINT
  [paths]   data_dir       -> RIF_DATA_DIR
  [paths]   config_dir     -> RIF_CONFIG_DIR
  [security] rate_limit_rps             -> RIF_RATE_LIMIT_RPS
  [security] rate_limit_burst           -> RIF_RATE_LIMIT_BURST
  [security] auth_lockout_attempts      -> RIF_AUTH_LOCKOUT_ATTEMPTS
  [security] auth_lockout_window_seconds-> RIF_AUTH_LOCKOUT_WINDOW_SECONDS
"""

from __future__ import annotations

import os
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from .schemas import RuntimeConfig

_SETTINGS_TOML_PATH = Path("rif.toml")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProviderMode(StrEnum):
    """Supported provider execution modes."""

    local = "local"
    remote = "remote"
    hybrid = "hybrid"


class PostureLevel(StrEnum):
    """Runtime governance posture levels."""

    normal = "normal"
    elevated = "elevated"
    restricted = "restricted"
    locked = "locked"


# ---------------------------------------------------------------------------
# Settings sub-models
# ---------------------------------------------------------------------------


class RuntimeSection(BaseModel):
    """Top-level runtime behaviour knobs."""

    model_config = ConfigDict(extra="forbid")

    posture: PostureLevel = PostureLevel.normal
    environment: str = "production"
    cloud_egress: bool = False


class ServerSection(BaseModel):
    """HTTP server configuration."""

    model_config = ConfigDict(extra="forbid")

    # Default bind for local/dev servers; operators override via rif.toml / RIF_HOST.
    host: str = "0.0.0.0"  # nosec B104
    port: int = 8000
    root_path: str = ""

    @field_validator("port")
    @classmethod
    def _port_range(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


class ProviderSection(BaseModel):
    """LLM / AI provider configuration."""

    model_config = ConfigDict(extra="forbid")

    mode: ProviderMode = ProviderMode.local
    model: str = "default"
    endpoint: str = ""


class PathsSection(BaseModel):
    """Filesystem paths used by the runtime."""

    model_config = ConfigDict(extra="forbid")

    data_dir: str = "data"
    config_dir: str = "config"


class SecuritySection(BaseModel):
    """Security hardening knobs (rate limiting + auth lockout).

    All values are optional and fall back to safe defaults.
    """

    model_config = ConfigDict(extra="forbid")

    rate_limit_rps: float = 20.0
    rate_limit_burst: int = 40
    auth_lockout_attempts: int = 10
    auth_lockout_window_seconds: float = 60.0

    @field_validator("rate_limit_rps")
    @classmethod
    def _rps_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("rate_limit_rps must be positive")
        return v

    @field_validator("rate_limit_burst")
    @classmethod
    def _burst_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("rate_limit_burst must be >= 1")
        return v

    @field_validator("auth_lockout_attempts")
    @classmethod
    def _attempts_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("auth_lockout_attempts must be >= 1")
        return v

    @field_validator("auth_lockout_window_seconds")
    @classmethod
    def _window_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("auth_lockout_window_seconds must be positive")
        return v


# ---------------------------------------------------------------------------
# Top-level settings
# ---------------------------------------------------------------------------


class RifSettings(BaseModel):
    """Canonical runtime settings loaded from rif.toml + RIF_* env vars.

    Unknown keys are rejected (extra='forbid') so typos surface immediately.
    """

    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeSection = RuntimeSection()
    server: ServerSection = ServerSection()
    provider: ProviderSection = ProviderSection()
    paths: PathsSection = PathsSection()
    security: SecuritySection = SecuritySection()

    def safe_summary(self) -> dict[str, Any]:
        """Return a secret-safe dict suitable for logging at startup.

        Redacts provider.endpoint (may contain tokens in query params).
        """
        data = self.model_dump()
        endpoint = data["provider"]["endpoint"]
        if endpoint:
            data["provider"]["endpoint"] = "***"
        return data


# ---------------------------------------------------------------------------
# Env-var override mapping
# ---------------------------------------------------------------------------

# Maps RIF_<NAME> env var to (section, key) path in the settings dict.
_ENV_MAP: dict[str, tuple[str, str]] = {
    "RIF_POSTURE": ("runtime", "posture"),
    "RIF_ENVIRONMENT": ("runtime", "environment"),
    "RIF_CLOUD_EGRESS": ("runtime", "cloud_egress"),
    "RIF_SERVER_HOST": ("server", "host"),
    "RIF_SERVER_PORT": ("server", "port"),
    "RIF_SERVER_ROOT_PATH": ("server", "root_path"),
    "RIF_PROVIDER_MODE": ("provider", "mode"),
    "RIF_PROVIDER_MODEL": ("provider", "model"),
    "RIF_PROVIDER_ENDPOINT": ("provider", "endpoint"),
    "RIF_DATA_DIR": ("paths", "data_dir"),
    "RIF_CONFIG_DIR": ("paths", "config_dir"),
    "RIF_RATE_LIMIT_RPS": ("security", "rate_limit_rps"),
    "RIF_RATE_LIMIT_BURST": ("security", "rate_limit_burst"),
    "RIF_AUTH_LOCKOUT_ATTEMPTS": ("security", "auth_lockout_attempts"),
    "RIF_AUTH_LOCKOUT_WINDOW_SECONDS": ("security", "auth_lockout_window_seconds"),
}


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Overlay RIF_* env vars onto a parsed TOML dict (mutates in place)."""
    for env_key, (section, key) in _ENV_MAP.items():
        value = os.environ.get(env_key)
        if value is None:
            continue
        data.setdefault(section, {})[key] = _coerce_env_value(value, section, key)
    return data


def _coerce_env_value(raw: str, section: str, key: str) -> str | int | float | bool:
    """Best-effort coercion so env vars match expected TOML types."""
    # Boolean fields
    if key == "cloud_egress":
        return raw.lower() in ("1", "true", "yes")
    # Integer fields
    if key in ("port", "rate_limit_burst", "auth_lockout_attempts"):
        return int(raw)
    # Float fields
    if key in ("rate_limit_rps", "auth_lockout_window_seconds"):
        return float(raw)
    return raw


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""


def load_settings(
    path: Path | str | None = None,
) -> RifSettings:
    """Load RIF settings from TOML file + env-var overrides.

    Args:
        path: Explicit path to the TOML file.  Defaults to ``rif.toml`` in
              the current working directory.

    Returns:
        Validated ``RifSettings`` instance.

    Raises:
        ConfigError: If the file contains invalid/unknown keys or values
                     fail validation.
    """
    toml_path = Path(path) if path is not None else _SETTINGS_TOML_PATH

    # Load base config from file; fall back to empty dict (all defaults)
    if toml_path.is_file():
        with open(toml_path, "rb") as f:
            data: dict[str, Any] = tomllib.load(f)
    else:
        data = {}

    # Apply env-var overrides
    _apply_env_overrides(data)

    # Validate
    try:
        return RifSettings.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


# Module-level singleton (lazy)
_settings: RifSettings | None = None


def get_settings() -> RifSettings:
    """Return the module-level settings singleton, loading on first access."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_settings() -> None:
    """Reset the cached singleton (useful in tests)."""
    global _settings  # noqa: PLW0603
    _settings = None


# ---------------------------------------------------------------------------
# Legacy loader (backward-compatible)
# ---------------------------------------------------------------------------


def load_config(path: str | Path | None = None) -> RuntimeConfig:
    """Load the environments config from YAML (legacy interface).

    Used by ``RIFRuntime.__init__``.  The path now defaults to
    ``<settings.paths.config_dir>/environments.yaml``.
    """
    if path is None:
        settings = get_settings()
        path = Path(settings.paths.config_dir) / "environments.yaml"
    else:
        path = Path(path)

    if not path.is_file():
        # Provide sensible defaults when environments file is absent
        from .schemas import EnvironmentProfile

        return RuntimeConfig(
            default_environment="production",
            environments={"production": EnvironmentProfile()},
        )

    return RuntimeConfig.model_validate(yaml.safe_load(path.read_text()))
