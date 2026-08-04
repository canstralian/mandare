from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModuleInfo:
    """
    Describes a Python module discovered in a repository.
    """

    name: str
    path: Path


@dataclass(frozen=True, slots=True)
class TestInfo:
    """
    Describes a Python test module.
    """

    name: str
    path: Path
