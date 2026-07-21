import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

import rif_runtime


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    expected = data["project"]["version"]

    # Verify installed package metadata matches pyproject.toml.
    # CI always runs `pip install -e .` before pytest (see ci.yml), so this
    # path is always taken there. Local dev runs without an editable install
    # are skipped rather than hard-failed to avoid confusing new contributors.
    try:
        installed = version("rif-runtime")
    except PackageNotFoundError:
        pytest.skip("rif-runtime not installed — run `pip install -e .` first")

    assert installed == expected, (
        f"installed metadata {installed!r} != pyproject {expected!r}"
    )
    assert rif_runtime.__version__ == expected
