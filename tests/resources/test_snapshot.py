from rif_runtime.resources.identity import ResourceId, ResourceKind
from rif_runtime.resources.resource import ResourceReference
from rif_runtime.resources.snapshot import ResourceSnapshot


def test_snapshot_preserves_reference() -> None:
    reference = ResourceReference(
        id=ResourceId(
            kind=ResourceKind.REPOSITORY,
            namespace="canstralian",
            name="rif-runtime",
        ),
        uri="https://github.com/canstralian/rif-runtime",
    )

    snapshot = ResourceSnapshot(
        resource=reference,
        snapshot_id="snapshot-001",
        content_hash="sha256:test",
    )

    assert snapshot.resource is reference
    assert snapshot.content_hash == "sha256:test"
