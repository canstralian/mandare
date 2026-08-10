"""
RIF Runtime v1.0 - Test Strategy for Deterministic Replay

Guarantees that policy decisions, evidence, and governance graph can be
replayed consistently across Linux, Windows, and macOS with byte-for-byte
identical hashes and serialization.
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pydantic import BaseModel


# ============================================================================
# Test Matrix Definition
# ============================================================================

class OS(str, Enum):
    """Operating systems to test."""
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"


class PythonVersion(str, Enum):
    """Python versions to test."""
    PY_312 = "3.12"
    PY_313 = "3.13"


class SerializationFormat(str, Enum):
    """Serialization formats for determinism testing."""
    JSON = "json"
    MSGPACK = "msgpack"
    CBOR = "cbor"
    PROTOBUF = "protobuf"


@dataclass
class TestMatrix:
    """
    Complete test matrix for deterministic replay.
    
    Covers all OS x Python version combinations.
    """
    
    # Primary matrix (tested in CI)
    PRIMARY = [
        ("linux", "3.12", "json"),      # Linux + latest Python + JSON (primary)
        ("linux", "3.13", "json"),      # Linux + Python 3.13
        ("windows", "3.12", "json"),    # Windows + Python 3.12
        ("macos", "3.12", "json"),      # macOS + Python 3.12
    ]
    
    # Extended matrix (tested on release)
    EXTENDED = PRIMARY + [
        ("linux", "3.12", "msgpack"),
        ("windows", "3.12", "msgpack"),
        ("macos", "3.12", "msgpack"),
    ]
    
    # Full matrix (tested nightly)
    FULL = EXTENDED + [
        ("linux", "3.13", "msgpack"),
        ("windows", "3.13", "msgpack"),
        ("macos", "3.13", "msgpack"),
        ("linux", "3.12", "cbor"),
        ("windows", "3.12", "cbor"),
    ]


# ============================================================================
# Golden Test Format
# ============================================================================

class GoldenFixture(BaseModel):
    """
    Golden fixture for deterministic replay testing.
    
    Contains all inputs, outputs, and intermediate state needed to verify
    bit-for-bit identical replay across platforms.
    """
    
    # Metadata
    id: str                          # Fixture ID (e.g., "golden_001")
    version: str                     # Fixture version (e.g., "1.0.0")
    created_at: str                  # ISO 8601 timestamp
    os: str                          # Original OS (linux|windows|macos)
    python_version: str              # Original Python version (3.12)
    
    # Inputs (deterministic)
    actor: str                       # e.g., "agent:test"
    action: str                      # e.g., "http.request"
    target: str                      # e.g., "https://api.example.com"
    policy_rules: Dict[str, Any]     # Policy configuration
    
    # Expected outputs (byte-for-byte reproducible)
    policy_decision: str             # "allow" or "deny"
    decision_hash: str               # SHA256 hash of decision JSON
    evidence_hashes: Dict[str, str]  # SHA256 hashes of each evidence artifact
    
    # Serialized state (for validation)
    decision_json: str               # Decision serialized as JSON
    evidence_json_map: Dict[str, str]  # Evidence serialized as JSON map
    
    # Intermediate state (for debugging)
    governance_graph_hash: str       # SHA256 hash of governance graph
    posture_hash: str                # SHA256 hash of posture state
    
    # Determinism checks
    determinism_level: str           # "deterministic|idempotent|non_deterministic"
    environment_vars: Dict[str, str]  # Env vars that affect output
    system_dependencies: List[str]   # System libs/tools needed


class GoldenFixtureCollection(BaseModel):
    """Collection of golden fixtures organized by category."""
    
    version: str                     # Collection version (1.0.0)
    created_at: str                  # ISO 8601 timestamp
    fixtures: List[GoldenFixture]    # All fixtures
    
    # Metadata
    test_categories: Dict[str, int]  # Count by category
    platforms_covered: List[str]     # [linux, windows, macos]
    total_coverage_percent: float    # % of policy engine covered


# ============================================================================
# Hashing Rules (Deterministic)
# ============================================================================

class HashingRules:
    """
    Rules for generating deterministic hashes across platforms.
    
    Ensures SHA256(object) is identical on Linux, Windows, macOS.
    """
    
    @staticmethod
    def hash_json(obj: Any) -> str:
        """
        Hash a JSON-serializable object deterministically.
        
        Rules:
        1. Serialize to JSON with sorted keys (not insertion order)
        2. Use compact format (no whitespace)
        3. Use UTF-8 encoding
        4. Compute SHA256 of UTF-8 bytes
        5. Return lowercase hex string
        
        Example:
            obj = {"b": 2, "a": 1}
            # Serializes to: {"a": 1, "b": 2}  (keys sorted)
            # Hash: sha256(b'{"a": 1, "b": 2}')
        """
        import json
        import hashlib
        
        # Serialize with sorted keys and no whitespace
        canonical_json = json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,  # Escape non-ASCII characters
            default=str,
        )
        
        # Compute SHA256 of UTF-8 bytes
        hash_obj = hashlib.sha256(canonical_json.encode("utf-8"))
        return hash_obj.hexdigest().lower()
    
    @staticmethod
    def hash_file(file_path: str) -> str:
        """
        Hash a file deterministically.
        
        Rules:
        1. Read file in binary mode (platform-independent)
        2. Normalize line endings: convert CRLF to LF
        3. Compute SHA256
        4. Return lowercase hex
        
        Example:
            # Windows file with CRLF
            b"line1\r\nline2\r\n"
            # Normalized to LF
            b"line1\nline2\n"
            # Hash computed on normalized content
        """
        import hashlib
        
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Normalize line endings: CRLF → LF
        normalized = content.replace(b"\r\n", b"\n")
        
        hash_obj = hashlib.sha256(normalized)
        return hash_obj.hexdigest().lower()
    
    @staticmethod
    def hash_ordered_list(items: List[Any]) -> str:
        """
        Hash a list with guaranteed order.
        
        Rules:
        1. Convert to JSON array
        2. Sort elements (if all comparable)
        3. Serialize with sorted keys per item
        4. Hash as JSON
        
        Example:
            items = [{"b": 2}, {"a": 1}]
            # Sorted to: [{"a": 1}, {"b": 2}]
            # Serialized: [{"a":1},{"b":2}]
            # Hash: sha256(...)
        """
        import json
        import hashlib
        
        # Serialize each item with sorted keys
        serialized_items = [
            json.dumps(item, sort_keys=True, separators=(",", ":"), default=str)
            for item in items
        ]
        
        # Sort items (lexicographic order)
        serialized_items.sort()
        
        # Create array
        canonical_json = "[" + ",".join(serialized_items) + "]"
        
        hash_obj = hashlib.sha256(canonical_json.encode("utf-8"))
        return hash_obj.hexdigest().lower()
    
    @staticmethod
    def hash_dict_values_only(d: Dict[str, Any]) -> str:
        """
        Hash only the values of a dict (ignore keys for hash).
        
        Rules:
        1. Extract values in sorted key order
        2. Create array of values
        3. Hash array
        
        Useful for: hashes that shouldn't change if keys are reordered.
        """
        import json
        import hashlib
        
        values = [d[k] for k in sorted(d.keys())]
        canonical_json = json.dumps(
            values,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        hash_obj = hashlib.sha256(canonical_json.encode("utf-8"))
        return hash_obj.hexdigest().lower()


# ============================================================================
# Serialization Rules (Deterministic)
# ============================================================================

class SerializationRules:
    """
    Rules for serializing objects deterministically.
    
    Ensures that serialize(obj) produces identical output on all platforms.
    """
    
    @staticmethod
    def serialize_decision(decision: Dict[str, Any]) -> str:
        """
        Serialize a policy decision deterministically to JSON.
        
        Rules:
        1. Sort all keys at all nesting levels
        2. Use compact format (no whitespace)
        3. Use ISO 8601 for timestamps
        4. Ensure ASCII (escape non-ASCII)
        5. Use specific float precision
        
        Example:
            {
              "actor": "agent:test",
              "decision": "allow",
              "reason": "policy match"
            }
            
            Serializes to:
            {"actor":"agent:test","decision":"allow","reason":"policy match"}
        """
        import json
        from datetime import datetime
        
        def json_serializer(obj):
            """Custom serializer for non-standard types."""
            if isinstance(obj, datetime):
                return obj.isoformat() + "Z"
            if isinstance(obj, set):
                return sorted(list(obj))
            return str(obj)
        
        return json.dumps(
            decision,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=json_serializer,
        )
    
    @staticmethod
    def serialize_evidence(evidence: Dict[str, Any]) -> str:
        """
        Serialize evidence deterministically.
        
        Rules:
        1. Sort keys
        2. For nested dicts: recursively sort all levels
        3. For lists: sort if values are comparable; else preserve order
        4. Use compact JSON format
        5. Normalize whitespace in string values (trim, no extra spaces)
        
        Example:
            {
              "stdout": "line1\\nline2\\n",
              "exit_code": 0
            }
            
            Serializes to:
            {"exit_code":0,"stdout":"line1\\nline2\\n"}
        """
        import json
        
        def normalize_strings(obj):
            """Recursively normalize string values."""
            if isinstance(obj, dict):
                return {k: normalize_strings(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [normalize_strings(item) for item in obj]
            elif isinstance(obj, str):
                # Normalize whitespace but preserve intentional line breaks
                return obj.strip()
            return obj
        
        normalized = normalize_strings(evidence)
        
        return json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
    
    @staticmethod
    def serialize_graph_node(node: Dict[str, Any]) -> str:
        """
        Serialize a governance graph node deterministically.
        
        Rules:
        1. Sort all fields
        2. For relationships: sort by target ID
        3. Use consistent type representation
        4. Use compact JSON
        
        Example node:
            {
              "id": "node_001",
              "actor": "agent:test",
              "relationships": [
                {"type": "approved", "target": "node_002"},
                {"type": "requested", "target": "node_003"}
              ]
            }
            
            Relationships sorted by target.
        """
        import json
        
        # Sort relationships if present
        if "relationships" in node:
            node = node.copy()
            node["relationships"] = sorted(
                node["relationships"],
                key=lambda r: r.get("target", ""),
            )
        
        return json.dumps(
            node,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@dataclass
class PropertyTest:
    """
    Property-based test definition using Hypothesis.
    
    Each property test verifies an invariant that must hold for all inputs.
    """
    
    name: str
    description: str
    property_func: callable
    example_count: int = 100  # Number of examples to test
    
    
class DeterminismProperties:
    """Property tests that must hold for deterministic replay."""
    
    @staticmethod
    def test_hash_commutativity():
        """
        Property: hash(serialize(obj)) should be identical on different calls.
        
        Ensures that running the same serialization twice produces same hash.
        """
        # Example implementation (pseudo-code)
        """
        from hypothesis import given, settings
        import hypothesis.strategies as st
        
        @given(st.dictionaries(st.text(), st.integers()))
        @settings(max_examples=1000)
        def test_hash_idempotent(d):
            hash1 = HashingRules.hash_json(d)
            hash2 = HashingRules.hash_json(d)
            assert hash1 == hash2
        """
        pass
    
    @staticmethod
    def test_serialization_platform_independence():
        """
        Property: serialize(obj) should be identical on Linux, Windows, macOS.
        
        Ensures serialization doesn't depend on platform-specific behavior.
        """
        # Example: verify that serialization doesn't use platform-specific
        # path separators, line endings, or ordering.
        pass
    
    @staticmethod
    def test_sorting_stability():
        """
        Property: sorted(items) should produce same order across platforms.
        
        Ensures that Python's sort is deterministic (it is by default).
        """
        # Test that sorted() produces identical results
        pass
    
    @staticmethod
    def test_float_precision():
        """
        Property: float(x) should serialize identically.
        
        Ensures floats are serialized with consistent precision.
        """
        # Example: 1.0 should always serialize as "1.0" (not "1.00" or "1")
        pass
    
    @staticmethod
    def test_unicode_normalization():
        """
        Property: Unicode strings should be normalized before hashing.
        
        Ensures that "é" (precomposed) and "e" + "´" (decomposed) hash the same.
        """
        # Example: ensure Unicode normalization (NFC) before hashing
        pass


# ============================================================================
# Golden Test Framework
# ============================================================================

@dataclass
class GoldenTestCase:
    """Single golden test case."""
    
    name: str                   # Test case name
    description: str            # Human-readable description
    inputs: Dict[str, Any]      # Input parameters
    expected_outputs: Dict[str, Any]  # Expected outputs
    expected_hashes: Dict[str, str]   # Expected hashes
    
    # Determinism requirements
    replays_deterministically: bool
    platform_independent: bool
    

class GoldenTestSuite:
    """Suite of golden tests for deterministic replay."""
    
    TESTS: List[GoldenTestCase] = [
        GoldenTestCase(
            name="simple_allow_decision",
            description="Simple policy allow decision",
            inputs={
                "actor": "agent:test",
                "action": "http.request",
                "target": "https://api.example.com",
            },
            expected_outputs={
                "decision": "allow",
                "reason": "trusted_actor",
            },
            expected_hashes={
                "decision": "3b2c1c5e7f9a2d4e6c8f1a3b5c7d9e1f",  # Example
                "governance_graph": "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p",
            },
            replays_deterministically=True,
            platform_independent=True,
        ),
        GoldenTestCase(
            name="deny_decision_with_reason",
            description="Policy deny with detailed reason",
            inputs={
                "actor": "agent:untrusted",
                "action": "http.request",
                "target": "https://blocked.example.com",
            },
            expected_outputs={
                "decision": "deny",
                "reason": "actor not in trusted list",
            },
            expected_hashes={
                "decision": "7c8f9a2d4e6c8f1a3b5c7d9e1f3b2c1",
            },
            replays_deterministically=True,
            platform_independent=True,
        ),
        # ... more test cases
    ]


# ============================================================================
# CI Workflow Definition
# ============================================================================

@dataclass
class CIJob:
    """Single CI job definition."""
    
    name: str
    os: str
    python_version: str
    steps: List[str]
    timeout_minutes: int = 30


class CIWorkflow:
    """Complete CI workflow for deterministic replay testing."""
    
    JOBS = {
        "test-matrix": CIJob(
            name="Deterministic Replay Test Matrix",
            os="ubuntu-latest",
            python_version="3.12",
            steps=[
                "Checkout code",
                "Set up Python 3.12",
                "Install dependencies",
                "Run golden tests on Linux",
                "Set up Python 3.13",
                "Run golden tests on Python 3.13",
            ],
        ),
        "cross-platform": CIJob(
            name="Cross-Platform Determinism",
            os="macos-latest",
            python_version="3.12",
            steps=[
                "Checkout code",
                "Set up Python 3.12",
                "Install dependencies",
                "Run golden tests on macOS",
                "Compare hashes with Linux baseline",
            ],
        ),
        "windows-determinism": CIJob(
            name="Windows Determinism",
            os="windows-latest",
            python_version="3.12",
            steps=[
                "Checkout code",
                "Set up Python 3.12",
                "Install dependencies",
                "Run golden tests on Windows",
                "Compare hashes with Linux baseline",
                "Verify line ending handling",
            ],
        ),
    }


if __name__ == "__main__":
    """Print test strategy overview."""
    print("RIF Runtime v1.0 - Test Strategy for Deterministic Replay")
    print("=" * 80)
    print(f"\nTest Matrix (Primary):")
    for os_name, py_ver, fmt in TestMatrix.PRIMARY:
        print(f"  {os_name:10} Python {py_ver}  {fmt}")
    print(f"\nTotal golden test cases: {len(GoldenTestSuite.TESTS)}")
    print(f"Hashing algorithm: SHA256")
    print(f"Serialization format: JSON (with sorted keys)")
    print("\nKey principles:")
    print("  1. Sorted keys at all nesting levels")
    print("  2. Platform-neutral line endings (LF)")
    print("  3. UTF-8 encoding with ASCII escaping")
    print("  4. Deterministic ordering of collections")
    print("  5. Consistent type representation")
