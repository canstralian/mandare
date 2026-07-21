import tomllib
from pathlib import Path

import rif_runtime


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    assert rif_runtime.__version__ == data["project"]["version"]
