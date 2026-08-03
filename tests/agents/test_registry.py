import pytest

from rif_runtime.agents.exceptions import (
    DuplicateAgentError,
    UnknownAgentError,
)
from rif_runtime.agents.manifest import AgentManifest
from rif_runtime.agents.registry import AgentRegistry


def manifest(name: str = "runtime-architect") -> AgentManifest:
    return AgentManifest(
        name=name,
        kind="cursor-agent",
        description="Test agent.",
        owns=(),
        responsibilities=(),
        inputs=(),
        outputs=(),
        depends_on=(),
        blocks=(),
        quality_gates=(),
        invariants=(),
    )


def test_registry_starts_empty() -> None:
    registry = AgentRegistry()

    assert len(registry) == 0


def test_register_agent() -> None:
    registry = AgentRegistry()

    registry.register(manifest())

    assert len(registry) == 1


def test_contains_operator() -> None:
    registry = AgentRegistry()

    registry.register(manifest())

    assert "runtime-architect" in registry


def test_resolve_agent() -> None:
    registry = AgentRegistry()

    registry.register(manifest())

    assert registry.resolve("runtime-architect").name == "runtime-architect"


def test_duplicate_registration_raises() -> None:
    registry = AgentRegistry()

    registry.register(manifest())

    with pytest.raises(DuplicateAgentError):
        registry.register(manifest())


def test_unknown_agent_raises() -> None:
    registry = AgentRegistry()

    with pytest.raises(UnknownAgentError):
        registry.resolve("unknown")
