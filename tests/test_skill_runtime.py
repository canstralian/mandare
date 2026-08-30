from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from rif_runtime.execution.result import ExecutionResult, ExecutionStatus
from rif_runtime.skills import (
    SkillExecutionContext,
    SkillManifest,
    SkillRuntime,
    SkillStep,
    topological_order,
    valid_skill_id,
    valid_step_id,
)


SCHEMA_PATH = Path(__file__).parents[1] / "contracts" / "skill_manifest.schema.json"


class StubExecutor:
    def __init__(self, statuses: list[ExecutionStatus] | None = None) -> None:
        self.statuses = statuses or [ExecutionStatus.SUCCEEDED]
        self.calls = []

    def execute_capability(self, manifest):
        self.calls.append(manifest)
        status = self.statuses[min(len(self.calls) - 1, len(self.statuses) - 1)]
        return ExecutionResult(status=status)


def test_identifier_regexes_are_anchored_to_contract_shape() -> None:
    assert valid_skill_id("research-analysis")
    assert valid_skill_id("a")
    assert not valid_skill_id("Research-analysis")
    assert not valid_skill_id("research_analysis")
    assert not valid_skill_id("research.analysis")
    assert valid_step_id("extract_evidence")
    assert not valid_step_id("extract-evidence")


def test_topological_order_is_deterministic() -> None:
    steps = (
        SkillStep("synthesize", "summarize", ("claims", "sources")),
        SkillStep("sources", "acquire"),
        SkillStep("claims", "extract"),
    )
    assert tuple(step.step_id for step in topological_order(steps)) == (
        "claims",
        "sources",
        "synthesize",
    )


def test_topological_order_rejects_missing_dependency_and_cycle() -> None:
    with pytest.raises(ValueError, match="missing dependencies"):
        topological_order((SkillStep("a", "cap", ("missing",)),))

    with pytest.raises(ValueError, match="cycle"):
        topological_order(
            (
                SkillStep("a", "cap_a", ("b",)),
                SkillStep("b", "cap_b", ("a",)),
            )
        )


def test_skill_runtime_delegates_every_step_to_existing_executor() -> None:
    executor = StubExecutor([ExecutionStatus.SUCCEEDED, ExecutionStatus.SUCCEEDED])
    runtime = SkillRuntime(executor)
    skill = SkillManifest(
        spec_version="0.1",
        skill_id="research-analysis",
        version="1.0.0",
        description="Research workflow",
        steps=(
            SkillStep("synthesize", "summarize", ("extract",)),
            SkillStep("extract", "extract_evidence"),
        ),
    )
    context = SkillExecutionContext(
        run_id="run-1",
        actor="agent",
        skill_id=skill.skill_id,
        skill_version=skill.version,
    )

    result = runtime.execute(skill, context)

    assert result.failed_step is None
    assert result.completed_steps == ("extract", "synthesize")
    assert [call.capability for call in executor.calls] == [
        "extract_evidence",
        "summarize",
    ]
    assert executor.calls[0].metadata["run_id"] == "run-1"


def test_skill_runtime_stops_after_failed_capability() -> None:
    executor = StubExecutor([ExecutionStatus.FAILED, ExecutionStatus.SUCCEEDED])
    runtime = SkillRuntime(executor)
    skill = SkillManifest(
        spec_version="0.1",
        skill_id="research-analysis",
        version="1.0.0",
        description="Research workflow",
        steps=(SkillStep("first", "first_cap"), SkillStep("second", "second_cap")),
    )
    context = SkillExecutionContext(
        run_id="run-2",
        actor="agent",
        skill_id=skill.skill_id,
        skill_version=skill.version,
    )

    result = runtime.execute(skill, context)

    assert result.failed_step == "first"
    assert result.completed_steps == ()
    assert len(executor.calls) == 1


def test_skill_manifest_schema_rejects_unknown_fields() -> None:
    import json

    schema = json.loads(SCHEMA_PATH.read_text())
    instance = {
        "spec_version": "0.1",
        "skill_id": "research-analysis",
        "version": "1.0.0",
        "description": "Research workflow",
        "steps": [
            {
                "step_id": "extract_evidence",
                "capability_id": "extract",
                "unexpected": True,
            }
        ],
    }
    errors = list(Draft202012Validator(schema).iter_errors(instance))
    assert any("unexpected" in error.message for error in errors)
