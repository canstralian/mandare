from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .identity import ResourceKind


class ResourceEffect(str, Enum):
    """
    Categories of governed operations performed on resources.
    """

    READ = "read"
    WRITE = "write"
    SNAPSHOT = "snapshot"
    INVENTORY = "inventory"
    PROJECT = "project"
    RENDER = "render"


@dataclass(frozen=True, slots=True)
class ResourceCapabilityDescriptor:
    """
    Declarative description of a governed capability against a resource.

    Policy evaluates descriptors.
    Providers execute approved operations.
    """

    name: str
    resource_kind: ResourceKind
    effect: ResourceEffect
    replayable: bool
    description: str
