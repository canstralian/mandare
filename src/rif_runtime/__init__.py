try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("rif-runtime")
except PackageNotFoundError:
    __version__ = "0.2.2"
