from __future__ import annotations

import hashlib
import json
from typing import Any

from .openai_adapter import generate_structured
from .schemas import GuardedSecurityDraft, IntelligenceRequest, IntelligenceResponse


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _fallback(request: IntelligenceRequest) -> tuple[str, list[str], GuardedSecurityDraft | None]:
    warnings = ["OPENAI_API_KEY unavailable or model response rejected; deterministic fallback used."]
    if not request.evidence:
        warnings.append("Evidence is incomplete: no evidence items supplied.")
    snapshot = request.decision
    interpretation = (
        f"Deterministic RIF decision is {snapshot.decision.value}; rule {snapshot.rule_id} "
        f"applied under {snapshot.posture.value} posture. This intelligence output does not alter enforcement."
    )
    draft = None
    if request.mode.value in {"recon_plan", "finding_triage", "remediation_draft", "detection_rule_draft", "alert_enrichment", "report_draft"}:
        draft = GuardedSecurityDraft(
            title=f"Guarded {request.mode.value.replace('_', ' ')}",
            summary="Planning-only draft derived from deterministic RIF state.",
            recommended_steps=["Validate supplied evidence against approved scope.", "Submit any execution request to deterministic RIF policy evaluation."],
            constraints=["No execution commands.", "No autonomous tool invocation.", "Existing approval gates remain authoritative."],
            execution_commands=[],
        )
    return interpretation, warnings, draft


def generate_intelligence(request: IntelligenceRequest) -> IntelligenceResponse:
    input_payload = request.model_dump(mode="json")
    input_hash = _digest(input_payload)
    raw, model_used = generate_structured(input_payload)
    if raw is None:
        interpretation, warnings, draft = _fallback(request)
        source = "deterministic_fallback"
    else:
        try:
            draft = GuardedSecurityDraft.model_validate(raw["draft"]) if raw.get("draft") else None
            interpretation = str(raw["interpretation"])
            warnings = [str(item) for item in raw.get("warnings", [])]
            if not request.evidence:
                warnings.append("Evidence is incomplete: no evidence items supplied.")
            source = "llm_assisted"
        except (KeyError, ValueError, TypeError):
            interpretation, warnings, draft = _fallback(request)
            source = "deterministic_fallback"
            model_used = None
    output_material = {"interpretation": interpretation, "warnings": warnings, "draft": draft.model_dump() if draft else None}
    return IntelligenceResponse(
        mode=request.mode,
        decision=request.decision,
        source=source,
        model_used=model_used,
        input_hash=input_hash,
        output_hash=_digest(output_material),
        interpretation=interpretation,
        warnings=warnings,
        draft=draft,
    )
