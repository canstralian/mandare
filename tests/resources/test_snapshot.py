from mandare.resources.identity import ResourceId, ResourceKind
from mandare.resources.resource import ResourceReference
from mandare.resources.snapshot import ResourceSnapshot


def test_snapshot_preserves_reference() -> None:
    reference = ResourceReference(
        id=ResourceId(
            kind=ResourceKind.REPOSITORY,
            namespace="canstralian",
            name="mandare",
        ),
        uri="https://github.com/canstralian/mandare",
    )

    snapshot = ResourceSnapshot(
        resource=reference,
        snapshot_id="snapshot-001",
        content_hash="sha256:test",
    )

    assert snapshot.resource is reference
    assert snapshot.content_hash == "sha256:test"
