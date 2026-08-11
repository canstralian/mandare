from __future__ import annotations

from enum import StrEnum


class ExecutionState(StrEnum):
    """
    Lifecycle states for a governed execution.

    States represent where an execution is in the runtime
    lifecycle, independent of its final outcome.
    """

    CREATED = "created"
    POLICY_APPROVED = "policy_approved"
    ROUTING = "routing"
    EXECUTING = "executing"
    RECORDING_EVIDENCE = "recording_evidence"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"
