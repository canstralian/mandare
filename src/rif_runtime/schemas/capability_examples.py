"""
Capability Manifest Examples for RIF Runtime

Real-world examples showing how to declare:
- shell command execution
- web search
- file write
- git push
- HTTP API call
"""

from rif_runtime.schemas.capability import (
    CapabilityManifest,
    SideEffectType,
    Replayability,
    EvidenceRequirement,
    NetworkAccessSpec,
    FilesystemAccessSpec,
    ExternalServiceSpec,
    CostEstimate,
    NetworkProtocol,
    AccessLevel,
)


# ============================================================================
# Example 1: Shell Command Execution
# ============================================================================

SHELL_COMMAND_MANIFEST = CapabilityManifest(
    name="shell_command",
    version="1.0.0",
    description="Execute arbitrary shell commands in a sandboxed environment",
    category="process",
    
    side_effects=[
        SideEffectType.PROCESS_EXECUTION,
        SideEffectType.ENVIRONMENT_MUTATION,
        SideEffectType.FILESYSTEM_WRITE,  # May write to temp
    ],
    mutates_state=True,  # Commands can have side effects
    
    network_access=NetworkAccessSpec(
        enabled=False,  # Base shell doesn't need network; can be added via pipes
        timeout_seconds=60,
    ),
    
    filesystem_access=FilesystemAccessSpec(
        enabled=True,
        access_level=AccessLevel.EXECUTE,
        allowed_paths=[
            "/tmp/**",
            "/home/user/workspace/**",
        ],
        blocked_paths=[
            "/etc/**",
            "/sys/**",
            "/proc/**",
            "/root/**",
        ],
        max_file_size_mb=500,
        max_total_size_mb=2000,
    ),
    
    external_services=[],
    
    timeout_seconds=60,
    max_retries=1,
    
    evidence_requirements=[
        EvidenceRequirement(
            name="command_invoked",
            format="text",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="stdout",
            format="text",
            sensitive=True,  # May contain secrets
            immutable=True,
        ),
        EvidenceRequirement(
            name="stderr",
            format="text",
            sensitive=True,
            immutable=True,
        ),
        EvidenceRequirement(
            name="exit_code",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="execution_time_ms",
            format="json",
            sensitive=False,
            immutable=True,
        ),
    ],
    
    replayability=Replayability.NON_DETERMINISTIC,  # Commands often have non-deterministic output
    
    cost_estimate=CostEstimate(
        api_calls=0,
        data_transfer_mb=0.0,
        compute_seconds=2.0,
        storage_mb=0.0,
        estimated_cost_usd=None,
    ),
    
    parameters={
        "command": {
            "type": "string",
            "description": "Shell command to execute",
            "minLength": 1,
            "maxLength": 10000,
        },
        "timeout": {
            "type": "integer",
            "description": "Execution timeout in seconds",
            "minimum": 1,
            "maximum": 300,
            "default": 30,
        },
        "cwd": {
            "type": "string",
            "description": "Working directory",
            "default": "/home/user/workspace",
        },
    },
    required_parameters=["command"],
    
    requires_approval=True,
    approval_reason="Arbitrary code execution is high-risk; must be explicitly approved",
    
    author="rif-team",
    tags=["execution", "shell", "dangerous", "high-risk"],
)


# ============================================================================
# Example 2: Web Search
# ============================================================================

WEB_SEARCH_MANIFEST = CapabilityManifest(
    name="web_search",
    version="1.0.0",
    description="Search the web using Google/Bing and return results",
    category="network",
    
    side_effects=[
        SideEffectType.NETWORK_EGRESS,
    ],
    mutates_state=False,  # No persistent side effects
    
    network_access=NetworkAccessSpec(
        enabled=True,
        protocols=[NetworkProtocol.HTTPS],
        allowed_domains=[
            "*.google.com",
            "*.bing.com",
            "*.duckduckgo.com",
        ],
        blocked_domains=[
            "169.254.169.254",  # AWS metadata
            "127.0.0.1",
        ],
        require_tls=True,
        timeout_seconds=15,
    ),
    
    filesystem_access=FilesystemAccessSpec(
        enabled=False,
    ),
    
    external_services=[
        ExternalServiceSpec(
            name="google",
            endpoint="https://www.google.com/search",
            auth_required=False,
            credentials_type=None,
            rate_limit=60,
            mutation_allowed=False,
        ),
    ],
    
    timeout_seconds=20,
    max_retries=2,
    
    evidence_requirements=[
        EvidenceRequirement(
            name="search_query",
            format="text",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="search_results",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="http_status_code",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="response_time_ms",
            format="json",
            sensitive=False,
            immutable=True,
        ),
    ],
    
    replayability=Replayability.NON_DETERMINISTIC,  # Search results may vary
    
    cost_estimate=CostEstimate(
        api_calls=1,
        data_transfer_mb=0.5,
        compute_seconds=0.5,
        storage_mb=0.0,
        estimated_cost_usd=0.0,  # Free tier
    ),
    
    parameters={
        "query": {
            "type": "string",
            "description": "Search query",
            "minLength": 1,
            "maxLength": 1000,
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "minimum": 1,
            "maximum": 100,
            "default": 10,
        },
        "language": {
            "type": "string",
            "description": "Language code (e.g., en, de, fr)",
            "default": "en",
        },
    },
    required_parameters=["query"],
    
    requires_approval=False,
    
    author="rif-team",
    tags=["search", "network", "read-only", "safe"],
)


# ============================================================================
# Example 3: File Write
# ============================================================================

FILE_WRITE_MANIFEST = CapabilityManifest(
    name="file_write",
    version="1.0.0",
    description="Write or append content to a file",
    category="filesystem",
    
    side_effects=[
        SideEffectType.FILESYSTEM_WRITE,
    ],
    mutates_state=True,
    
    network_access=NetworkAccessSpec(
        enabled=False,
    ),
    
    filesystem_access=FilesystemAccessSpec(
        enabled=True,
        access_level=AccessLevel.WRITE,
        allowed_paths=[
            "/home/user/workspace/**",
            "/tmp/**",
            "/app/data/**",
        ],
        blocked_paths=[
            "/etc/**",
            "/sys/**",
            "/root/**",
            "/proc/**",
        ],
        allowed_extensions=[".txt", ".json", ".yaml", ".py", ".md", ".csv"],
        max_file_size_mb=100,
        max_total_size_mb=500,
    ),
    
    external_services=[],
    
    timeout_seconds=10,
    max_retries=1,
    
    evidence_requirements=[
        EvidenceRequirement(
            name="file_path",
            format="text",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="mode",
            format="text",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="content_written",
            format="text",
            sensitive=True,
            immutable=True,
        ),
        EvidenceRequirement(
            name="file_size_before",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="file_size_after",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="content_hash",
            format="text",
            sensitive=False,
            immutable=True,
        ),
    ],
    
    replayability=Replayability.IDEMPOTENT,  # Can be replayed safely if mode is 'write'
    
    cost_estimate=CostEstimate(
        api_calls=0,
        data_transfer_mb=0.0,
        compute_seconds=0.1,
        storage_mb=0.05,
        estimated_cost_usd=None,
    ),
    
    parameters={
        "path": {
            "type": "string",
            "description": "File path to write to",
            "minLength": 1,
        },
        "content": {
            "type": "string",
            "description": "Content to write",
        },
        "mode": {
            "type": "string",
            "enum": ["write", "append"],
            "description": "Write mode (write=overwrite, append=add to end)",
            "default": "write",
        },
        "encoding": {
            "type": "string",
            "description": "File encoding",
            "default": "utf-8",
        },
    },
    required_parameters=["path", "content"],
    
    requires_approval=True,
    approval_reason="File writes must be explicitly approved to prevent accidental data loss",
    
    author="rif-team",
    tags=["filesystem", "write", "mutation", "requires-approval"],
)


# ============================================================================
# Example 4: Git Push
# ============================================================================

GIT_PUSH_MANIFEST = CapabilityManifest(
    name="git_push",
    version="1.0.0",
    description="Push commits to a Git repository",
    category="external_service",
    
    side_effects=[
        SideEffectType.EXTERNAL_SERVICE_MUTATION,
        SideEffectType.NETWORK_EGRESS,
        SideEffectType.CREDENTIAL_EXPOSURE,
    ],
    mutates_state=True,
    
    network_access=NetworkAccessSpec(
        enabled=True,
        protocols=[NetworkProtocol.SSH, NetworkProtocol.HTTPS],
        allowed_domains=[
            "*.github.com",
            "*.gitlab.com",
            "*.bitbucket.org",
        ],
        require_tls=True,
        timeout_seconds=60,
    ),
    
    filesystem_access=FilesystemAccessSpec(
        enabled=True,
        access_level=AccessLevel.READ,
        allowed_paths=[
            "/home/user/workspace/**",
            "/home/user/.ssh/**",  # SSH keys
        ],
        blocked_paths=[
            "/etc/**",
        ],
        max_file_size_mb=500,
    ),
    
    external_services=[
        ExternalServiceSpec(
            name="github",
            endpoint="https://github.com",
            auth_required=True,
            credentials_type="ssh_key",
            rate_limit=None,
            mutation_allowed=True,
        ),
    ],
    
    timeout_seconds=60,
    max_retries=2,
    
    evidence_requirements=[
        EvidenceRequirement(
            name="repository_url",
            format="text",
            sensitive=True,  # May contain credentials
            immutable=True,
        ),
        EvidenceRequirement(
            name="branch",
            format="text",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="commits_pushed",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="push_output",
            format="text",
            sensitive=True,
            immutable=True,
        ),
        EvidenceRequirement(
            name="commit_hashes",
            format="json",
            sensitive=False,
            immutable=True,
        ),
    ],
    
    replayability=Replayability.NON_IDEMPOTENT,  # Can't safely replay (creates duplicate commits)
    
    cost_estimate=CostEstimate(
        api_calls=1,
        data_transfer_mb=10.0,
        compute_seconds=5.0,
        storage_mb=0.0,
        estimated_cost_usd=None,
    ),
    
    parameters={
        "repo_path": {
            "type": "string",
            "description": "Local repository path",
            "minLength": 1,
        },
        "branch": {
            "type": "string",
            "description": "Branch to push to",
            "default": "main",
        },
        "remote": {
            "type": "string",
            "description": "Remote name",
            "default": "origin",
        },
        "force": {
            "type": "boolean",
            "description": "Use force push (dangerous)",
            "default": False,
        },
    },
    required_parameters=["repo_path"],
    
    requires_approval=True,
    approval_reason="Git push mutates repository and must be explicitly approved",
    
    author="rif-team",
    tags=["git", "network", "mutation", "credential-sensitive", "requires-approval"],
)


# ============================================================================
# Example 5: HTTP API Call
# ============================================================================

HTTP_API_CALL_MANIFEST = CapabilityManifest(
    name="http_api_call",
    version="1.0.0",
    description="Make HTTP/HTTPS requests to APIs",
    category="network",
    
    side_effects=[
        SideEffectType.NETWORK_EGRESS,
    ],
    mutates_state=False,  # Base HTTP is read-only (depends on endpoint)
    
    network_access=NetworkAccessSpec(
        enabled=True,
        protocols=[NetworkProtocol.HTTP, NetworkProtocol.HTTPS],
        allowed_domains=[],  # Empty = require explicit policy allowlist
        blocked_domains=[
            "169.254.169.254",  # AWS metadata
            "127.0.0.1",
            "169.254.169.253",  # Azure metadata
        ],
        require_tls=True,
        timeout_seconds=30,
    ),
    
    filesystem_access=FilesystemAccessSpec(
        enabled=False,
    ),
    
    external_services=[
        ExternalServiceSpec(
            name="arbitrary_api",
            endpoint="*",
            auth_required=False,
            credentials_type=None,
            rate_limit=None,
            mutation_allowed=True,  # Depends on method
        ),
    ],
    
    timeout_seconds=30,
    max_retries=2,
    
    evidence_requirements=[
        EvidenceRequirement(
            name="http_method",
            format="text",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="http_url",
            format="text",
            sensitive=True,  # May contain tokens in query params
            immutable=True,
        ),
        EvidenceRequirement(
            name="http_headers",
            format="json",
            sensitive=True,  # May contain Authorization
            immutable=True,
        ),
        EvidenceRequirement(
            name="http_request_body",
            format="text",
            sensitive=True,
            immutable=True,
        ),
        EvidenceRequirement(
            name="http_status_code",
            format="json",
            sensitive=False,
            immutable=True,
        ),
        EvidenceRequirement(
            name="http_response_body",
            format="text",
            sensitive=True,
            immutable=True,
        ),
        EvidenceRequirement(
            name="response_time_ms",
            format="json",
            sensitive=False,
            immutable=True,
        ),
    ],
    
    replayability=Replayability.NON_DETERMINISTIC,  # API responses vary
    
    cost_estimate=CostEstimate(
        api_calls=1,
        data_transfer_mb=1.0,
        compute_seconds=0.5,
        storage_mb=0.0,
        estimated_cost_usd=None,
    ),
    
    parameters={
        "url": {
            "type": "string",
            "description": "API endpoint URL",
            "format": "uri",
            "minLength": 1,
        },
        "method": {
            "type": "string",
            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "description": "HTTP method",
            "default": "GET",
        },
        "headers": {
            "type": "object",
            "description": "HTTP headers",
            "default": {},
        },
        "body": {
            "type": "object",
            "description": "Request body (for POST/PUT/PATCH)",
        },
        "timeout": {
            "type": "integer",
            "description": "Request timeout in seconds",
            "minimum": 1,
            "maximum": 300,
            "default": 30,
        },
        "verify_ssl": {
            "type": "boolean",
            "description": "Verify SSL certificates",
            "default": True,
        },
    },
    required_parameters=["url"],
    
    requires_approval=False,  # Depends on URL; policy should gate
    
    author="rif-team",
    tags=["network", "api", "http", "read-heavy"],
)


# ============================================================================
# Summary: All Examples
# ============================================================================

EXAMPLES = {
    "shell_command": SHELL_COMMAND_MANIFEST,
    "web_search": WEB_SEARCH_MANIFEST,
    "file_write": FILE_WRITE_MANIFEST,
    "git_push": GIT_PUSH_MANIFEST,
    "http_api_call": HTTP_API_CALL_MANIFEST,
}


if __name__ == "__main__":
    """Print all examples as JSON for reference."""
    import json
    
    for name, manifest in EXAMPLES.items():
        print(f"\n{'='*80}")
        print(f"CAPABILITY: {name.upper()}")
        print(f"{'='*80}")
        print(json.dumps(manifest.model_dump(), indent=2, default=str))
