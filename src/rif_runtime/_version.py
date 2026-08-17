from __future__ import annotations


def _read_version_from_pyproject() -> str | None:
    # Returns None (not raises) so _read_version() can escalate to RuntimeWarning.
    # None is correct both for built wheels (no pyproject.toml on this path) and
    # for source checkouts where the layout changed.
    #
    # Depth assumption: src/rif_runtime/_version.py is exactly 3 directories below
    # the repo root (root/src/rif_runtime/_version.py). Only valid in source/editable
    # checkouts — built wheels go through importlib.metadata instead.
    try:
        import tomllib
        from pathlib import Path

        _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        with _pyproject.open("rb") as _f:
            version: str = tomllib.load(_f)["project"]["version"]
            # #region agent log
            import json as _json
            import time as _time

            open("/opt/cursor/logs/debug.log", "a").write(
                _json.dumps(
                    {
                        "hypothesisId": "H3",
                        "location": "_version.py:_read_version_from_pyproject",
                        "message": "pyproject version path resolved",
                        "data": {
                            "version_file": str(Path(__file__).resolve()),
                            "pyproject_path": str(_pyproject.resolve()),
                            "in_site_packages": "site-packages" in str(Path(__file__)),
                            "version": version,
                        },
                        "timestamp": int(_time.time() * 1000),
                    }
                )
                + "\n"
            )
            # #endregion
            return version
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError) as _exc:
        # #region agent log
        import json as _json
        import time as _time
        from pathlib import Path as _Path

        open("/opt/cursor/logs/debug.log", "a").write(
            _json.dumps(
                {
                    "hypothesisId": "H3",
                    "location": "_version.py:_read_version_from_pyproject",
                    "message": "pyproject version path FAILED",
                    "data": {
                        "version_file": str(_Path(__file__).resolve()),
                        "resolved_root_candidate": str(
                            _Path(__file__).parent.parent.parent.resolve()
                        ),
                        "in_site_packages": "site-packages"
                        in str(_Path(__file__).resolve()),
                        "error_type": type(_exc).__name__,
                        "error": str(_exc),
                    },
                    "timestamp": int(_time.time() * 1000),
                }
            )
            + "\n"
        )
        # #endregion
        return None


def _read_version() -> str:
    """Resolve package version without a hardcoded duplicate of pyproject.toml.

    Resolution order:
    1. importlib.metadata  — installed package, normal case
    2. pyproject.toml      — editable source checkout without pip install
    3. RuntimeWarning + "unknown" — last resort when both paths unavailable
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        _meta = version("rif-runtime")
        # #region agent log
        import json as _json
        import time as _time
        from pathlib import Path as _Path

        open("/opt/cursor/logs/debug.log", "a").write(
            _json.dumps(
                {
                    "hypothesisId": "H3",
                    "location": "_version.py:_read_version",
                    "message": "version via importlib.metadata",
                    "data": {
                        "source": "importlib.metadata",
                        "version": _meta,
                        "version_file": str(_Path(__file__).resolve()),
                        "in_site_packages": "site-packages"
                        in str(_Path(__file__).resolve()),
                    },
                    "timestamp": int(_time.time() * 1000),
                }
            )
            + "\n"
        )
        # #endregion
        return _meta
    except PackageNotFoundError:
        pass

    # Package not installed — read directly from pyproject.toml in the source tree.
    # Real use case: `python -m rif_runtime` in a fresh clone before `pip install -e .`.
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


# Called once when rif_runtime is first imported; Python's module cache means
# this runs at most once per process.
__version__ = _read_version()
