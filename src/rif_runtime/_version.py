from __future__ import annotations


# #region agent log
def _dbg(hypothesis_id, location, message, data=None):
    import json
    import time

    with open("/workspace/.cursor/debug-1e76.log", "a") as f:
        f.write(
            json.dumps(
                {
                    "sessionId": "1e76",
                    "hypothesisId": hypothesis_id,
                    "location": location,
                    "message": message,
                    "data": data or {},
                    "timestamp": int(time.time() * 1000),
                }
            )
            + "\n"
        )


# #endregion


def _read_version_from_pyproject() -> str | None:
    # Returns None (not raises) so _read_version() can escalate to RuntimeWarning.
    # None is correct both for built wheels (no pyproject.toml on this path) and
    # for source checkouts where the layout changed.
    #
    # Depth assumption: src/rif_runtime/_version.py is exactly 3 directories below
    # the repo root (root/src/rif_runtime/_version.py). Only valid in source/editable
    # checkouts — built wheels go through importlib.metadata instead.
    # #region agent log
    _file = __file__
    _in_site = "site-packages" in _file
    _in_src = "/src/" in _file.replace("\\", "/")
    _dbg(
        "H1",
        "_version.py:_read_version_from_pyproject:entry",
        "entry",
        {
            "__file__": _file,
            "in_site_packages": _in_site,
            "in_src_tree": _in_src,
            "install_layout": (
                "site-packages"
                if _in_site
                else ("src-editable" if _in_src else "other")
            ),
        },
    )
    # #endregion
    try:
        import tomllib
        from pathlib import Path

        _here = Path(__file__)
        _candidates = {
            "parents[0]": _here.parents[0] / "pyproject.toml",
            "parents[1]": _here.parents[1] / "pyproject.toml",
            "parents[2]": _here.parents[2] / "pyproject.toml",
            "parents[3]": (
                _here.parents[3] / "pyproject.toml" if len(_here.parents) > 3 else None
            ),
        }
        _pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        # #region agent log
        _cand_info = {}
        for k, v in _candidates.items():
            _cand_info[k] = {
                "path": str(v) if v is not None else None,
                "exists": v.exists() if v is not None else False,
            }
        _dbg(
            "H1",
            "_version.py:_read_version_from_pyproject:candidates",
            "pyproject candidate paths",
            {
                "chosen": str(_pyproject),
                "chosen_exists": _pyproject.exists(),
                "candidates": _cand_info,
            },
        )
        # #endregion
        with _pyproject.open("rb") as _f:
            version: str = tomllib.load(_f)["project"]["version"]
            # #region agent log
            _dbg(
                "H2",
                "_version.py:_read_version_from_pyproject:success",
                "read version from pyproject",
                {"version": version, "pyproject": str(_pyproject)},
            )
            # #endregion
            return version
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError) as _exc:
        # #region agent log
        _dbg(
            "H1",
            "_version.py:_read_version_from_pyproject:fail",
            "returning None",
            {
                "exc_type": type(_exc).__name__,
                "exc": str(_exc),
                "__file__": __file__,
            },
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
        _dbg(
            "H3",
            "_version.py:_read_version:metadata",
            "importlib.metadata succeeded",
            {"version": _meta, "__file__": __file__},
        )
        # #endregion
        return _meta
    except PackageNotFoundError as _exc:
        # #region agent log
        _dbg(
            "H3",
            "_version.py:_read_version:metadata_miss",
            "importlib.metadata PackageNotFoundError",
            {"exc": str(_exc), "__file__": __file__},
        )
        # #endregion
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
