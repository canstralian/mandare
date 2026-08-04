"""The Metasploit MCP governor: firewall, shadow harness, and lab broker.

Three governance lanes share one ordered decision procedure. The order of the
checks *is* the answer to "which authority bounds the agent?" questions that
auditors ask:

1. **Firewall** - pre-execution hard deny (posture gates, banned modules,
   IP target restrictions).  Evaluated first so we never even simulate
   something that policy forbids.
2. **Shadow Harness** - post-gate, pre-execution simulation.  If the runtime
   posture allows the intent, we still shadow-run it first and record the
   predicted blast radius.  Only then does the real execution proceed.
3. **Lab Broker** - dynamic lab provisioning for destructive intents that
   pass the firewall but whose blast radius is above the auto-approve
   threshold.

Capability tokens (short-lived, scoped authorisation) bridge human-in-the-loop
approval and agent autonomy: the operator mints a token for a specific intent,
and the agent can act within that scope without re-prompting.

Signing key stability
---------------------
Prior to this PR the signing key was generated fresh on every process start,
which broke webhook signature verification across restarts.  Now the key is
resolved via (highest priority first):

1. ``RIF_MSF_SIGNING_KEY`` env var (explicit, for operators who rotate keys).
2. HKDF derivation from ``RIF_SECRET_KEY`` (stable across restarts; requires
   only the app-level secret to be set).
3. Secure random fallback (legacy behaviour, logs a warning).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signing key derivation
# ---------------------------------------------------------------------------


def _derive_signing_key() -> str:
    """Resolve the webhook/event signing key.

    Priority:
      1. RIF_MSF_SIGNING_KEY env var (explicit operator override).
      2. HKDF(SHA-256) from RIF_SECRET_KEY (stable across restarts).
      3. Random fallback (logs warning; breaks cross-restart verification).
    """
    explicit = os.environ.get("RIF_MSF_SIGNING_KEY")
    if explicit:
        return explicit

    app_secret = os.environ.get("RIF_SECRET_KEY")
    if app_secret:
        # HKDF-Extract then Expand (RFC 5869), single output block.
        # Using stdlib hmac + hashlib (no new dependencies).
        prk = hmac.new(
            key=b"rif-msf-signing",  # salt (domain separation)
            msg=app_secret.encode(),
            digestmod=hashlib.sha256,
        ).digest()
        # Expand with info="msf-event-signing-v1"
        okm = hmac.new(
            key=prk,
            msg=b"msf-event-signing-v1" + b"\x01",
            digestmod=hashlib.sha256,
        ).digest()
        return okm.hex()

    logger.warning(
        "Neither RIF_MSF_SIGNING_KEY nor RIF_SECRET_KEY is set; "
        "generating an ephemeral signing key (will not survive restart)."
    )
    return secrets.token_hex(32)


# ---------------------------------------------------------------------------
# Enums & schemas
# ---------------------------------------------------------------------------


class GovernanceMode(StrEnum):
    """Operating modes for the Metasploit governor."""

    read_only_firewall = "read_only_firewall"
    shadow_harness = "shadow_harness"
    lab_broker = "lab_broker"
    full = "full"


class IntentSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class MetasploitIntent(BaseModel):
    """Structured representation of what an agent wants to do via Metasploit."""

    module: str
    target: str
    options: dict[str, Any] = {}
    reason: str | None = None
    severity: IntentSeverity = IntentSeverity.medium


class CapabilityToken(BaseModel):
    """Short-lived scoped authorisation token."""

    token_id: str
    intent_hash: str
    approver: str
    issued_at: float
    expires_at: float
    revoked: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.revoked and time.time() < self.expires_at


class GovernanceOutcome(BaseModel):
    """Result of a governance evaluation."""

    decision: str  # "allow", "deny", "simulate"
    evidence: list[str] = []
    simulated: bool = False
    severe: bool = False
    lab_required: bool = False


class GovernanceEvent(BaseModel):
    """Auditable event emitted after every governance decision."""

    event_id: str
    timestamp: str
    intent: MetasploitIntent
    outcome: GovernanceOutcome
    mode: GovernanceMode
    signature: str | None = None


# ---------------------------------------------------------------------------
# Governor
# ---------------------------------------------------------------------------


class MetasploitGovernor:
    """Central governance engine for Metasploit MCP operations."""

    # Modules unconditionally denied regardless of posture.
    BANNED_MODULES: frozenset[str] = frozenset(
        {
            "exploit/multi/handler",
            "post/multi/gather/ssh_creds",
            "exploit/windows/smb/ms17_010_eternalblue",
        }
    )

    # IP ranges never allowed as targets (CIDR-lite, /8 only for simplicity).
    BLOCKED_TARGET_PREFIXES: tuple[str, ...] = (
        "10.",
        "172.16.",
        "192.168.",
        "127.",
    )

    def __init__(self, posture: str = "normal") -> None:
        self.posture = posture
        self.signing_key: str = _derive_signing_key()
        self._event_log: list[GovernanceEvent] = []
        self._tokens: dict[str, CapabilityToken] = {}

    # ------------------------------------------------------------------
    # Firewall
    # ------------------------------------------------------------------

    def _check_firewall(self, intent: MetasploitIntent) -> GovernanceOutcome | None:
        """Hard-deny check. Returns an outcome only if denied."""
        if intent.module in self.BANNED_MODULES:
            return GovernanceOutcome(
                decision="deny",
                evidence=[f"module '{intent.module}' is banned by policy"],
                severe=True,
            )

        if self.posture in ("restricted", "locked"):
            return GovernanceOutcome(
                decision="deny",
                evidence=[
                    f"posture '{self.posture}' blocks all Metasploit operations"
                ],
                severe=False,
            )

        for prefix in self.BLOCKED_TARGET_PREFIXES:
            if intent.target.startswith(prefix):
                return GovernanceOutcome(
                    decision="deny",
                    evidence=[
                        f"target '{intent.target}' is in a blocked IP range"
                    ],
                    severe=True,
                )

        return None  # No firewall objection

    # ------------------------------------------------------------------
    # Shadow Harness
    # ------------------------------------------------------------------

    def _shadow_simulate(self, intent: MetasploitIntent) -> GovernanceOutcome:
        """Simulate the intent and assess blast radius."""
        is_severe = intent.severity in (IntentSeverity.high, IntentSeverity.critical)
        return GovernanceOutcome(
            decision="simulate",
            evidence=[
                f"shadow simulation of '{intent.module}' against '{intent.target}'",
                f"severity={intent.severity.value}",
            ],
            simulated=True,
            severe=is_severe,
            lab_required=is_severe,
        )

    # ------------------------------------------------------------------
    # Lab Broker
    # ------------------------------------------------------------------

    def _assess_lab_need(
        self, intent: MetasploitIntent, shadow: GovernanceOutcome
    ) -> GovernanceOutcome:
        """Decide whether a lab environment is required."""
        if shadow.lab_required:
            return GovernanceOutcome(
                decision="deny",
                evidence=shadow.evidence
                + ["lab environment required but not provisioned"],
                severe=shadow.severe,
                lab_required=True,
                simulated=True,
            )
        return GovernanceOutcome(
            decision="allow",
            evidence=shadow.evidence + ["blast radius acceptable; proceeding"],
            simulated=True,
            severe=False,
        )

    # ------------------------------------------------------------------
    # Capability tokens
    # ------------------------------------------------------------------

    def _intent_hash(self, intent: MetasploitIntent) -> str:
        """Deterministic hash of an intent for token binding."""
        payload = f"{intent.module}:{intent.target}:{sorted(intent.options.items())}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def mint_token(
        self,
        intent: MetasploitIntent,
        approver: str = "human:operator",
        ttl_seconds: int = 600,
    ) -> CapabilityToken:
        """Mint a scoped capability token for a specific intent."""
        now = time.time()
        token = CapabilityToken(
            token_id=secrets.token_hex(16),
            intent_hash=self._intent_hash(intent),
            approver=approver,
            issued_at=now,
            expires_at=now + ttl_seconds,
        )
        self._tokens[token.token_id] = token
        return token

    def _validate_token(
        self, intent: MetasploitIntent, token: CapabilityToken | None
    ) -> bool:
        """Validate that a token authorises this specific intent."""
        if token is None:
            return False
        stored = self._tokens.get(token.token_id)
        if stored is None or not stored.is_valid:
            return False
        return stored.intent_hash == self._intent_hash(intent)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        intent: MetasploitIntent,
        mode: GovernanceMode = GovernanceMode.full,
        token: CapabilityToken | None = None,
    ) -> GovernanceOutcome:
        """Run the full governance pipeline for an intent."""

        # Step 0: valid capability token bypasses shadow + lab (but not firewall).
        has_token = self._validate_token(intent, token)

        # Step 1: Firewall (always runs).
        firewall_result = self._check_firewall(intent)
        if firewall_result is not None:
            self._record_event(intent, firewall_result, mode)
            return firewall_result

        if mode == GovernanceMode.read_only_firewall:
            outcome = GovernanceOutcome(
                decision="allow", evidence=["firewall passed (read-only mode)"]
            )
            self._record_event(intent, outcome, mode)
            return outcome

        # Step 2: Shadow harness.
        shadow = self._shadow_simulate(intent)
        if mode == GovernanceMode.shadow_harness:
            self._record_event(intent, shadow, mode)
            return shadow

        # Step 3: Lab broker (skipped if valid token held).
        if has_token:
            outcome = GovernanceOutcome(
                decision="allow",
                evidence=shadow.evidence + ["capability token valid; lab bypassed"],
                simulated=True,
                severe=False,
            )
        else:
            outcome = self._assess_lab_need(intent, shadow)

        self._record_event(intent, outcome, mode)
        return outcome

    # ------------------------------------------------------------------
    # Event recording
    # ------------------------------------------------------------------

    def _compute_signature(
        self, payload: dict[str, Any], key: str
    ) -> str:
        """HMAC-SHA256 signature over the JSON-serialised event payload."""
        import json as _json

        canonical = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            key.encode(), canonical.encode(), hashlib.sha256
        ).hexdigest()

    def _record_event(
        self,
        intent: MetasploitIntent,
        outcome: GovernanceOutcome,
        mode: GovernanceMode,
    ) -> None:
        """Record an auditable governance event with HMAC signature."""
        event = GovernanceEvent(
            event_id=secrets.token_hex(8),
            timestamp=datetime.now(timezone.utc).isoformat(),
            intent=intent,
            outcome=outcome,
            mode=mode,
        )
        # Sign the event (excluding the signature field itself).
        sig = self._compute_signature(
            event.model_dump(exclude={"signature"}), self.signing_key
        )
        event.signature = sig
        self._event_log.append(event)

    @property
    def event_log(self) -> list[GovernanceEvent]:
        return list(self._event_log)

    def verify_event(self, event: GovernanceEvent) -> bool:
        """Verify the HMAC signature of a recorded event."""
        expected = self._compute_signature(
            event.model_dump(exclude={"signature"}), self.signing_key
        )
        return bool(event.signature) and hmac.compare_digest(
            event.signature, expected
        )
