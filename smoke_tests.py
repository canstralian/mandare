#!/usr/bin/env python
"""
RIF Runtime - Smoke Tests & Code Quality Report
Comprehensive verification script for quality assurance
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

class QualityReport:
    """Generates comprehensive quality report."""
    
    def __init__(self):
        self.results: dict[str, Any] = {}
        self.passed: int = 0
        self.failed: int = 0
    
    def section(self, name: str) -> None:
        """Start a new section."""
        print(f"\n{'='*70}")
        print(f"  {name}")
        print(f"{'='*70}")
        self.results[name] = {}
    
    def test(self, name: str, cmd: list[str], critical: bool = False) -> bool:
        """Run a test and report result."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            success = result.returncode == 0
            
            if success:
                self.passed += 1
                status = "✓ PASS"
            else:
                self.failed += 1
                status = "✗ FAIL" if critical else "⚠ WARN"
            
            print(f"{status:8} | {name}")
            if not success and result.stdout:
                print(f"         Output: {result.stdout[:100]}")
            
            self.results[list(self.results.keys())[-1]][name] = {
                "status": "pass" if success else "fail",
                "critical": critical
            }
            return success
        except subprocess.TimeoutExpired:
            print(f"✗ TIMEOUT | {name}")
            self.failed += 1
            return False
        except Exception as e:
            print(f"✗ ERROR   | {name}: {str(e)[:50]}")
            self.failed += 1
            return False
    
    def summary(self) -> None:
        """Print final summary."""
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"  SUMMARY: {self.passed}/{total} tests passed")
        print(f"{'='*70}\n")
        
        if self.failed > 0:
            sys.exit(1)

def run_smoke_tests() -> None:
    """Execute comprehensive quality checks."""
    
    report = QualityReport()
    base_dir = Path(__file__).parent
    
    # Smoke Tests
    report.section("SMOKE TESTS")
    report.test("API Health", ["docker", "compose", "exec", "-T", "server", 
                               "python", "-c", "import httpx; r = httpx.get('http://localhost:8000/health'); assert r.status_code == 200"])
    report.test("FastAPI Import", ["docker", "compose", "exec", "-T", "server", 
                                   "python", "-c", "from rif_runtime.api import app; print('✓')"])
    report.test("CLI Available", ["docker", "compose", "exec", "-T", "server", 
                                  "rif", "--help"])
    
    # Code Analysis (local)
    report.section("CODE ANALYSIS")
    
    # Count Python files
    py_files = list(base_dir.glob("src/rif_runtime/**/*.py"))
    print(f"   Python files: {len(py_files)}")
    print(f"   Test files: {len(list(base_dir.glob('tests/**/*.py')))}")
    
    # Check for common smells
    report.section("CODE SMELLS")
    
    # Long functions (>50 lines)
    long_functions = []
    for py_file in py_files:
        try:
            with open(py_file) as f:
                content = f.read()
                lines = content.split('\n')
                in_func = False
                func_start = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('def '):
                        if in_func and i - func_start > 50:
                            long_functions.append(f"{py_file.name}:{func_start}")
                        in_func = True
                        func_start = i
        except:
            pass
    
    if long_functions:
        print(f"⚠ WARN   | Long functions (>50 lines): {len(long_functions)}")
        for item in long_functions[:5]:
            print(f"         - {item}")
    else:
        print(f"✓ PASS   | No excessively long functions")
        report.passed += 1
    
    # Missing type hints
    missing_hints = 0
    for py_file in py_files:
        try:
            with open(py_file) as f:
                content = f.read()
                if 'def ' in content and '->' not in content:
                    missing_hints += 1
        except:
            pass
    
    if missing_hints > 0:
        print(f"⚠ WARN   | Files with missing type hints: {missing_hints}")
    else:
        print(f"✓ PASS   | Type hints present")
        report.passed += 1
    
    # Complexity check
    report.section("DEPENDENCIES")
    report.test("Requirements Syntax", ["python", "-m", "py_compile", 
                                       str(base_dir / "requirements.txt")])
    
    # Docker
    report.section("CONTAINERIZATION")
    report.test("Dockerfile Validity", ["docker", "build", "-t", "rif-runtime-test:latest", 
                                        "--dry-run", "."], critical=False)
    
    # File structure
    report.section("PROJECT STRUCTURE")
    
    required_files = [
        "README.md", "LICENSE", "Dockerfile", "docker-compose.yml",
        "pyproject.toml", "ARCHITECTURE.md", "DEVELOPMENT.md",
        "TESTING.md", "SECURITY.md", "DEPLOYMENT.md", "Makefile"
    ]
    
    for file in required_files:
        exists = (base_dir / file).exists()
        status = "✓ PASS" if exists else "✗ FAIL"
        print(f"{status:8} | {file}")
        if exists:
            report.passed += 1
        else:
            report.failed += 1
    
    # API Endpoints
    report.section("API ENDPOINTS")
    endpoints = [
        "/health",
        "/docs",
        "/openapi.json",
        "/v1/environments",
        "/v1/graph/summary",
        "/v1/telemetry/summary",
    ]
    
    for endpoint in endpoints:
        cmd = [
            "docker", "compose", "exec", "-T", "server", "python", "-c",
            f"import httpx; r = httpx.get('http://localhost:8000{endpoint}'); print(f'{{r.status_code}}')"
        ]
        report.test(endpoint, cmd, critical=False)
    
    # Print summary
    report.summary()

if __name__ == "__main__":
    try:
        run_smoke_tests()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
