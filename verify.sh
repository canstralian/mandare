#!/bin/bash
# Quick verification script for Mandare

set -e

echo "================================"
echo "Mandare Verification Script"
echo "================================"
echo ""

# Check Python version
echo "[1/6] Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version"

# Install dependencies
echo "[2/6] Installing dependencies..."
pip install -q -e . 2>/dev/null || echo "⚠ Could not install package"

# Run linting
echo "[3/6] Running linters..."
if command -v ruff &> /dev/null; then
    ruff check src/ tests/ --quiet && echo "✓ Ruff checks passed" || echo "⚠ Ruff found issues"
else
    echo "⚠ Ruff not installed"
fi

# Run type checking
echo "[4/6] Running type checker..."
if command -v mypy &> /dev/null; then
    mypy src/ tests/ --quiet && echo "✓ MyPy checks passed" || echo "⚠ MyPy found issues"
else
    echo "⚠ MyPy not installed"
fi

# Run tests
echo "[5/6] Running tests..."
if command -v pytest &> /dev/null; then
    pytest tests/ -q --tb=short 2>/dev/null && echo "✓ Tests passed" || echo "⚠ Some tests failed"
else
    echo "⚠ Pytest not installed"
fi

# Check Docker
echo "[6/6] Checking Docker setup..."
if command -v docker &> /dev/null; then
    echo "✓ Docker installed"
    echo "  Build test image with: docker build -t mandare-server:latest ."
    echo "  Start dev stack with: docker compose up --build"
else
    echo "⚠ Docker not installed"
fi

echo ""
echo "================================"
echo "✓ Verification complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Read NEXT_STEPS.md"
echo "2. Review ARCHITECTURE.md"
echo "3. Run: make docker-up"
echo "4. Visit: http://localhost:8000/docs"
echo ""
