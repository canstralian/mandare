from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping


SKILL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
"""Lexical shape for stable skill identifiers."""

STEP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
"""Lexical shape for stable step identifiers."""


class SkillStepKind(StrEnum):
    """Kinds of work a skill planner may describe."""

    capability = "capability"


def _freeze(value: Any) -> Any:
    """Convert built-in mutable containers to deterministic read-only forms."""
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a recursively frozen copy of a mapping payload."""
    frozen = _freeze(dict(value))
    if not isinstance(frozen, Mapping):
        raise TypeError("expected mapping payload")
    return frozen


@dataclass(frozen=True, slots=True)
class SkillStep:
    """One deterministic, governed step in a skill plan.

    ``depends_on`` is an immutable tuple because dependency order is part of
    the replay contract. ``parameters`` and ``metadata`` are recursively frozen
    at construction so nested lists and dictionaries cannot mutate the plan.
    """

    step_id: str
    capability_id: str
    depends_on: tuple[str, ...] = ()
    kind: SkillStepKind = SkillStepKind.capability
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "depends_on", tuple(self.depends_on))
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class SkillManifest:
    """Versioned declarative procedure composed from governed capabilities."""

    schema_version: str
    skill_id: str
    version: str
    description: str
    steps: tuple[SkillStep, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class SkillExecutionContext:
    """Immutable context shared by one skill execution attempt."""

    run_id: str
    actor: str
    skill_id: str
    skill_version: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class SkillExecutionResult:
    """Aggregate result for a skill execution."""

    skill_id: str
    completed_steps: tuple[str, ...]
    failed_step: str | None
    results: tuple[Any, ...]


def valid_skill_id(value: str) -> bool:
    """Return whether ``value`` has the permitted skill identifier shape."""
    return bool(SKILL_ID_RE.fullmatch(value))


def valid_step_id(value: str) -> bool:
    """Return whether ``value`` has the permitted step identifier shape."""
    return bool(STEP_ID_RE.fullmatch(value))
