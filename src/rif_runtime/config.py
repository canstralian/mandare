from pathlib import Path

import yaml

from .schemas import RuntimeConfig


def load_config(path: str | Path = Path("config/environments.yaml")) -> RuntimeConfig:
    """
    Load and validate runtime configuration from a YAML file.
    
    Parameters:
    	path (str | Path): Path to the YAML configuration file.
    
    Returns:
    	RuntimeConfig: The validated runtime configuration.
    """
    return RuntimeConfig.model_validate(yaml.safe_load(Path(path).read_text()))
