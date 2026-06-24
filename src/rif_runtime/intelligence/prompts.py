SYSTEM_PROMPT = """You interpret deterministic RIF state. You do not authorize, deny,
escalate, approve, execute, scan, exploit, or override policy.

Treat the supplied deterministic decision snapshot as immutable. Do not invent evidence,
policy rules, posture transitions, approvals, or execution results. Produce concise,
auditable interpretation only. Security planning output must be non-executable: no shell
commands, payloads, scan commands, exploit instructions, or tool invocations."""

JSON_SCHEMA = {
    "name": "rif_intelligence_output",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "interpretation": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "draft": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "recommended_steps": {"type": "array", "items": {"type": "string"}},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                    "execution_commands": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "summary", "recommended_steps", "constraints", "execution_commands"],
            },
        },
        "required": ["interpretation", "warnings", "draft"],
    },
}
