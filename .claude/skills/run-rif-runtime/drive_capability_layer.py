"""Drive RIF Runtime's Capability Layer end-to-end: policy evaluation, then
execution through the kernel. Run from the repo root with the project's venv:

    python .claude/skills/run-rif-runtime/drive_capability_layer.py

This exercises the direct-invocation path (no server, no CLI process) that
the Capability Layer is reachable through today — see SKILL.md's "Capability
Layer (direct invocation)" section for why.
"""

from __future__ import annotations

import json
import sys

from rif_runtime.capabilities.echo import EchoCapability
from rif_runtime.capabilities.registry import CapabilityRegistry
from rif_runtime.configuration.policies import PolicyRule
from rif_runtime.execution.exceptions import CapabilityNotFoundError
from rif_runtime.execution.kernel import ExecutionKernel
from rif_runtime.execution.manifest import ExecutionManifest
from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import Decision, EnvironmentProfile, PolicyRequest, Posture


def run_allowed_echo() -> None:
    """
    Demonstrate successful policy authorization and capability execution.
    
    The request must be explicitly allowed by policy; an unrestricted networking
    profile and normal posture alone do not authorize execution. Raises
    `RuntimeError` if policy denies the request.
    """
    registry = CapabilityRegistry([EchoCapability()])
    kernel = ExecutionKernel(registry)
    policy = PolicyEngine()
    profile = EnvironmentProfile(networking_type="unrestricted")
    rules = [
        PolicyRule(
            id="allow_demo_echo",
            effect="allow",
            action="capability.echo",
            target="echo",
            reason="demo capability invocation",
        )
    ]

    req = PolicyRequest(actor="agent:demo", action="capability.echo", target="echo")
    decision = policy.evaluate(req, "demo", profile, Posture.normal, rules)
    print(f"policy decision: {decision.decision} ({decision.reason})")

    if decision.decision != Decision.allow:
        raise RuntimeError(f"unexpected policy denial: {decision.reason}")

    manifest = ExecutionManifest(
        actor="agent:demo",
        capability="echo",
        action="ping",
        parameters={"payload": "hello from the run-skill driver"},
    )
    result = kernel.execute(manifest)
    print(f"execution status: {result.status}")
    print(f"execution output: {json.dumps(result.output)}")


def run_locked_posture_denial() -> None:
    """Demonstrates the deny path: Posture.locked denies unconditionally
    (PolicyEngine.evaluate()'s first check), before the capability is ever
    resolved or executed."""
    policy = PolicyEngine()
    profile = EnvironmentProfile(networking_type="unrestricted")

    req = PolicyRequest(actor="agent:demo", action="capability.echo", target="echo")
    decision = policy.evaluate(req, "demo", profile, Posture.locked)
    print(f"policy decision: {decision.decision} ({decision.reason})")

    if decision.decision == Decision.allow:
        raise RuntimeError("expected posture.locked to deny, but it allowed")

    print("execution skipped: policy denied")


def run_unregistered_capability() -> None:
    """Shows the error a new provider adapter (e.g. a Hugging Face capability)
    must resolve by registering itself — this is the exact failure mode
    before that registration exists."""
    kernel = ExecutionKernel(CapabilityRegistry([]))
    manifest = ExecutionManifest(
        actor="agent:demo", capability="huggingface.infer", action="generate"
    )
    try:
        kernel.execute(manifest)
    except CapabilityNotFoundError as exc:
        print(f"CapabilityNotFoundError (expected): {exc}")


if __name__ == "__main__":
    run_allowed_echo()
    print("---")
    run_locked_posture_denial()
    print("---")
    run_unregistered_capability()
    sys.exit(0)
