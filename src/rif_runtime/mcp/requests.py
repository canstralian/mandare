"""Request bodies for the Metasploit MCP routes.

Kept beside the governor rather than in ``api.py`` so the route module stays
route wiring, and so the wire contract sits next to the domain types it wraps.
FastAPI validates these before the handler runs, which is what turns a
malformed body into a 422 instead of a partially-parsed intent.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .metasploit import CapabilityToken, GovernanceMode, MetasploitIntent

# Upper bound on capability-token lifetime. Authority is time-bound by design;
# an unbounded ttl_seconds would let one approval mint a effectively permanent
# execution grant.
MAX_TOKEN_TTL_SECONDS = 3600


class MetasploitEvaluateRequest(BaseModel):
    intent: MetasploitIntent
    mode: GovernanceMode = GovernanceMode.read_only_firewall
    token: CapabilityToken | None = None


class MetasploitTokenRequest(BaseModel):
    intent: MetasploitIntent
    approver: str = "human:operator"
    ttl_seconds: int = Field(default=600, gt=0, le=MAX_TOKEN_TTL_SECONDS)
