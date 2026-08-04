from __future__ import annotations

from hashlib import sha256
from typing import Any

from .repository import RepositoryResource, RepositorySnapshot
from .scanner import RepositoryScanner
from .snapshot import ResourceSnapshot


class RepositorySnapshotBuilder:
    """
    Builds immutable RepositorySnapshot objects from scanner observations.
    """

    def build(
        self,
        resource: RepositoryResource,
        scanner: RepositoryScanner,
    ) -> RepositorySnapshot:
        """
        Build a repository snapshot from scanner results.
        
        Parameters:
            resource (RepositoryResource): Repository resource to associate with the snapshot.
            scanner (RepositoryScanner): Scanner providing the repository modules and tests.
        
        Returns:
            RepositorySnapshot: Snapshot containing the repository resource, modules, tests, and content hash.
        """
        modules = scanner.modules()
        tests = scanner.tests()

        snapshot = ResourceSnapshot(
            resource=resource.reference,
            snapshot_id="repository-snapshot",
            content_hash=self._content_hash(modules, tests),
        )

        return RepositorySnapshot(
            resource=resource,
            snapshot=snapshot,
            commit_sha="unknown",
            tree_hash="unknown",
            modules=modules,
            tests=tests,
        )

    @staticmethod
    def _content_hash(modules: tuple[Any, ...], tests: tuple[Any, ...]) -> str:
        """Create a SHA-256 digest from the module and test counts.
        
        Parameters:
        	modules (tuple[Any, ...]): Modules included in the repository snapshot.
        	tests (tuple[Any, ...]): Tests included in the repository snapshot.
        
        Returns:
        	str: The hexadecimal SHA-256 digest of the module and test counts.
        """
        payload = f"{len(modules)}:{len(tests)}"
        return sha256(payload.encode("utf-8")).hexdigest()
