from pathlib import Path

from mandare.resources import (
    RepositoryResource,
    RepositoryScanner,
    RepositorySnapshotBuilder,
    ResourceId,
    ResourceKind,
    ResourceReference,
)


def make_resource() -> RepositoryResource:
    reference = ResourceReference(
        id=ResourceId(
            kind=ResourceKind.REPOSITORY,
            namespace="canstralian",
            name="mandare",
        ),
        uri="file://.",
    )

    return RepositoryResource(reference=reference)


def test_snapshot_preserves_resource_identity() -> None:
    """
    A snapshot must preserve the identity of the resource it observes.
    """

    builder = RepositorySnapshotBuilder()

    snapshot = builder.build(
        make_resource(),
        RepositoryScanner(Path(".")),
    )

    assert snapshot.resource.reference.id.namespace == "canstralian"
    assert snapshot.resource.reference.id.name == "mandare"


def test_snapshot_counts_match_inventory() -> None:
    """
    Derived counts must equal the inventory they summarize.
    """

    builder = RepositorySnapshotBuilder()

    snapshot = builder.build(
        make_resource(),
        RepositoryScanner(Path(".")),
    )

    assert snapshot.module_count == len(snapshot.modules)
    assert snapshot.test_count == len(snapshot.tests)


def test_snapshot_hash_is_deterministic() -> None:
    """
    Building the same repository twice without changes should
    produce the same content hash.
    """

    builder = RepositorySnapshotBuilder()

    scanner = RepositoryScanner(Path("."))

    first = builder.build(make_resource(), scanner)
    second = builder.build(make_resource(), scanner)

    assert first.snapshot.content_hash == second.snapshot.content_hash


def test_snapshot_never_contains_mutable_collections() -> None:
    """
    Snapshot inventories should be immutable.
    """

    builder = RepositorySnapshotBuilder()

    snapshot = builder.build(
        make_resource(),
        RepositoryScanner(Path(".")),
    )

    assert isinstance(snapshot.modules, tuple)
    assert isinstance(snapshot.tests, tuple)
