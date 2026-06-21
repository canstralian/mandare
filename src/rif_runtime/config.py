from pathlib import Path
import yaml
from .schemas import RuntimeConfig

def load_config(path=Path('config/environments.yaml')):
    return RuntimeConfig.model_validate(yaml.safe_load(Path(path).read_text()))
