"""Capability taxonomy for Metasploit-class MCP tools.

The central RIF invariant is that *intent is not authority*. To enforce it for
a Metasploit MCP bridge we classify every concrete tool capability into one of
three bands and deny by default: only capabilities that read security
knowledge (never mutating target, session, or control-plane state) are treated
as non-consequential. Everything else — and anything unrecognised — carries
authority and is denied unless a valid, time-bound, dual-authorised broker
token is presented.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from ..security import sha256_digest

CONTRACT_VERSION = "msf-governance/v1"


class CapabilityClass(StrEnum):
    """How much authority a Metasploit MCP capability carries."""

    read_only = "read_only"
    consequential = "consequential"
    unknown = "unknown"


# Non-consequential knowledge/recon queries. These read security *knowledge*;
# they never mutate target, session, datastore, or control-plane state. These
# are the only capabilities the read-only firewall permits.
READ_ONLY_CAPABILITIES: frozenset[str] = frozenset(
    {
        "module.search",
        "module.info",
        "module.metadata",
        "module.options",
        "module.references",
        "module.compatible",
        "remediation.context",
        "recon.read",
        "recon.lab_data",
    }
)

# Consequential capabilities carry execution or mutation *authority*. Denied by
# the firewall and shadow lanes; permitted only through the broker with a valid
# capability token.
CONSEQUENTIAL_CAPABILITIES: frozenset[str] = frozenset(
    {
        "module.execute",
        "module.run",
        "exploit.run",
        "payload.generate",
        "handler.create",
        "listener.create",
        "session.create",
        "session.interact",
        "session.list",
        "route.add",
        "datastore.set",
        "target.set",
    }
)

# Consequential capabilities whose denial is *severe*: creating a persistent
# foothold, widening scope beyond a pinned asset, or exporting data/artifacts
# off the control plane. A severe denial escalates posture immediately rather
# than only counting toward the reflexive denial threshold.
SEVERE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "session.create",
        "session.interact",
        "handler.create",
        "listener.create",
        "route.add",
        "scope.widen",
        "credentials.export",
        "artifact.export",
        "payload.export",
        "loot.export",
    }
)


def normalize(capability: str) -> str:
    return capability.strip().lower()


def classify(capability: str) -> CapabilityClass:
    normalized = normalize(capability)
    if normalized in READ_ONLY_CAPABILITIES:
        return CapabilityClass.read_only
    if normalized in CONSEQUENTIAL_CAPABILITIES or normalized in SEVERE_CAPABILITIES:
        return CapabilityClass.consequential
    return CapabilityClass.unknown


def is_severe(capability: str) -> bool:
    return normalize(capability) in SEVERE_CAPABILITIES


def contract_hash() -> str:
    """Stable digest of the governance contract this taxonomy encodes.

    Pinned into every evidence event so a decision can be replayed against the
    exact capability contract that produced it.
    """

    return sha256_digest(
        {
            "version": CONTRACT_VERSION,
            "read_only": sorted(READ_ONLY_CAPABILITIES),
            "consequential": sorted(CONSEQUENTIAL_CAPABILITIES),
            "severe": sorted(SEVERE_CAPABILITIES),
        }
    )


def capability_catalog() -> dict[str, Any]:
    """Human-readable taxonomy for the ``explain`` surface."""

    return {
        "contract_version": CONTRACT_VERSION,
        "contract_hash": contract_hash(),
        "read_only": sorted(READ_ONLY_CAPABILITIES),
        "consequential": sorted(CONSEQUENTIAL_CAPABILITIES),
        "severe": sorted(SEVERE_CAPABILITIES),
    }
