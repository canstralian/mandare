import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import rif_runtime


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    expected = data["project"]["version"]

    # Explicitly verify installed package metadata matches pyproject.toml.
    # If this raises, the package wasn't pip-installed after the version bump
    # (run `pip install -e .`). Relying solely on __version__ would silently
    # pass via the fallback constant when the package isn't installed.
    try:
        installed = version("rif-runtime")
    except PackageNotFoundError as exc:
        raise AssertionError(
            "rif-runtime not installed — run `pip install -e .` before testing"
        ) from exc

    assert installed == expected, (
        f"installed metadata {installed!r} != pyproject {expected!r}"
    )
    assert rif_runtime.__version__ == expected
