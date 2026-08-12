# Development Guide

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git
- Make (recommended)

## Local Setup

### 1. Clone & Virtual Environment

```bash
git clone https://github.com/canstralian/rif-runtime.git
cd rif-runtime
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

### 2. Install Development Dependencies

```bash
pip install -e ".[dev]"
pip install -r requirements-dev.txt
```

### 3. Verify Installation

```bash
rif --version
python -m pytest --version
mypy --version
```

## Running the Application

### Development Mode (Hot Reload)

```bash
docker compose up --build
```

Or directly with uvicorn:

```bash
uvicorn 'src.rif_runtime.api:app' --host=0.0.0.0 --port=8000 --reload
```

### Access Points

- **API**: `http://localhost:8000`
- **Docs (Swagger UI)**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health**: `http://localhost:8000/health`

### CLI Development

```bash
rif execute --intent "test intent"
rif policy check config/policies.yaml
rif evidence export latest.zip
```

## Project Structure

```
rif-runtime/
├── src/rif_runtime/          # Main package
├── tests/                    # Test suite
├── config/                   # Configuration templates
├── data/                     # Runtime data (gitignored)
├── docs/                     # Documentation
├── spec/                     # API specifications
├── scripts/                  # Utility scripts
├── Dockerfile                # Container image
├── docker-compose.yml        # Development stack
├── pyproject.toml            # Package metadata & tool config
├── requirements.txt          # Runtime deps
├── requirements-dev.txt      # Development deps
├── rif.toml                  # Runtime configuration
└── Makefile                  # Common tasks
```

## Code Quality

### Linting

```bash
# Ruff (fast Python linter)
ruff check src/ tests/

# Type checking
mypy src/ tests/

# All checks
make lint
```

### Formatting

```bash
# Check formatting
ruff format --check src/ tests/

# Auto-format
ruff format src/ tests/
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src/rif_runtime tests/

# Specific test file
pytest tests/test_policy.py

# Verbose output
pytest -v tests/
```

### Security Scanning

```bash
# Bandit (security linter)
bandit -r src/

# Gitleaks (secret detection)
gitleaks detect
```

## Configuration

### Runtime Config (`rif.toml`)

```toml
[runtime]
version = "0.3.0rc1"
log_level = "INFO"
evidence_dir = "data/"

[policy]
default_policy = "config/policies.yaml"
auto_reload = true

[capabilities]
registry = "config/capabilities.yaml"

[storage]
backend = "jsonl"
decisions_file = "data/decisions.jsonl"
posture_file = "data/posture_history.jsonl"
```

### Environment Variables

Prefix with `RIF_`:

```bash
RIF_LOG_LEVEL=DEBUG
RIF_POLICY_AUTO_RELOAD=false
RIF_STORAGE_BACKEND=sqlite
```

### Policy Configuration

See `config/policies.yaml` for policy definitions and examples.

## Common Tasks

### Add a New Capability

1. Create capability module: `src/rif_runtime/capabilities/my_capability.py`
2. Implement `Capability` interface
3. Register in `config/capabilities.yaml`
4. Test with `tests/test_my_capability.py`

### Add a New API Endpoint

1. Create route file: `src/rif_runtime/api/routes/my_route.py`
2. Define Pydantic models in `schemas.py` if needed
3. Add route to `api.py` using `app.include_router()`
4. Document in `spec/openapi.yaml`
5. Test with `tests/test_api_my_route.py`

### Add a Policy Rule

1. Define rule structure in `rif_runtime/governance/models.py`
2. Implement evaluation logic in `rif_runtime/policy.py`
3. Add test cases
4. Document in `docs/POLICIES.md`

## Debugging

### Enable Debug Logging

```bash
export RIF_LOG_LEVEL=DEBUG
rif execute --intent "test" --verbose
```

### Inspect Evidence

```bash
# View recent decisions
tail -20 data/decisions.jsonl | python -m json.tool

# Export decision bundle
rif evidence export exec_123 bundle.zip
```

### Docker Container Debugging

```bash
# Shell access
docker compose exec server /bin/bash

# View logs
docker compose logs -f server

# Inspect network
docker network inspect rif-runtime_default
```

## Testing

### Test Organization

```
tests/
├── test_policy.py              # Policy engine tests
├── test_capabilities.py        # Capability system tests
├── test_api.py                 # API endpoint tests
├── test_audit.py               # Audit & evidence tests
├── test_execution.py           # Execution layer tests
├── test_mcp_integration.py     # MCP server tests
└── fixtures/                   # Test data & mocks
    ├── policies.yaml
    ├── decisions.jsonl
    └── sample_events.json
```

### Writing Tests

Use pytest with fixtures:

```python
import pytest
from rif_runtime.policy import PolicyEngine


@pytest.fixture
def policy_engine():
    return PolicyEngine(policy_file="tests/fixtures/policies.yaml")


def test_policy_evaluation(policy_engine):
    result = policy_engine.evaluate(
        actor="test:agent", action="http.request", target="https://api.example.com"
    )
    assert result.decision == "allow"
```

## Continuous Integration

GitHub Actions workflows in `.github/workflows/`:

- `ci.yml` — Tests on push/PR
- `quality.yml` — Code quality checks
- `codeql.yml` — Security analysis
- `bandit.yml` — Dependency vulnerabilities
- `gitleaks.yml` — Secret detection
- `release.yml` — Release automation

View results on GitHub Actions tab.

## Making Changes

1. Create a branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -am "Add feature"`
3. Push and create a pull request
4. Ensure CI passes (tests, lint, security scans)
5. Request review from maintainers
6. Merge when approved

## Performance Profiling

### CPU Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... code to profile ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative").print_stats(10)
```

### Memory Profiling

```bash
pip install memory-profiler
python -m memory_profiler -m rif execute --intent "test"
```

## Documentation

- API docs auto-generated at `/docs`
- Architecture: `ARCHITECTURE.md`
- Security model: `SECURITY.md`
- Release process: `release-engineering-guide.md`
- CLI reference: `cli-reference.md`

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Pytest Docs](https://docs.pytest.org/)
- [MyPy Docs](https://mypy.readthedocs.io/)
