"""
Capability Manifest Schema for RIF Runtime

Represents tools and side effects as explicit, auditable, policy-evaluable capabilities.
Manifests declare all observable behaviors to enable governance and replay.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, validator


class AccessLevel(str, Enum):
    """Access level for resource operations."""

    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class NetworkProtocol(str, Enum):
    """Supported network protocols."""

    HTTP = "http"
    HTTPS = "https"
    SSH = "ssh"
    DNS = "dns"
    WEBSOCKET = "websocket"
    GRPC = "grpc"


class SideEffectType(str, Enum):
    """Types of side effects a capability can have."""

    NETWORK_EGRESS = "network_egress"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"
    PROCESS_EXECUTION = "process_execution"
    ENVIRONMENT_MUTATION = "environment_mutation"
    EXTERNAL_SERVICE_MUTATION = "external_service_mutation"
    CREDENTIAL_EXPOSURE = "credential_exposure"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class Replayability(str, Enum):
    """How repeatable a capability is."""

    DETERMINISTIC = "deterministic"  # Same input → same output, safe to replay
    IDEMPOTENT = "idempotent"  # Safe to replay (e.g., mkdir -p)
    NON_IDEMPOTENT = "non_idempotent"  # Replay may have different effects
    NON_DETERMINISTIC = "non_deterministic"  # Output varies (e.g., curl with random)
    NON_REPLAYABLE = "non_replayable"  # Cannot safely replay (e.g., rm)


class EvidenceRequirement(BaseModel):
    """Evidence that must be captured for auditability."""

    name: str = Field(
        ...,
        description=(
            "Evidence artifact name (e.g., 'http_request', "
            "'file_written', 'process_output')"
        ),
    )
    format: Literal["json", "text", "binary", "structured"] = Field(
        default="json",
        description="Format of evidence artifact",
    )
    sensitive: bool = Field(
        default=False,
        description=(
            "Whether evidence may contain credentials/PII (redact before logging)"
        ),
    )
    immutable: bool = Field(
        default=True,
        description=(
            "Whether evidence must be cryptographically signed for audit trail"
        ),
    )


class NetworkAccessSpec(BaseModel):
    """Declares network access patterns."""

    enabled: bool = Field(
        default=False, description="Whether capability requires network access"
    )
    protocols: list[NetworkProtocol] = Field(
        default_factory=list,
        description="Allowed protocols (HTTP, HTTPS, SSH, DNS, WebSocket, gRPC)",
    )
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="Whitelist of allowed domains/IPs (CIDR notation supported)",
    )
    blocked_domains: list[str] = Field(
        default_factory=list,
        description="Blacklist of blocked domains/IPs (e.g., metadata services)",
    )
    require_tls: bool = Field(
        default=True, description="Whether TLS verification is required"
    )
    dns_only: bool = Field(
        default=False,
        description="Whether capability only performs DNS lookups (no HTTP/SSH)",
    )
    timeout_seconds: int = Field(default=30, description="Network operation timeout")


class FilesystemAccessSpec(BaseModel):
    """Declares filesystem access patterns."""

    enabled: bool = Field(
        default=False, description="Whether capability accesses filesystem"
    )
    access_level: AccessLevel = Field(
        default=AccessLevel.NONE,
        description="Access level (read, write, execute, admin)",
    )
    allowed_paths: list[str] = Field(
        default_factory=list,
        description="Whitelist of allowed paths (glob patterns supported)",
    )
    blocked_paths: list[str] = Field(
        default_factory=list,
        description="Blacklist of blocked paths (e.g., /etc, /sys)",
    )
    allowed_extensions: list[str] = Field(
        default_factory=list, description="Allowed file extensions (.py, .json, etc.)"
    )
    max_file_size_mb: int = Field(
        default=100, description="Maximum file size for operations"
    )
    max_total_size_mb: int = Field(
        default=1000, description="Maximum total data written in one execution"
    )


class ExternalServiceSpec(BaseModel):
    """Declares external service integrations."""

    name: str = Field(
        ..., description="Service name (e.g., 'github', 'aws_s3', 'slack')"
    )
    endpoint: str = Field(..., description="Service endpoint URL or identifier")
    auth_required: bool = Field(
        default=True, description="Whether authentication is required"
    )
    credentials_type: str | None = Field(
        default=None,
        description=(
            "Type of credentials (api_key, oauth_token, username_password, etc.)"
        ),
    )
    rate_limit: int | None = Field(
        default=None, description="Calls per minute limit (if known)"
    )
    mutation_allowed: bool = Field(
        default=False, description="Whether capability can mutate state (not just read)"
    )


class CostEstimate(BaseModel):
    """Cost implications of running the capability."""

    api_calls: int = Field(
        default=1, description="Estimated number of external API calls"
    )
    data_transfer_mb: float = Field(
        default=0.0, description="Estimated data transfer in MB"
    )
    compute_seconds: float = Field(
        default=1.0, description="Estimated compute time in seconds"
    )
    storage_mb: float = Field(
        default=0.0, description="Estimated persistent storage in MB"
    )
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated cost in USD (if applicable)"
    )


class CapabilityManifest(BaseModel):
    """
    Complete capability manifest for RIF Runtime.

    Declares all observable behaviors, side effects, access patterns, and evidence.
    Used for policy evaluation, execution sandboxing, and audit trail.
    """

    # Identity
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Capability name (e.g., 'shell_command', 'github_push')",
    )
    version: str = Field(default="1.0.0", description="Semantic version of capability")
    description: str = Field(
        ..., description="Human-readable description of what the capability does"
    )

    # Categorization
    category: Literal[
        "network",
        "filesystem",
        "process",
        "credential",
        "system",
        "external_service",
        "data_processing",
    ] = Field(..., description="Primary category of capability")

    # Side Effects
    side_effects: list[SideEffectType] = Field(
        default_factory=list, description="List of all observable side effects"
    )
    mutates_state: bool = Field(
        default=False,
        description="Whether capability mutates external state (not idempotent)",
    )

    # Access Patterns
    network_access: NetworkAccessSpec = Field(
        default_factory=NetworkAccessSpec,
        description="Network access patterns and restrictions",
    )
    filesystem_access: FilesystemAccessSpec = Field(
        default_factory=FilesystemAccessSpec,
        description="Filesystem access patterns and restrictions",
    )
    external_services: list[ExternalServiceSpec] = Field(
        default_factory=list,
        description="External services this capability integrates with",
    )

    # Execution Constraints
    timeout_seconds: int = Field(
        default=30, ge=1, le=3600, description="Maximum execution time"
    )
    max_retries: int = Field(
        default=3, ge=0, description="Maximum retry attempts on failure"
    )

    # Auditability
    evidence_requirements: list[EvidenceRequirement] = Field(
        default_factory=list,
        description="Evidence artifacts that must be captured for audit",
    )
    replayability: Replayability = Field(
        default=Replayability.DETERMINISTIC,
        description="How safely this capability can be replayed",
    )

    # Cost & Performance
    cost_estimate: CostEstimate = Field(
        default_factory=CostEstimate, description="Cost and performance implications"
    )

    # Input Parameters
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameter schema (JSON Schema compatible)",
    )
    required_parameters: list[str] = Field(
        default_factory=list, description="Required parameter names"
    )

    # Governance
    requires_approval: bool = Field(
        default=False,
        description="Whether policy must explicitly approve before execution",
    )
    approval_reason: str | None = Field(
        default=None, description="Why approval is required (e.g., 'data deletion')"
    )

    # Metadata
    author: str = Field(
        default="rif-team", description="Author/maintainer of this capability"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization and discovery"
    )

    # Validation
    @validator("version")
    def validate_version(cls, v: str) -> str:
        """Ensure semantic versioning."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+", v):
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v

    @validator("side_effects", pre=True, always=True)
    def validate_side_effects(
        cls, v: list[SideEffectType], values: dict[str, Any]
    ) -> list[SideEffectType]:
        """Validate side effects are appropriate for category."""
        if not v:
            return v

        category = values.get("category")
        allowed_for_category = {
            "network": [SideEffectType.NETWORK_EGRESS],
            "filesystem": [
                SideEffectType.FILESYSTEM_WRITE,
                SideEffectType.FILESYSTEM_DELETE,
            ],
            "process": [
                SideEffectType.PROCESS_EXECUTION,
                SideEffectType.ENVIRONMENT_MUTATION,
            ],
            "credential": [SideEffectType.CREDENTIAL_EXPOSURE],
            "system": [SideEffectType.PRIVILEGE_ESCALATION],
            "external_service": [SideEffectType.EXTERNAL_SERVICE_MUTATION],
            "data_processing": [],
        }

        if category in allowed_for_category:
            expected = set(allowed_for_category[category])
            actual = set(v)
            if not actual.issubset(expected | {SideEffectType.ENVIRONMENT_MUTATION}):
                raise ValueError(
                    f"Side effects {actual} not appropriate for category {category}"
                )

        return v

    @validator("network_access")
    def validate_network_access(
        cls, v: NetworkAccessSpec, values: dict[str, Any]
    ) -> NetworkAccessSpec:
        """Ensure network access is declared if side effects indicate it."""
        side_effects = values.get("side_effects", [])
        if SideEffectType.NETWORK_EGRESS in side_effects and not v.enabled:
            raise ValueError(
                "network_access.enabled must be True if NETWORK_EGRESS in side_effects"
            )
        return v

    @validator("filesystem_access")
    def validate_filesystem_access(
        cls, v: FilesystemAccessSpec, values: dict[str, Any]
    ) -> FilesystemAccessSpec:
        """Ensure filesystem access is declared if side effects indicate it."""
        side_effects = values.get("side_effects", [])
        fs_effects = {
            SideEffectType.FILESYSTEM_WRITE,
            SideEffectType.FILESYSTEM_DELETE,
        }
        if (fs_effects & set(side_effects)) and not v.enabled:
            raise ValueError(
                "filesystem_access.enabled must be True if filesystem "
                "side effects present"
            )
        return v

    @validator("replayability")
    def validate_replayability(
        cls, v: Replayability, values: dict[str, Any]
    ) -> Replayability:
        """Validate replayability vs mutates_state."""
        mutates = values.get("mutates_state", False)
        if mutates and v == Replayability.DETERMINISTIC:
            raise ValueError(
                "Capability that mutates state cannot be DETERMINISTIC replayable"
            )
        return v


# Backward-compatible alias
CapabilitySpec = CapabilityManifest
