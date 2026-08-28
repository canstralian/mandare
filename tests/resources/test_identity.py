from dataclasses import FrozenInstanceError

import pytest

from mandare.resources.identity import ResourceId, ResourceKind


def test_resource_id_string_representation() -> None:
    resource_id = ResourceId(
        kind=ResourceKind.REPOSITORY,
        namespace="canstralian",
        name="mandare",
    )

    assert str(resource_id) == "repository:canstralian/mandare"


def test_resource_id_is_immutable() -> None:
    resource_id = ResourceId(
        kind=ResourceKind.REPOSITORY,
        namespace="canstralian",
        name="mandare",
    )

    with pytest.raises(FrozenInstanceError):
        resource_id.name = "other"  # type: ignore[misc]
