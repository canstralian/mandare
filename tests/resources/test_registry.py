import pytest

from mandare.resources.descriptor import (
    ResourceCapabilityDescriptor,
    ResourceEffect,
)
from mandare.resources.exceptions import (
    DuplicateResourceCapabilityError,
    UnknownResourceCapabilityError,
)
from mandare.resources.identity import ResourceKind
from mandare.resources.registry import ResourceCapabilityRegistry


def descriptor(name: str) -> ResourceCapabilityDescriptor:
    return ResourceCapabilityDescriptor(
        name=name,
        resource_kind=ResourceKind.REPOSITORY,
        effect=ResourceEffect.READ,
        replayable=True,
        description="test",
    )


def test_registry_resolves_registered_descriptor() -> None:
    registry = ResourceCapabilityRegistry([descriptor("repo.snapshot.read")])

    resolved = registry.resolve("repo.snapshot.read")

    assert resolved.name == "repo.snapshot.read"


def test_duplicate_registration_fails() -> None:
    registry = ResourceCapabilityRegistry()

    registry.register(descriptor("repo.snapshot.read"))

    with pytest.raises(DuplicateResourceCapabilityError):
        registry.register(descriptor("repo.snapshot.read"))


def test_unknown_descriptor_fails() -> None:
    registry = ResourceCapabilityRegistry()

    with pytest.raises(UnknownResourceCapabilityError):
        registry.resolve("missing")
