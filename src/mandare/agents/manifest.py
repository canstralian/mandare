from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentManifest:
    """
    Immutable description of an AI engineering agent.

    Agent manifests are declarative metadata. They describe an agent's
    responsibilities, capabilities, dependencies, and quality gates.
    """

    name: str
    kind: str
    description: str

    owns: Sequence[str]
    responsibilities: Sequence[str]

    inputs: Sequence[str]
    outputs: Sequence[str]

    depends_on: Sequence[str]
    blocks: Sequence[str]

    quality_gates: Sequence[str]
    invariants: Sequence[str]
