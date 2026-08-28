from mandare.resources.identity import ResourceId, ResourceKind
from mandare.resources.resource import ResourceReference


def test_reference_keeps_identity_separate_from_uri() -> None:
    reference = ResourceReference(
        id=ResourceId(
            kind=ResourceKind.REPOSITORY,
            namespace="canstralian",
            name="mandare",
        ),
        uri="https://github.com/canstralian/mandare",
    )

    assert reference.id.name == "mandare"
    assert reference.uri.startswith("https://")
