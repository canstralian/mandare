from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .inventory import ModuleInfo, TestInfo
from .resource import ResourceReference
from .snapshot import ResourceSnapshot


@dataclass(frozen=True, slots=True)
class RepositoryResource:
    """
    Repository-specific resource metadata.

    A repository composes a ResourceReference rather than inheriting from it.
    """

    reference: ResourceReference
    default_branch: str = "main"


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """
    Immutable observation of a repository at a point in time.
    """

    resource: RepositoryResource
    snapshot: ResourceSnapshot

    commit_sha: str
    tree_hash: str

    modules: Sequence[ModuleInfo]
    tests: Sequence[TestInfo]

    @property
    def module_count(self) -> int:
        return len(self.modules)

    @property
    def test_count(self) -> int:
        return len(self.tests)
