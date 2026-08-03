from rif_runtime.resources.identity import ResourceId, ResourceKind
from rif_runtime.resources.resource import ResourceReference


def test_reference_keeps_identity_separate_from_uri() -> None:
    reference = ResourceReference(
        id=ResourceId(
            kind=ResourceKind.REPOSITORY,
            namespace="canstralian",
            name="rif-runtime",
        ),
        uri="https://github.com/canstralian/rif-runtime",
    )

    assert reference.id.name == "rif-runtime"
    assert reference.uri.startswith("https://")
