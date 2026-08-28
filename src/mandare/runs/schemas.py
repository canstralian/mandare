"""Pydantic schemas for the run lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    created = "created"
    policy_approved = "policy_approved"
    denied = "denied"
    failed = "failed"


class RunRequest(BaseModel):
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    identity_id: str
    status: RunStatus
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    policy_decision: str | None = None
    matched_rule: str | None = None
