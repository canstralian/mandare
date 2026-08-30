from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from ..execution.manifest import ExecutionManifest
from ..execution.result import ExecutionResult, ExecutionStatus
from .models import SkillExecutionContext, SkillExecutionResult, SkillManifest, SkillStep


class CapabilityExecutor(Protocol):
    """Existing runtime surface required by the skill orchestrator."""

    def execute_capability(self, manifest: ExecutionManifest) -> ExecutionResult:
        """Execute one already-declared capability through the runtime gate."""


@dataclass(frozen=True, slots=True)
class PlannedStep:
    """A skill step with its deterministic execution position."""

    ordinal: int
    step: SkillStep


def _canonical_step_key(step: SkillStep) -> tuple[str, str]:
    """Return a stable key for tie-breaking independent of mapping order."""
    return (step.step_id, step.capability_id)


def topological_order(steps: Iterable[SkillStep]) -> tuple[SkillStep, ...]:
    """Return a deterministic topological ordering of skill steps.

    The planner rejects duplicate identifiers, missing dependencies and cycles.
    When multiple nodes are ready, lexical ``(step_id, capability_id)`` order is
    used so replay does not depend on insertion order or thread scheduling.
    """
    step_map: dict[str, SkillStep] = {}
    for step in steps:
        if step.step_id in step_map:
            raise ValueError(f"duplicate skill step: {step.step_id}")
        step_map[step.step_id] = step

    dependents: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = {}
    for step in step_map.values():
        unique_dependencies = set(step.depends_on)
        if step.step_id in unique_dependencies:
            raise ValueError(f"skill step depends on itself: {step.step_id}")
        missing = unique_dependencies - step_map.keys()
        if missing:
            raise ValueError(
                f"skill step {step.step_id} has missing dependencies: "
                f"{sorted(missing)}"
            )
        indegree[step.step_id] = len(unique_dependencies)
        for dependency in unique_dependencies:
            dependents[dependency].add(step.step_id)

    ready = sorted(
        (step_map[step_id] for step_id, degree in indegree.items() if degree == 0),
        key=_canonical_step_key,
    )
    ordered: list[SkillStep] = []

    while ready:
        step = ready.pop(0)
        ordered.append(step)
        for dependent_id in sorted(dependents[step.step_id]):
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                ready.append(step_map[dependent_id])
                ready.sort(key=_canonical_step_key)

    if len(ordered) != len(step_map):
        unresolved = sorted(set(step_map) - {step.step_id for step in ordered})
        raise ValueError(f"skill dependency cycle detected: {unresolved}")

    return tuple(ordered)


class SkillRuntime:
    """Orchestrate declarative skills through the existing RIF runtime gate.

    This class deliberately contains no policy rules, admission rules, or
    capability validation. Each step becomes an ``ExecutionManifest`` and is
    handed to the existing ``execute_capability`` path, preserving one
    authorization and evidence regime for the whole runtime.
    """

    def __init__(self, executor: CapabilityExecutor) -> None:
        self._executor = executor

    def plan(self, skill: SkillManifest) -> tuple[PlannedStep, ...]:
        """Compile a skill manifest into deterministic executable steps."""
        return tuple(
            PlannedStep(ordinal=index, step=step)
            for index, step in enumerate(topological_order(skill.steps))
        )

    def execute(
        self,
        skill: SkillManifest,
        context: SkillExecutionContext,
        *,
        result_factory: Callable[[SkillStep, ExecutionResult], Any] | None = None,
    ) -> SkillExecutionResult:
        """Execute skill steps through the existing capability authorization path.

        The executor remains the sole authority for policy and admission. A
        failed capability result stops the skill; no later step is dispatched.
        """
        if context.skill_id != skill.skill_id:
            raise ValueError("execution context skill_id does not match manifest")
        if context.skill_version != skill.version:
            raise ValueError("execution context skill_version does not match manifest")

        planned = self.plan(skill)
        completed: list[str] = []
        results: list[Any] = []

        for planned_step in planned:
            step = planned_step.step
            manifest = ExecutionManifest(
                actor=context.actor,
                capability=step.capability_id,
                action=f"skill:{skill.skill_id}:{step.step_id}",
                target=None,
                parameters=dict(MappingProxyType(dict(step.parameters))),
                metadata={
                    **dict(context.metadata),
                    **dict(step.metadata),
                    "skill_id": skill.skill_id,
                    "skill_version": skill.version,
                    "skill_step_id": step.step_id,
                    "skill_step_ordinal": planned_step.ordinal,
                    "run_id": context.run_id,
                },
            )
            result = self._executor.execute_capability(manifest)
            results.append(
                result_factory(step, result) if result_factory else result
            )
            if result.status is not ExecutionStatus.SUCCEEDED:
                return SkillExecutionResult(
                    skill_id=skill.skill_id,
                    completed_steps=tuple(completed),
                    failed_step=step.step_id,
                    results=tuple(results),
                )
            completed.append(step.step_id)

        return SkillExecutionResult(
            skill_id=skill.skill_id,
            completed_steps=tuple(completed),
            failed_step=None,
            results=tuple(results),
        )
