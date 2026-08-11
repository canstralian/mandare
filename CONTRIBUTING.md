# Contributing to RIF Runtime

Thank you for your interest in RIF Runtime! This document outlines our contribution guidelines and development workflow.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read `CODE_OF_CONDUCT.md` and follow its principles in all interactions.

## Development Workflow

### 1. Setup

```bash
git clone https://github.com/canstralian/rif-runtime.git
cd rif-runtime
make setup
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-fix-name
# or
git checkout -b docs/your-docs-update
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation updates
- `refactor/` — Code refactoring (no behavior change)
- `test/` — Test improvements
- `security/` — Security fixes

### 3. Make Changes

Follow these practices:

#### Code Quality

- **Write tests first** — Use TDD when possible
- **Run linting**: `make lint` — Must pass before PR
- **Type hints** — All functions and methods must have type hints
- **Docstrings** — Public functions require docstrings
- **Comments** — Complex logic needs inline comments

#### Example: Adding a Capability

```python
# src/rif_runtime/capabilities/email_capability.py
from typing import Dict, Any
from rif_runtime.capabilities.base import Capability

class EmailCapability(Capability):
    """Send emails with policy evaluation."""
    
    def __init__(self):
        super().__init__(name="email", timeout_seconds=30)
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email capability.
        
        Args:
            params: {to, subject, body, reply_to}
        
        Returns:
            {message_id, status, timestamp}
        
        Raises:
            ValueError: Invalid email parameters
        """
        # Implementation...
        pass
```

#### Testing

```python
# tests/unit/test_email_capability.py
import pytest
from rif_runtime.capabilities.email_capability import EmailCapability

@pytest.fixture
def email_cap():
    return EmailCapability()

@pytest.mark.asyncio
async def test_send_email_success(email_cap):
    """Test successful email sending."""
    result = await email_cap.execute({
        "to": "test@example.com",
        "subject": "Test",
        "body": "Hello"
    })
    assert result["status"] == "sent"
    assert "message_id" in result

@pytest.mark.asyncio
async def test_invalid_email_address(email_cap):
    """Test rejection of invalid email."""
    with pytest.raises(ValueError, match="invalid email"):
        await email_cap.execute({"to": "not-an-email"})
```

### 4. Testing Locally

```bash
# Run affected tests
make test

# With coverage
make coverage

# Only unit tests
make test-unit

# Watch mode (auto-rerun on changes)
make watch
```

### 5. Code Quality Checks

```bash
# All checks
make lint

# Individual checks
make lint-ruff        # Linting
make type-check       # Type checking
make format           # Auto-format
make security         # Security scanning
```

### 6. Commit

Write clear, descriptive commit messages:

```
feature: add email capability with policy evaluation

- Implement EmailCapability.execute() with async support
- Add SMTP configuration in rif.toml
- Add 100% test coverage for email capability
- Update docs/CAPABILITIES.md with usage examples

Closes #123
```

Guidelines:
- Use present tense ("add" not "added")
- Be specific about what changed and why
- Reference issues: `Closes #123` or `Fixes #456`
- Limit first line to 72 characters

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a PR on GitHub with:

- **Title**: Brief description (same as commit message first line)
- **Description**: Explain the change, why it matters, and any tradeoffs
- **Checklist**:
  - [ ] Tests added/updated
  - [ ] Linting passes (`make lint`)
  - [ ] Coverage maintained or improved
  - [ ] Docs updated if applicable
  - [ ] No breaking changes (or documented in PR)

#### PR Template

```markdown
## Description
What does this PR do?

## Related Issues
Closes #123

## Type of Change
- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactoring
- [ ] Security

## Testing
How did you test this?

## Checklist
- [ ] Tests added/updated
- [ ] Linting passes
- [ ] Coverage maintained (>80%)
- [ ] Docs updated
- [ ] No breaking changes

## Screenshots (if applicable)
```

### 8. Review Process

- At least one maintainer review required
- CI must pass (tests, lint, security scans)
- Coverage must not decrease
- All feedback must be addressed
- Maintainer merges when ready

## Areas for Contribution

### Good First Issues

Look for:
- `good-first-issue` label on GitHub
- Documentation improvements
- Test coverage for uncovered code
- Bug fixes with clear reproduction steps

### High-Priority Areas

1. **Capabilities** — Implement missing integrations (Slack, GitHub, etc.)
2. **Policy Engine** — Optimization and new rule types
3. **Storage Backends** — PostgreSQL, MongoDB support
4. **Kubernetes** — K8s deployment improvements
5. **Documentation** — API docs, tutorials, examples
6. **Performance** — Latency reduction, throughput improvements
7. **Security** — Hardening, fuzzing, cryptographic improvements

## Documentation Guidelines

### Files to Update

- **Feature**: Update relevant `.md` file or create new one
- **API Endpoint**: Update `spec/openapi.yaml` and docstrings
- **CLI Command**: Update `cli-reference.md`
- **Architecture Change**: Update `ARCHITECTURE.md`
- **Security**: Update `SECURITY.md`

### Documentation Standards

- Clear, concise language
- Code examples where applicable
- Link to related documentation
- Keep in sync with code

## Security Reporting

**Do not** open a public issue for security vulnerabilities. Instead:

1. Email `security@example.com`
2. Include details and reproduction steps
3. Allow 7 days for response
4. Embargo until patch is released

## Performance Considerations

When contributing:

- **Policy Engine**: Target <50ms latency
- **Storage**: Append-only design; no blocking writes
- **Network**: Minimize external API calls
- **Memory**: Keep per-execution overhead <10MB

Profile before/after:

```bash
python -m cProfile -s cumulative -m rif execute --intent "test"
```

## Versioning

We follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (rare; discussed in issue first)
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes

See `release-engineering-guide.md` for release process.

## Questions?

- **Usage**: Check `README.md` and `docs/`
- **Development**: See `DEVELOPMENT.md`
- **Architecture**: Read `ARCHITECTURE.md`
- **Security**: Review `SECURITY.md`
- **Discussions**: GitHub Discussions
- **Issues**: GitHub Issues

## License

All contributions are under MIT License. By contributing, you agree to this license.

Thank you for contributing to RIF Runtime! ✨
