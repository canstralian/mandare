"""Agent package: the template, its worked examples, and the manifest binding.

Every module here sat at 0% coverage. `agents/manifest.py` in particular is the
Python side of a checked-in contract (`.rif/agents/manifest.schema.yaml`) with
nothing asserting the two agree, and `DeputyAgent.review` branches on a
StrEnum by string comparison without a test proving that works.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

from rif_runtime.agents.deputy import DeputyAgent
from rif_runtime.agents.manifest import AgentManifest
from rif_runtime.agents.orchestrator import OrchestratorAgent
from rif_runtime.schemas import Decision, PolicyDecision, Posture

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / ".rif" / "agents" / "manifest.schema.yaml"
)


def _decision(decision: Decision) -> PolicyDecision:
    """Create a policy decision fixture with fixed test context and the specified decision.
    
    Parameters:
    	decision (Decision): The policy decision outcome to include.
    
    Returns:
    	PolicyDecision: A policy decision populated with the standard test actor, request, target, environment, posture, reason, and matched rule.
    """
    return PolicyDecision(
        decision=decision,
        actor="agent:test",
        action="http.request",
        target="https://example.com",
        environment="RIF_Runtime",
        posture=Posture.normal,
        reason="test",
        matched_rule="policy.test",
    )


# --- manifest contract -------------------------------------------------------


def test_agent_manifest_matches_the_declared_schema():
    """Verify that AgentManifest fields match the declared manifest schema and include all required properties."""
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    fields = {f.name for f in dataclasses.fields(AgentManifest)}

    assert fields == set(schema["properties"]), (
        "AgentManifest fields and manifest.schema.yaml properties have diverged"
    )
    assert set(schema["required"]) <= fields


def test_agent_manifest_is_immutable():
    manifest = AgentManifest(
        name="agent:example",
        kind="claude-skill",
        description="",
        owns=(),
        responsibilities=(),
        inputs=(),
        outputs=(),
        depends_on=(),
        blocks=(),
        quality_gates=(),
        invariants=(),
    )

    try:
        manifest.name = "agent:mutated"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("AgentManifest should be frozen")


# --- deputy ------------------------------------------------------------------


def test_deputy_flags_a_denial():
    """
    Verify that the Deputy agent reports denied policy decisions with the matched rule.
    """
    review = DeputyAgent().review(_decision(Decision.deny))

    assert review["agent"] == "agent:deputy"
    assert review["finding"] == "policy denial observed"
    assert review["rule"] == "policy.test"


def test_deputy_passes_an_allow_through():
    review = DeputyAgent().review(_decision(Decision.allow))

    assert review["finding"] == "request allowed"


def test_deputy_treats_review_as_not_a_denial():
    """Decision has three members; `review` must not be read as a denial."""
    review = DeputyAgent().review(_decision(Decision.review))

    assert review["finding"] == "request allowed"


# --- orchestrator ------------------------------------------------------------


def test_orchestrator_builds_a_governed_request():
    request = OrchestratorAgent().request_http("https://example.com", reason="why")

    assert request.actor == "agent:orchestrator"
    assert request.action == "http.request"
    assert request.target == "https://example.com"
    assert request.reason == "why"


def test_orchestrator_actor_follows_the_template_convention():
    """template.py points at OrchestratorAgent as the naming example."""
    from rif_runtime.agents.template import TemplateAgent

    assert TemplateAgent(OrchestratorAgent.name).validate() is True


# --- execution lifecycle seam ------------------------------------------------


def test_execution_state_overlaps_run_status_as_the_spec_review_notes():
    """Pins the overlap the identity-spine review is holding open.

    ExecutionState is seeded but unwired. If someone converges it with
    RunStatus without going through that review, this test's premise changes
    and the reconciliation gets noticed rather than landing silently.
    """
    from rif_runtime.execution.state import ExecutionState
    from rif_runtime.runs.schemas import RunStatus

    shared = {member.value for member in ExecutionState} & {
        member.value for member in RunStatus
    }

    assert shared == {"created", "policy_approved", "denied", "failed"}


def test_execution_state_is_not_used_by_the_runtime():
    """Seeded means seeded: nothing should be reading it yet."""
    import ast

    root = Path(__file__).resolve().parent.parent / "src" / "rif_runtime"
    importers = []
    for path in root.rglob("*.py"):
        if path.name == "state.py" and path.parent.name == "execution":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and "execution.state" in (
                node.module or ""
            ):
                importers.append(str(path.relative_to(root)))
            elif isinstance(node, ast.ImportFrom) and node.module == ".state":
                importers.append(str(path.relative_to(root)))

    assert not importers, (
        f"ExecutionState is now imported by {importers}. Wiring it is Track B "
        "work held by docs/spec-review-identity-spine-migration.md -- update "
        "that review's status before landing this."
    )
