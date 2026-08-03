from __future__ import annotations

from hashlib import sha256

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
    def _content_hash(modules: tuple, tests: tuple) -> str:
        payload = (
            f"{len(modules)}:"
            f"{len(tests)}"
        )
        return sha256(payload.encode("utf-8")).hexdigest()
