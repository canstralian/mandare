from __future__ import annotations

from pathlib import Path

import yaml

from .schemas import RuntimeConfig

DEFAULT_CONFIG_PATH = Path("config/environments.yaml")


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> RuntimeConfig:
    return RuntimeConfig.model_validate(
        yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    )
