"""The Metasploit MCP governor: firewall, shadow harness, and lab broker.

Three governance lanes share one ordered decision procedure. The order of the
checks *is* the answer to "which authority boundary prevented escalation":

1. ``posture.locked``            — a locked runtime denies everything.
2. injection / NL-authority      — untrusted instructions are quarantined; a
                                   natural-language assertion is never authority.
3. read-only capability          — security knowledge is always permitted.
4. consequential capability      — requires authority the lane may not grant:
     * read-only firewall lane   — denied outright (execution authority absent).
     * shadow lane               — denied and simulated; never reaches the tool.
     * lab-broker lane           — permitted only with a valid, time-bound,
                                   target-pinned, dual-authorised capability
                                   token whose intent hash still matches.

Every decision produces a signed evidence event.
"""

from __future__ import annotations

import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from ..schemas import Decision, PolicyDecision, Posture
from ..security import hmac_signature, sha256_digest
from .capabilities import (
    CapabilityClass,
    classify,
    contract_hash,
    is_severe,
)

# Natural-language authority assertions and prompt-injection markers. None of
# these confer authority; their presence in operator text, imported recon, or
# tool parameters quarantines the request.
INJECTION_PATTERNS: tuple[str, ...] = (
    "ignore previous",
    "ignore all previous",
    "ignore the above",
    "disregard previous",
    "disregard the above",
    "new instructions",
    "system prompt",
    "you are now",
    "you are authorised",
    "you are authorized",
    "you are permitted",
    "skip safeguards",
    "skip the safeguards",
    "skip governance",
    "bypass policy",
    "bypass the policy",
    "bypass governance",
    "disable governance",
    "disable the policy",
    "override policy",
    "override the policy",
    "grant yourself",
    "elevate your",
    "as an administrator",
    "act as root",
    "no restrictions",
    "without approval",
)


class GovernanceMode(StrEnum):
    """Which containment lane evaluates a Metasploit intent."""

    read_only_firewall = "read_only_firewall"
    shadow = "shadow"
    lab_broker = "lab_broker"


class MetasploitIntent(BaseModel):
    """A proposed Metasploit MCP call, as seen by the governor.

    ``capability`` is the concrete tool method (e.g. ``module.search``); free
    natural language lives in ``text`` and imported/untrusted material in
    ``untrusted_context`` — neither participates in the signed intent hash.
    """

    actor: str = "agent:metasploit"
    tool: str = "msfmcpd"
    capability: str
    target: str
    scope_id: str = "unscoped"
    text: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    untrusted_context: str | None = None

    def intent_hash(self) -> str:
        return sha256_digest(
            {
                "tool": self.tool,
                "capability": self.capability,
                "target": self.target,
                "scope_id": self.scope_id,
                "params": self.params,
            }
        )


class CapabilityToken(BaseModel):
    """A short-lived, single-capability, target-pinned execution grant.

    Minted only after signed human approval. Binds one capability to one target
    and to the exact intent hash approved, and expires quickly so stale
    authority cannot be reused.
    """

    token_id: str = Field(default_factory=lambda: str(uuid4()))
    capability: str
    target: str
    scope_id: str
    intent_hash: str
    approver: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime
    signature: str = ""

    @field_validator("issued_at", "expires_at", mode="after")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        # A token deserialised from a naive ISO string would otherwise raise a
        # TypeError when compared against the timezone-aware ``now`` in the
        # broker, and would sign inconsistently across environments.
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def signing_payload(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "capability": self.capability,
            "target": self.target,
            "scope_id": self.scope_id,
            "intent_hash": self.intent_hash,
            "approver": self.approver,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


class EvidenceEvent(BaseModel):
    """Signed, replayable record of one governance decision."""

    decision_id: str
    intent_hash: str
    tool: str
    requested_capability: str
    policy_decision: str
    scope_id: str
    contract_hash: str
    matched_rule: str
    timestamp: str
    signature: str = ""


@dataclass
class GovernanceOutcome:
    decision: PolicyDecision
    evidence: EvidenceEvent
    severe: bool
    simulated: bool


def _string_params(value: Any) -> list[str]:
    # Recurse through nested containers so a string buried in a sub-dict or
    # list cannot smuggle an injected instruction past the scanner.
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        collected: list[str] = []
        for inner in value.values():
            collected.extend(_string_params(inner))
        return collected
    if isinstance(value, (list, tuple, set)):
        collected = []
        for item in value:
            collected.extend(_string_params(item))
        return collected
    return []


def scan_for_injection(*texts: str | None) -> list[str]:
    """Return the injection/authority-assertion phrases found in ``texts``."""

    hits: list[str] = []
    for text in texts:
        if not text:
            continue
        lowered = text.lower()
        for pattern in INJECTION_PATTERNS:
            if pattern in lowered and pattern not in hits:
                hits.append(pattern)
    return hits


class MetasploitGovernor:
    def __init__(self, signing_key: str | None = None) -> None:
        self.signing_key = (
            signing_key or os.getenv("RIF_MSF_BROKER_KEY") or secrets.token_hex(32)
        )

    def mint_token(
        self,
        intent: MetasploitIntent,
        approver: str,
        ttl_seconds: int = 600,
    ) -> CapabilityToken:
        issued = datetime.now(UTC)
        token = CapabilityToken(
            capability=intent.capability,
            target=intent.target,
            scope_id=intent.scope_id,
            intent_hash=intent.intent_hash(),
            approver=approver,
            issued_at=issued,
            expires_at=issued + timedelta(seconds=ttl_seconds),
        )
        signature = hmac_signature(token.signing_payload(), self.signing_key)
        return token.model_copy(update={"signature": signature})

    def evaluate(
        self,
        intent: MetasploitIntent,
        *,
        mode: GovernanceMode = GovernanceMode.read_only_firewall,
        env_name: str = "RIF_Runtime",
        posture: Posture = Posture.normal,
        token: CapabilityToken | None = None,
        now: datetime | None = None,
    ) -> GovernanceOutcome:
        now = now or datetime.now(UTC)
        simulated = mode == GovernanceMode.shadow
        capability_class = classify(intent.capability)
        severe = is_severe(intent.capability)

        if posture == Posture.locked:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "runtime locked",
                "posture.locked",
                severe=False,
                simulated=simulated,
            )

        injection = scan_for_injection(
            intent.text,
            intent.untrusted_context,
            *_string_params(intent.params),
        )
        if injection:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                f"quarantined untrusted instruction: {', '.join(injection)}",
                "msf.injection.quarantined",
                severe=True,
                simulated=simulated,
            )

        if capability_class == CapabilityClass.read_only:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.allow,
                "read-only capability: security knowledge, not authority",
                "msf.capability.read_only",
                severe=False,
                simulated=simulated,
            )

        if mode == GovernanceMode.read_only_firewall:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "execution authority absent under read-only firewall",
                "msf.capability.execution_absent",
                severe=severe,
                simulated=simulated,
            )

        if mode == GovernanceMode.shadow:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "shadow lane: high-impact action simulated, never executed",
                "msf.shadow.denied",
                severe=severe,
                simulated=True,
            )

        return self._evaluate_broker(intent, env_name, posture, token, now, severe)

    def _evaluate_broker(
        self,
        intent: MetasploitIntent,
        env_name: str,
        posture: Posture,
        token: CapabilityToken | None,
        now: datetime,
        severe: bool,
    ) -> GovernanceOutcome:
        if token is None:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "no signed human approval token presented",
                "msf.broker.approval_absent",
                severe=severe,
                simulated=False,
            )

        expected = hmac_signature(token.signing_payload(), self.signing_key)
        if not token.signature or not hmac.compare_digest(token.signature, expected):
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "capability token signature invalid",
                "msf.broker.signature_invalid",
                severe=True,
                simulated=False,
            )

        if now >= token.expires_at:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "capability token expired: authority is time-bound",
                "msf.broker.token_expired",
                severe=severe,
                simulated=False,
            )

        if token.capability != intent.capability:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "token authorises a different capability class",
                "msf.broker.capability_mismatch",
                severe=severe,
                simulated=False,
            )

        if token.target != intent.target:
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "target not pinned to the approved lab asset",
                "msf.broker.target_pinned",
                severe=True,
                simulated=False,
            )

        if token.intent_hash != intent.intent_hash():
            return self._finish(
                intent,
                env_name,
                posture,
                Decision.deny,
                "signed intent hash no longer matches the request",
                "msf.broker.intent_mismatch",
                severe=True,
                simulated=False,
            )

        return self._finish(
            intent,
            env_name,
            posture,
            Decision.allow,
            "bounded lab action authorised by capability token",
            "msf.broker.authorized",
            severe=False,
            simulated=False,
        )

    def _finish(
        self,
        intent: MetasploitIntent,
        env_name: str,
        posture: Posture,
        decision: Decision,
        reason: str,
        rule: str,
        *,
        severe: bool,
        simulated: bool,
    ) -> GovernanceOutcome:
        policy_decision = PolicyDecision(
            decision=decision,
            actor=intent.actor,
            action=f"mcp.metasploit.{intent.capability}",
            target=intent.target,
            environment=env_name,
            posture=posture,
            reason=reason,
            matched_rule=rule,
        )
        return GovernanceOutcome(
            decision=policy_decision,
            evidence=self._sign_evidence(intent, policy_decision),
            severe=severe and decision == Decision.deny,
            simulated=simulated,
        )

    def _sign_evidence(
        self, intent: MetasploitIntent, decision: PolicyDecision
    ) -> EvidenceEvent:
        event = EvidenceEvent(
            decision_id=str(uuid4()),
            intent_hash=intent.intent_hash(),
            tool=intent.tool,
            requested_capability=intent.capability,
            policy_decision=decision.decision.value,
            scope_id=intent.scope_id,
            contract_hash=contract_hash(),
            matched_rule=decision.matched_rule,
            timestamp=decision.timestamp.isoformat(),
        )
        signature = hmac_signature(
            event.model_dump(exclude={"signature"}), self.signing_key
        )
        return event.model_copy(update={"signature": signature})

    def verify_evidence(self, event: EvidenceEvent) -> bool:
        expected = hmac_signature(
            event.model_dump(exclude={"signature"}), self.signing_key
        )
        return bool(event.signature) and hmac.compare_digest(event.signature, expected)
