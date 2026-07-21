try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("rif-runtime")
except PackageNotFoundError:
    # Package not installed — read version directly from pyproject.toml so there
    # is no manually-maintained duplicate string. This covers source-tree runs
    # (e.g. `python -m rif_runtime`) without a prior `pip install -e .`.
    try:
        import tomllib
        from pathlib import Path

        _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        with _pyproject.open("rb") as _f:
            __version__ = tomllib.load(_f)["project"]["version"]
    except (FileNotFoundError, KeyError):
        # True last resort: no metadata and no pyproject.toml (e.g. installed
        # into a location without the source tree). Bump via scripts/bump-version.sh.
        __version__ = "0.2.2"
