def _read_version_from_pyproject() -> str | None:
    # Only reachable in source/editable checkouts, not built wheels.
    # Returns None (not raises) so _read_version() can escalate to RuntimeWarning
    # — None is correct here both for built wheels (no pyproject.toml on path)
    # and for source checkouts where the layout changed.
    try:
        import tomllib
        from pathlib import Path

        _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        with _pyproject.open("rb") as _f:
            return tomllib.load(_f)["project"]["version"]
    except (FileNotFoundError, KeyError):
        return None


def _read_version() -> str:
    """Resolve package version without a hardcoded duplicate of pyproject.toml."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("rif-runtime")
    except PackageNotFoundError:
        pass

    # Package not installed — read directly from pyproject.toml in the source tree.
    # Covers `python -m rif_runtime` style runs without a prior `pip install -e .`.
    v = _read_version_from_pyproject()
    if v is not None:
        return v

    # Neither metadata nor pyproject.toml is reachable — surface this loudly
    # rather than returning a silently-stale constant.
    import warnings

    warnings.warn(
        "rif-runtime: version could not be determined. "
        "Run `pip install -e .` to fix this.",
        RuntimeWarning,
        stacklevel=2,
    )
    return "unknown"


# Called once at module import time; Python's module cache means this runs at most
# once per process regardless of how many times `import rif_runtime` is called.
__version__ = _read_version()
