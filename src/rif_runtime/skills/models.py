from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping


SKILL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
"""Lexical shape for stable skill identifiers."""

STEP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
"""Lexical shape for stable step identifiers."""


class SkillStepKind(StrEnum):
    """Kinds of work a skill planner may describe."""

    capability = "capability"


@dataclass(frozen=True, slots=True)
class SkillStep:
    """One deterministic, governed step in a skill plan.

    ``depends_on`` is an immutable tuple because dependency order is part of
    the replay contract. ``parameters`` and ``metadata`` are copied into
    immutable mapping views by the runtime boundary; they are not policy
    decisions or authorization grants.
    """

    step_id: str
    capability_id: str
    kind: SkillStepKind = SkillStepKind.capability
    depends_on: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillManifest:
    """Versioned declarative procedure composed from governed capabilities.

    A manifest describes procedure and input shape only. Its presence never
    grants permission, selects a provider, carries credentials, or records a
    policy verdict. Authorization remains in the existing capability gate.
    """

    spec_version: str
    skill_id: str
    version: str
    description: str
    steps: tuple[SkillStep, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillExecutionContext:
    """Immutable context shared by one skill execution attempt."""

    run_id: str
    actor: str
    skill_id: str
    skill_version: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillExecutionResult:
    """Aggregate result for a skill execution.

    Individual capability results remain owned by the existing execution
    kernel. This object records orchestration state without introducing a
    second execution or policy model.
    """

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
