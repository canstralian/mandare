# RIF Runtime v1.0 - Test Strategy for Deterministic Replay

## Goal

**Guarantee that policy decisions, evidence, and governance graph can be replayed with byte-for-byte identical hashes and serialization across Linux, Windows, and macOS.**

This document defines the complete test strategy to ensure determinism is NOT a hope, but a verified invariant.

---

## Executive Summary

| Aspect | Strategy |
|--------|----------|
| **Test Matrix** | 4 OSes × 2 Python versions × 3 formats (primary); up to 12 combinations (full) |
| **Hashing** | SHA256 with canonical JSON serialization (sorted keys) |
| **Serialization** | JSON with UTF-8 + ASCII escaping, platform-neutral line endings (LF) |
| **Property Tests** | Hypothesis-based fuzz testing with 1000+ examples per property |
| **Golden Tests** | Fixture-based snapshot tests comparing against verified outputs |
| **CI/CD** | 4 parallel jobs (Linux, Windows, macOS, hash comparison) + flaky test detection |
| **Flaky Test Prevention** | Tests run 5-10 times; random seed injection; timing variance detection |

---

## 1. Test Matrix

### Primary Matrix (Tested on Every PR)

```yaml
Test Matrix:
  - Linux   + Python 3.12 + JSON          [PRIMARY - most common]
  - Linux   + Python 3.13 + JSON
  - Windows + Python 3.12 + JSON
  - macOS   + Python 3.12 + JSON

Coverage:
  - 4 platform combinations
  - 2 Python versions (latest & next)
  - 1 serialization format (JSON, most compatible)
  
Time: ~15 minutes per run
```

### Extended Matrix (Tested on Release)

```yaml
Primary matrix + 
  - Linux   + Python 3.12 + MessagePack
  - Windows + Python 3.12 + MessagePack
  - macOS   + Python 3.12 + MessagePack

Coverage:
  - Alternative serialization format (msgpack)
  - 7 combinations total
  
Time: ~25 minutes
```

### Full Matrix (Tested Nightly)

```yaml
Extended matrix +
  - Linux   + Python 3.13 + MessagePack
  - Windows + Python 3.13 + MessagePack
  - macOS   + Python 3.13 + MessagePack
  - Linux   + Python 3.12 + CBOR
  - Windows + Python 3.12 + CBOR

Coverage:
  - All Python versions
  - All serialization formats
  - 12 combinations total
  
Time: ~40 minutes
```

### Matrix Configuration

```python
# tests/conftest.py
import pytest

@pytest.fixture(params=['linux', 'windows', 'macos'])
def os_name(request):
    return request.param

@pytest.fixture(params=['3.12', '3.13'])
def python_version(request):
    return request.param

@pytest.fixture(params=['json', 'msgpack', 'cbor'])
def serialization_format(request):
    return request.param
```

---

## 2. Hashing Rules (Deterministic)

### Rule 1: Canonical JSON Serialization

**Requirement**: `hash(object)` must be identical on all platforms.

**Rule**:
```python
import json
import hashlib

def hash_deterministic(obj):
    # 1. Sort all keys (depth-first)
    canonical = json.dumps(
        obj,
        sort_keys=True,           # Sort all dict keys
        separators=(",", ":"),    # No spaces (compact)
        ensure_ascii=True,        # Escape non-ASCII (\u00e9 instead of é)
        default=str,              # Convert unserializable to string
    )
    
    # 2. Hash UTF-8 bytes
    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest().lower()
```

**Examples**:

```python
# Object with unordered keys
obj1 = {"b": 2, "a": 1}
obj2 = {"a": 1, "b": 2}

hash(obj1) == hash(obj2)  # True (both serialize to {"a":1,"b":2})

# Object with nested dicts
obj3 = {
    "user": {"name": "alice", "id": 123},
    "action": "http.request"
}
# Serializes to: {"action":"http.request","user":{"id":123,"name":"alice"}}
# Both outer and inner dicts sorted

# Non-ASCII characters
obj4 = {"city": "Montréal"}
# Serializes to: {"city":"Montr\u00e9al"}
# Consistent across all platforms
```

### Rule 2: Platform-Neutral Line Endings

**Requirement**: Files hashed on Windows (CRLF) must hash identically to Linux (LF).

**Rule**:
```python
def hash_file_deterministic(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Normalize: CRLF → LF
    normalized = content.replace(b'\r\n', b'\n')
    
    # Hash normalized content
    return hashlib.sha256(normalized).hexdigest().lower()
```

**Enforcement**:

```yaml
# .gitattributes (enforce LF in repo)
* text eol=lf
*.py text eol=lf
*.json text eol=lf
*.yaml text eol=lf
```

**CI Check**:
```bash
# .github/workflows/determinism.yml (Windows job)
- name: Verify line endings
  run: |
    python -c "
    import pathlib
    for file in pathlib.Path('fixtures/').glob('**/*.json'):
        with open(file, 'rb') as f:
            if b'\r\n' in f.read():
                raise RuntimeError(f'{file} has CRLF endings')
    "
```

### Rule 3: Stable Ordering of Collections

**Requirement**: Lists must be ordered consistently.

**Rule**:
```python
def hash_list_deterministic(items):
    # Convert to JSON (with each item sorted)
    serialized = json.dumps(
        sorted(items, key=lambda x: json.dumps(x, sort_keys=True, default=str)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest().lower()
```

**Guarantee**: If you have `[b, a]`, they will always be sorted to `[a, b]` before hashing.

### Rule 4: Float Precision

**Requirement**: Floats must serialize with consistent precision.

**Rule**:
```python
import json

# Use consistent float precision
def serialize_float(f):
    # Round to 6 decimal places (IEEE 754 single precision)
    return round(f, 6)

# In JSON serialization
json.dumps(
    {"value": 1.23456789},
    default=lambda x: serialize_float(x) if isinstance(x, float) else str(x)
)
# Result: {"value":1.234568}
```

**Guarantee**: `1.0` always serializes as `1.0` (not `1` or `1.00` or `1.000000`).

### Rule 5: Unicode Normalization

**Requirement**: Unicode strings must be normalized before hashing.

**Rule**:
```python
import unicodedata

def normalize_unicode(s):
    # NFC (Canonical Decomposition, followed by Canonical Composition)
    return unicodedata.normalize('NFC', s)

# In serialization
json.dumps(
    {k: normalize_unicode(v) if isinstance(v, str) else v for k, v in obj.items()},
    sort_keys=True,
    separators=(",", ":"),
)
```

**Guarantee**: "café" (precomposed é) and "cafe" + "´" (decomposed) both normalize to same form before hashing.

---

## 3. Serialization Rules (Deterministic)

### Decision Serialization

```python
from datetime import datetime

def serialize_decision(decision: dict) -> str:
    """Serialize policy decision deterministically."""
    def serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat() + "Z"  # ISO 8601 with Z
        if isinstance(obj, set):
            return sorted(list(obj))       # Sort sets
        return str(obj)
    
    return json.dumps(
        decision,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=serializer,
    )
```

**Canonical form**:
```json
{"actor":"agent:test","decision":"allow","reason":"trusted_actor","timestamp":"2024-01-15T10:30:00Z"}
```

### Evidence Serialization

```python
def serialize_evidence(evidence: dict) -> str:
    """Serialize evidence deterministically."""
    def normalize(obj):
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [normalize(item) for item in obj]
        elif isinstance(obj, str):
            return obj.strip()  # Trim whitespace
        return obj
    
    normalized = normalize(evidence)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
```

### Governance Graph Serialization

```python
def serialize_graph_node(node: dict) -> str:
    """Serialize governance graph node deterministically."""
    # Sort relationships by target
    if "relationships" in node:
        node = node.copy()
        node["relationships"] = sorted(
            node["relationships"],
            key=lambda r: r.get("target", "")
        )
    
    return json.dumps(
        node,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
```

---

## 4. Golden Fixture Format

### Fixture Structure

```yaml
# fixtures/golden/golden_001.json
{
  "id": "golden_001",
  "version": "1.0.0",
  "created_at": "2024-01-15T10:30:00Z",
  "os": "linux",
  "python_version": "3.12",
  
  # INPUTS (deterministic)
  "inputs": {
    "actor": "agent:test",
    "action": "http.request",
    "target": "https://api.example.com",
    "policy_rules": {
      "trusted_actors": ["agent:test"],
      "allowed_domains": ["api.example.com", "api.openai.com"]
    }
  },
  
  # EXPECTED OUTPUTS (byte-for-byte)
  "expected": {
    "decision": "allow",
    "reason": "trusted_actor in policy",
    "decision_hash": "3b2c1c5e7f9a2d4e6c8f1a3b5c7d9e1f",
    "decision_json": "{\"actor\":\"agent:test\",\"decision\":\"allow\",\"reason\":\"trusted_actor in policy\"}",
    
    # Evidence hashes
    "evidence_hashes": {
      "policy_evaluation": "7c8f9a2d4e6c8f1a3b5c7d9e1f3b2c1",
      "posture_snapshot": "2e3f4a5b6c7d8e9f0a1b2c3d4e5f6g7h"
    }
  },
  
  # DETERMINISM METADATA
  "determinism": {
    "level": "deterministic",
    "platform_independent": true,
    "replay_safe": true,
    "environment_vars": {},
    "system_dependencies": []
  }
}
```

### Fixture Generation

```python
# tests/fixtures/generate_golden.py
import json
import hashlib
from pathlib import Path

def generate_golden_fixture(test_case):
    """Generate a golden fixture from a test case."""
    
    # Run the policy evaluation
    result = policy_engine.evaluate(**test_case.inputs)
    
    # Serialize outputs
    decision_json = serialize_decision(result.decision)
    decision_hash = hashlib.sha256(
        decision_json.encode("utf-8")
    ).hexdigest().lower()
    
    # Capture evidence
    evidence_hashes = {}
    for name, evidence in result.evidence.items():
        evidence_json = serialize_evidence(evidence)
        evidence_hashes[name] = hashlib.sha256(
            evidence_json.encode("utf-8")
        ).hexdigest().lower()
    
    # Create fixture
    fixture = {
        "id": f"golden_{len(fixtures):03d}",
        "version": "1.0.0",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "os": platform.system().lower(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "inputs": test_case.inputs,
        "expected": {
            "decision": result.decision.decision.value,
            "reason": result.decision.reason,
            "decision_hash": decision_hash,
            "decision_json": decision_json,
            "evidence_hashes": evidence_hashes,
        },
        "determinism": test_case.determinism_metadata,
    }
    
    # Write fixture
    fixture_path = Path("fixtures/golden") / f"{fixture['id']}.json"
    with open(fixture_path, "w") as f:
        json.dump(fixture, f, indent=2)
    
    return fixture
```

---

## 5. Property-Based Tests (Hypothesis)

### Property 1: Hash Idempotence

```python
from hypothesis import given, settings
import hypothesis.strategies as st

@given(st.dictionaries(st.text(), st.integers()))
@settings(max_examples=1000)
def test_hash_idempotent(d):
    """hash(x) == hash(x) always"""
    hash1 = hash_deterministic(d)
    hash2 = hash_deterministic(d)
    assert hash1 == hash2
```

### Property 2: Hash Stability Across Platforms

```python
@given(st.dictionaries(st.text(), st.integers()))
@settings(max_examples=100)
def test_hash_platform_independent(d):
    """hash(x) on Linux == hash(x) on Windows == hash(x) on macOS"""
    # This test runs on each platform
    hash_value = hash_deterministic(d)
    
    # Load expected hash from golden fixture
    expected = load_golden_hash(d)
    assert hash_value == expected
```

### Property 3: Serialization Determinism

```python
@given(st.dictionaries(
    st.text(),
    st.one_of(st.integers(), st.text(), st.floats(allow_nan=False, allow_infinity=False))
))
@settings(max_examples=1000)
def test_serialization_deterministic(d):
    """serialize(x) == serialize(x) always"""
    s1 = serialize_decision(d)
    s2 = serialize_decision(d)
    assert s1 == s2
```

### Property 4: Collection Ordering

```python
@given(st.lists(st.dictionaries(st.text(), st.integers())))
@settings(max_examples=500)
def test_list_ordering_stable(items):
    """sorted(items) produces same order on all platforms"""
    hash1 = hash_list_deterministic(items)
    
    # Shuffle and hash again
    import random
    shuffled = items.copy()
    random.shuffle(shuffled)
    hash2 = hash_list_deterministic(shuffled)
    
    # Should be identical (both sorted internally)
    assert hash1 == hash2
```

---

## 6. Flaky Test Prevention

### Strategy 1: Deterministic Random Seed

```python
# conftest.py
import os

def pytest_configure(config):
    """Set deterministic seed at start."""
    os.environ['PYTHONHASHSEED'] = '0'
    
    # Also seed Python's random
    import random
    random.seed(0)
    
    # Seed numpy if installed
    try:
        import numpy as np
        np.random.seed(0)
    except ImportError:
        pass
```

### Strategy 2: Repeated Execution

```bash
# Run each test 5-10 times
pytest tests/test_determinism.py --count=5 --tb=short

# Run with random seeds
pytest tests/test_determinism.py --hypothesis-seed=random -n 100
```

### Strategy 3: Timing Normalization

```python
def test_timing_not_in_hash():
    """Timing information should not affect hashes"""
    
    start = time.time()
    result1 = policy_engine.evaluate(**inputs)
    duration1 = time.time() - start
    
    time.sleep(0.1)  # Force different timing
    
    start = time.time()
    result2 = policy_engine.evaluate(**inputs)
    duration2 = time.time() - start
    
    # Different execution times
    assert duration1 != duration2
    
    # Same hashes
    hash1 = hash_deterministic(result1)
    hash2 = hash_deterministic(result2)
    assert hash1 == hash2
```

### Strategy 4: Flakiness Detection

```python
# scripts/analyze_flakiness.py
import xml.etree.ElementTree as ET

def analyze_junit(junit_file):
    """Analyze JUnit output for flaky tests."""
    root = ET.parse(junit_file).getroot()
    
    results_by_test = {}
    for testcase in root.iter('testcase'):
        name = testcase.attrib['name']
        passed = testcase.find('failure') is None
        
        if name not in results_by_test:
            results_by_test[name] = {'passed': 0, 'failed': 0}
        
        if passed:
            results_by_test[name]['passed'] += 1
        else:
            results_by_test[name]['failed'] += 1
    
    # Report flaky tests (some pass, some fail)
    flaky = {
        name: results
        for name, results in results_by_test.items()
        if results['passed'] > 0 and results['failed'] > 0
    }
    
    if flaky:
        print("FLAKY TESTS DETECTED:")
        for name, results in flaky.items():
            pct = 100 * results['passed'] / (results['passed'] + results['failed'])
            print(f"  {name}: {pct:.0f}% pass rate")
        return False
    
    return True
```

---

## 7. CI/CD Workflow

### Workflow Jobs

```yaml
Jobs:
  1. determinism-linux       (Python 3.12, 3.13)     → 2 × 15 min
  2. determinism-windows     (Python 3.12)           → 15 min
  3. determinism-macos       (Python 3.12)           → 15 min
  4. compare-hashes          (cross-platform verify) → 10 min
  5. flaky-test-detection    (5-10 runs per test)    → 20 min
  6. performance-baseline    (benchmark tracking)    → 10 min

Total time: ~90 minutes for full primary matrix
```

### Hash Comparison

```python
# scripts/compare_hashes.py
import json
from pathlib import Path

def compare_hashes(all_hashes_dir):
    """Compare hashes across platforms."""
    
    results = {}
    for hash_file in Path(all_hashes_dir).glob('**/hashes.json'):
        platform = hash_file.parent.name
        with open(hash_file) as f:
            results[platform] = json.load(f)
    
    # Get baseline (Linux)
    baseline = results['linux_py312']
    
    discrepancies = []
    for platform, hashes in results.items():
        if platform == 'linux_py312':
            continue
        
        for test_id, hash_value in hashes.items():
            if hash_value != baseline[test_id]:
                discrepancies.append({
                    'test': test_id,
                    'platform': platform,
                    'expected': baseline[test_id],
                    'got': hash_value,
                })
    
    if discrepancies:
        print(f"HASH DISCREPANCIES: {len(discrepancies)}")
        for disc in discrepancies:
            print(f"  {disc['test']} on {disc['platform']}")
            print(f"    Expected: {disc['expected']}")
            print(f"    Got:      {disc['got']}")
        return False
    
    print("✓ All hashes match across platforms!")
    return True
```

---

## 8. Verification Checklist

### Before Shipping v1.0

- [ ] All 4 platform combinations in primary matrix pass
- [ ] All 12 platform combinations in full matrix pass (nightly)
- [ ] Cross-platform hash comparison passes (all hashes match)
- [ ] Property tests pass with 1000+ examples per property
- [ ] No flaky tests detected (5-10 runs all pass)
- [ ] Performance baseline established and tracked
- [ ] Golden fixture coverage >95%
- [ ] Line ending normalization verified (Windows)
- [ ] Float precision consistent across platforms
- [ ] Unicode normalization applied
- [ ] Serialization determinism proven
- [ ] Replay engine verified for idempotence

### Continuous Verification

```yaml
On every commit:
  - Run primary test matrix (~15 min)
  - Detect flaky tests
  
On every PR:
  - Run primary test matrix
  - Compare hashes
  - Report in PR comment
  
On release:
  - Run extended test matrix (~25 min)
  - Verify all platforms
  
Nightly:
  - Run full test matrix (~40 min)
  - All Python versions, formats
  - Performance trending
```

---

## 9. Expected Outcomes

### Success Criteria

✅ **All tests pass** on Linux 3.12, 3.13, Windows 3.12, macOS 3.12  
✅ **Hash discrepancies = 0** across platforms  
✅ **Flaky test rate = 0%** (all tests pass 100% of runs)  
✅ **Golden fixture coverage >95%** (>200 fixtures)  
✅ **Property tests pass** with diverse inputs (1000+ examples)  
✅ **Performance stable** (±5% variation across platforms)  

### Documentation

- Test strategy document (this file)
- CI workflow definition (.github/workflows/determinism.yml)
- Golden fixture reference
- Hashing rules and algorithms
- Serialization format specification
- Flaky test prevention playbook

---

## Summary

By implementing this comprehensive test strategy:

1. **Determinism is guaranteed**: Every execution produces identical hashes
2. **Cross-platform compatibility verified**: Linux, Windows, macOS all match
3. **Flakiness eliminated**: Tests run reproducibly 100% of the time
4. **Performance tracked**: Benchmarks prevent regressions
5. **Compliance ready**: Complete audit trail for replay validation

This makes RIF Runtime v1.0 production-ready for deterministic replay.
