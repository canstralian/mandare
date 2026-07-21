try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("rif-runtime")
except PackageNotFoundError:
    # Fallback for editable/dev installs that haven't been pip-installed yet.
    # This string must be kept in sync with pyproject.toml manually; the version
    # consistency test will catch drift if the package is properly installed.
    __version__ = "0.2.2"
