from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import ValidationError

from .openai_adapter import REDACTION_POLICY_VERSION, generate_structured, redact_secrets
from .schemas import GuardedSecurityDraft, IntelligenceRequest, IntelligenceResponse


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _fallback(
    request: IntelligenceRequest,
    *,
    egress_permitted: bool,
) -> tuple[str, list[str], GuardedSecurityDraft | None]:
    if egress_permitted:
        warnings = [
            "Provider response was unavailable or rejected; deterministic fallback used."
        ]
    else:
        warnings = [
            "Provider egress is disabled until a RIF policy-backed provider-access "
            "guard permits it; deterministic fallback used."
        ]

    if not request.evidence:
        warnings.append("Evidence is incomplete: no evidence items supplied.")

    snapshot = request.decision
    interpretation = (
        f"Supplied decision snapshot reports {snapshot.decision.value}; rule "
        f"{snapshot.rule_id} is associated with {snapshot.posture.value} posture. "
        "This response is advisory only and does not alter RIF enforcement."
    )

    draft = None
    planning_modes = {
        "recon_plan",
        "finding_triage",
        "remediation_draft",
        "detection_rule_draft",
        "alert_enrichment",
        "report_draft",
    }
    if request.mode.value in planning_modes:
        draft = GuardedSecurityDraft(
            title=f"Guarded {request.mode.value.replace('_', ' ')}",
            summary="Planning-only draft derived from supplied RIF context.",
            recommended_steps=[
                "Validate supplied evidence against approved scope.",
                "Submit any execution request to deterministic RIF policy evaluation.",
            ],
            constraints=[
                "No execution commands.",
                "No autonomous tool invocation.",
                "Existing approval gates remain authoritative.",
            ],
            execution_commands=[],
        )
    return interpretation, warnings, draft


def generate_intelligence(
    request: IntelligenceRequest,
    *,
    egress_permitted: bool = False,
) -> IntelligenceResponse:
    """Generate advisory output without granting authority or accidental cloud egress."""
    input_payload = request.model_dump(mode="json")
    redacted_input_payload = redact_secrets(input_payload)
    input_hash = _digest(redacted_input_payload)
    raw, model_used = generate_structured(
        redacted_input_payload,
        egress_permitted=egress_permitted,
    )

    source: Literal["llm_assisted", "deterministic_fallback"]
    if raw is None:
        interpretation, warnings, draft = _fallback(
            request,
            egress_permitted=egress_permitted,
        )
        source = "deterministic_fallback"
    else:
        try:
            draft = (
                GuardedSecurityDraft.model_validate(raw["draft"])
                if raw.get("draft")
                else None
            )
            interpretation = str(raw["interpretation"])
            warnings = [str(item) for item in raw.get("warnings", [])]
            if not request.evidence:
                warnings.append("Evidence is incomplete: no evidence items supplied.")
            source = "llm_assisted"
        except (KeyError, TypeError, ValidationError, ValueError):
            interpretation, warnings, draft = _fallback(
                request,
                egress_permitted=egress_permitted,
            )
            source = "deterministic_fallback"
            model_used = None

    output_material = {
        "mode": request.mode.value,
        "source": source,
        "model_used": model_used,
        "decision_verified": False,
        "redaction_policy_version": REDACTION_POLICY_VERSION,
        "interpretation": interpretation,
        "warnings": warnings,
        "draft": draft.model_dump() if draft else None,
    }

    return IntelligenceResponse(
        mode=request.mode,
        decision=request.decision,
        decision_verified=False,
        source=source,
        model_used=model_used,
        redaction_policy_version=REDACTION_POLICY_VERSION,
        input_hash=input_hash,
        output_hash=_digest(output_material),
        interpretation=interpretation,
        warnings=warnings,
        draft=draft,
    )
