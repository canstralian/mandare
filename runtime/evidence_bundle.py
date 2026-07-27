from dataclasses import dataclass


@dataclass
class EvidenceBundle:
    context: dict
    evidence: dict
    telemetry: dict
    replay: dict

    @classmethod
    def from_execution(cls, record):
        return cls(
            context={
                "intent": record.intent,
                "context": record.context,
            },
            evidence={
                "execution_id": record.id,
                "provider": record.provider,
            },
            telemetry={
                "provider": record.provider,
                "latency_ms": record.latency_ms,
                "timestamp": record.timestamp,
            },
            replay={
                "replay": record.to_dict(),
            },
        )

