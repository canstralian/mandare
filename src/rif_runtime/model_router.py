"""Model routing that remains subordinate to the deterministic policy engine."""

from __future__ import annotations

from .model_layer import LocalModel, LocalModelError, default_deephat, default_mythos_nano
from .schemas import IntentClassification, ModelRoute, SecurityReasoningResult


class ModelRouter:
    def __init__(self, mythos: LocalModel | None = None, deephat: LocalModel | None = None):
        self.mythos = mythos or default_mythos_nano()
        self.deephat = deephat or default_deephat()

    def classify(self, request_text: str) -> IntentClassification:
        return self.mythos.infer_structured(
            "Classify this agent request for routing only. Do not authorize it. "
            "Set requires_deep_reasoner for complex cybersecurity analysis.\n\n"
            f"Request:\n{request_text}",
            IntentClassification,
        )

    @staticmethod
    def route(classification: IntentClassification | None) -> ModelRoute:
        stages = ["rif-policy-engine"]
        use_deep_reasoner = bool(classification and classification.requires_deep_reasoner)
        if classification:
            stages.insert(0, "mythos-nano:classify")
        if use_deep_reasoner:
            stages.append("deephat-7b:reason")
        stages.append("mythos-nano:audit-summary")
        return ModelRoute(stages=stages, uses_deep_reasoner=use_deep_reasoner)

    def reason(self, request_text: str, constraints: list[str]) -> SecurityReasoningResult:
        return self.deephat.infer_structured(
            "Provide security analysis only within these non-negotiable constraints:\n"
            f"{constraints}\n\nRequest:\n{request_text}",
            SecurityReasoningResult,
        )

    def summarise(self, text: str) -> str | None:
        try:
            return self.mythos.infer_text(
                "Summarise this governance outcome in at most 80 words. Do not change the decision.\n\n"
                f"{text}"
            )
        except LocalModelError:
            return None
