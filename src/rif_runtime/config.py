from pathlib import Path

import yaml

from .schemas import RuntimeConfig


def load_config(path: str | Path = Path("config/environments.yaml")) -> RuntimeConfig:
    return RuntimeConfig.model_validate(yaml.safe_load(Path(path).read_text()))
