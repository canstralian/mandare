# Testing Strategy

## Overview

RIF Runtime uses a multi-layered testing approach: unit tests for logic isolation, integration tests for component interaction, and end-to-end tests for full workflows.

## Test Organization

```
tests/
├── unit/
│   ├── test_policy_engine.py
│   ├── test_intent_compiler.py
│   ├── test_capability_registry.py
│   ├── test_audit_trail.py
│   └── test_storage_backends.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_policy_evaluation_flow.py
│   ├── test_execution_pipeline.py
│   ├── test_mcp_integration.py
│   └── test_governance_graph.py
├── e2e/
│   ├── test_full_execution_workflow.py
│   ├── test_replay_determinism.py
│   └── test_evidence_export.py
├── fixtures/
│   ├── policies.yaml
│   ├── capabilities.yaml
│   ├── sample_decisions.jsonl
│   └── mcp_servers.json
└── conftest.py
```

## Unit Tests

Test individual components in isolation with mocked dependencies.

### Example: Policy Engine

```python
# tests/unit/test_policy_engine.py
import pytest
from rif_runtime.policy import PolicyEngine
from rif_runtime.schemas import PolicyDecision

@pytest.fixture
def policy_engine():
    return PolicyEngine(policy_file="tests/fixtures/policies.yaml")

def test_policy_allow_trusted_actor(policy_engine):
    """Trusted actors should be allowed by default."""
    result = policy_engine.evaluate(
        actor="agent:trusted",
        action="http.request",
        target="https://api.anthropic.com"
    )
    assert result.decision == "allow"
    assert result.rationale == "actor in trusted_actors"

def test_policy_deny_unknown_target(policy_engine):
    """Requests to unknown targets should require explicit approval."""
    result = policy_engine.evaluate(
        actor="agent:trusted",
        action="http.request",
        target="https://unknown-api.example.com"
    )
    assert result.decision == "deny"
    assert "unknown target" in result.rationale.lower()

def test_policy_evaluation_with_context(policy_engine):
    """Policy should consider execution context."""
    result = policy_engine.evaluate(
        actor="agent:untrusted",
        action="file.write",
        target="/etc/passwd",
        context={"sandbox_level": "strict"}
    )
    assert result.decision == "deny"
```

### Example: Intent Compiler

```python
# tests/unit/test_intent_compiler.py
import pytest
from rif_runtime.execution.compiler import IntentCompiler
from rif_runtime.schemas import CommandObject

@pytest.fixture
def compiler():
    return IntentCompiler()

def test_simple_intent_parsing(compiler):
    """Parse simple HTTP intent."""
    cmd = compiler.compile("POST https://api.example.com/resource {'key': 'value'}")
    assert cmd.action == "http.request"
    assert cmd.method == "POST"
    assert cmd.target == "https://api.example.com/resource"

def test_intent_validation(compiler):
    """Invalid intent should raise ValidationError."""
    with pytest.raises(ValueError, match="invalid syntax"):
        compiler.compile("INVALID intent }{")
```

## Integration Tests

Test component interaction and data flow through multiple layers.

### Example: Policy Evaluation Flow

```python
# tests/integration/test_policy_evaluation_flow.py
import pytest
from rif_runtime.runtime import RIFRuntime

@pytest.fixture
def runtime(tmp_path):
    return RIFRuntime(
        config_dir="tests/fixtures",
        data_dir=str(tmp_path)
    )

def test_full_policy_evaluation_pipeline(runtime):
    """End-to-end policy evaluation should record evidence."""
    result = runtime.evaluate_intent(
        intent="POST https://api.example.com/data",
        actor="agent:test"
    )
    
    # Check decision was made
    assert result.decision_id is not None
    assert result.decision in ["allow", "deny"]
    
    # Check evidence was recorded
    decision = runtime.storage.get_decision(result.decision_id)
    assert decision is not None
    assert decision["actor"] == "agent:test"
    assert decision["timestamp"] is not None

def test_policy_reload_reflects_changes(runtime):
    """Runtime should reflect policy changes on reload."""
    # Initial evaluation
    result1 = runtime.evaluate_intent(
        intent="POST https://api.example.com/data",
        actor="agent:new"
    )
    assert result1.decision == "deny"  # Not in initial policy
    
    # Reload with updated policy
    runtime.reload_policies("tests/fixtures/policies.updated.yaml")
    
    # Should now allow
    result2 = runtime.evaluate_intent(
        intent="POST https://api.example.com/data",
        actor="agent:new"
    )
    assert result2.decision == "allow"
```

## End-to-End Tests

Test full workflows from user intent to evidence export.

### Example: Execution Workflow

```python
# tests/e2e/test_full_execution_workflow.py
import pytest
import json
import zipfile
from rif_runtime.runtime import RIFRuntime

@pytest.fixture
def runtime_e2e(tmp_path):
    return RIFRuntime(
        config_dir="tests/fixtures",
        data_dir=str(tmp_path),
        mode="e2e_test"
    )

def test_full_http_execution_workflow(runtime_e2e, tmp_path, requests_mock):
    """Complete workflow: intent → policy → execution → evidence."""
    
    # Mock external HTTP endpoint
    requests_mock.post(
        "https://api.example.com/resource",
        json={"id": "123", "status": "created"}
    )
    
    # Execute intent
    result = runtime_e2e.execute_intent(
        intent='POST https://api.example.com/resource {"name": "test"}',
        actor="agent:e2e_test"
    )
    
    assert result.success is True
    assert result.execution_id is not None
    
    # Verify evidence was recorded
    decision = runtime_e2e.storage.get_decision(result.decision_id)
    assert decision["result"] == "allow"
    
    posture = runtime_e2e.storage.get_posture(result.posture_id)
    assert posture["runtime_version"] is not None
    
    # Export evidence bundle
    bundle_path = tmp_path / "evidence.zip"
    runtime_e2e.export_evidence(result.execution_id, str(bundle_path))
    
    # Verify bundle contents
    with zipfile.ZipFile(bundle_path) as zf:
        files = zf.namelist()
        assert "decision.json" in files
        assert "posture.json" in files
        assert "execution.json" in files
```

### Example: Replay Determinism

```python
# tests/e2e/test_replay_determinism.py
import pytest
from rif_runtime.replay import ReplayEngine

@pytest.fixture
def replay_engine(runtime_e2e):
    return ReplayEngine(runtime=runtime_e2e)

def test_replay_execution_determinism(runtime_e2e, replay_engine, requests_mock):
    """Replaying execution should produce identical results."""
    
    # Mock endpoint with consistent responses
    requests_mock.post(
        "https://api.example.com/resource",
        json={"result": "success", "timestamp": "fixed"}
    )
    
    # Original execution
    exec1 = runtime_e2e.execute_intent(
        intent='POST https://api.example.com/resource {"data": "test"}',
        actor="agent:replay_test"
    )
    
    # Replay execution
    exec2 = replay_engine.replay(exec1.execution_id)
    
    # Compare outcomes
    result1 = runtime_e2e.storage.get_execution(exec1.execution_id)
    result2 = runtime_e2e.storage.get_execution(exec2.execution_id)
    
    assert result1["http_status"] == result2["http_status"]
    assert result1["response_body"] == result2["response_body"]
```

## Test Fixtures

### Shared Fixtures (`tests/conftest.py`)

```python
import pytest
import tempfile
from pathlib import Path
from rif_runtime.runtime import RIFRuntime

@pytest.fixture
def tmp_config_dir(tmp_path):
    """Create temporary config directory with test fixtures."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # Copy fixture files
    import shutil
    for file in Path("tests/fixtures").glob("*.yaml"):
        shutil.copy(file, config_dir / file.name)
    
    return config_dir

@pytest.fixture
def runtime(tmp_path, tmp_config_dir):
    """Configured runtime for testing."""
    return RIFRuntime(
        config_dir=str(tmp_config_dir),
        data_dir=str(tmp_path)
    )

@pytest.fixture
def sample_decisions():
    """Load sample decisions for testing."""
    import json
    with open("tests/fixtures/sample_decisions.jsonl") as f:
        return [json.loads(line) for line in f]
```

## Coverage Requirements

- **Minimum coverage**: 80%
- **Critical paths** (policy, audit, execution): 95%+
- **Coverage report**: `pytest --cov=src/rif_runtime tests/`

## Running Tests

### All Tests

```bash
pytest
```

### Specific Test File

```bash
pytest tests/unit/test_policy_engine.py
```

### Specific Test Class/Function

```bash
pytest tests/unit/test_policy_engine.py::test_policy_allow_trusted_actor
```

### With Coverage

```bash
pytest --cov=src/rif_runtime --cov-report=html tests/
open htmlcov/index.html
```

### Watch Mode (requires `pytest-watch`)

```bash
ptw  # Auto-runs tests on file changes
```

### Parallel Execution (requires `pytest-xdist`)

```bash
pytest -n auto  # Use all CPU cores
```

## CI/CD Integration

Tests run automatically on:
- **Push**: All tests run
- **Pull Request**: Coverage must increase or maintain
- **Release**: Full suite + performance benchmarks

See `.github/workflows/ci.yml` for configuration.

## Performance Tests

Benchmark critical paths:

```python
# tests/performance/test_policy_throughput.py
import pytest

@pytest.mark.performance
def test_policy_evaluation_throughput(benchmark, policy_engine):
    """Policy evaluation should complete < 50ms."""
    def evaluate():
        return policy_engine.evaluate(
            actor="agent:test",
            action="http.request",
            target="https://api.example.com"
        )
    
    result = benchmark(evaluate)
    assert result.decision in ["allow", "deny"]
```

Run performance tests:

```bash
pytest tests/performance/ --benchmark-only
```

## Security Testing

### Input Validation

```python
def test_intent_injection_prevention(compiler):
    """Intent compiler should reject injection attempts."""
    malicious = "POST https://api.example.com/resource; rm -rf /"
    with pytest.raises(ValueError):
        compiler.compile(malicious)

def test_policy_bypass_prevention(policy_engine):
    """Policy evaluation should resist bypass attempts."""
    result = policy_engine.evaluate(
        actor="agent:test",
        action="http.request",
        target="https://api.example.com/../../../etc/passwd"
    )
    assert result.decision == "deny"
```

### Evidence Tampering

```python
def test_evidence_integrity_verification(runtime):
    """Tampered evidence should fail verification."""
    original = runtime.storage.get_decision(decision_id)
    
    # Tamper with decision
    original["result"] = "allow"  # Was "deny"
    runtime.storage._update_decision(original)
    
    # Verification should fail
    assert runtime.verify_evidence(decision_id) is False
```

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python version: `python --version` (should be 3.12+)
- Clear cache: `rm -rf .pytest_cache __pycache__`
- Reinstall deps: `pip install -e ".[dev]"`

### Flaky Tests

- Check for time-dependent assertions
- Mock time with `freezegun`
- Avoid real I/O; use fixtures and mocks

### Slow Tests

- Profile with `pytest-duration-plugin`
- Use `--maxfail=1` to stop on first failure during debugging
- Run only affected tests: `pytest --lf` (last failed)
