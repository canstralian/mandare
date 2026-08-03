from dataclasses import FrozenInstanceError

import pytest

from rif_runtime.resources.identity import ResourceId, ResourceKind


def test_resource_id_string_representation() -> None:
    resource_id = ResourceId(
        kind=ResourceKind.REPOSITORY,
        namespace="canstralian",
        name="rif-runtime",
    )

    assert str(resource_id) == "repository:canstralian/rif-runtime"


def test_resource_id_is_immutable() -> None:
    resource_id = ResourceId(
        kind=ResourceKind.REPOSITORY,
        namespace="canstralian",
        name="rif-runtime",
    )

    with pytest.raises(FrozenInstanceError):
        resource_id.name = "other"  # type: ignore[misc]
