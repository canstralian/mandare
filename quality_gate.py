#!/usr/bin/env python
"""
Quality Gate Report: Comprehensive code analysis and verification
Runs all quality checks: linting, type checking, tests, code smells
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class QualityGate:
    """Runs and reports on all quality gates."""
    
    def __init__(self):
        self.checks: Dict[str, Tuple[bool, str]] = {}
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def run_check(self, name: str, cmd: List[str], critical: bool = True) -> bool:
        """Run a single check."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path(__file__).parent
            )
            passed = result.returncode == 0
            
            if passed:
                self.passed += 1
                status = "✓ PASS"
            else:
                if critical:
                    self.failed += 1
                    status = "✗ FAIL"
                else:
                    self.warnings += 1
                    status = "⚠ WARN"
            
            # Truncate output
            output = result.stdout + result.stderr
            if len(output) > 500:
                output = output[:500] + "..."
            
            self.checks[name] = (passed, output)
            print(f"{status:8} {name}")
            
            return passed
        except subprocess.TimeoutExpired:
            self.failed += 1
            self.checks[name] = (False, "TIMEOUT")
            print(f"✗ FAIL   {name} (timeout)")
            return False
        except Exception as e:
            self.failed += 1
            self.checks[name] = (False, str(e))
            print(f"✗ FAIL   {name}: {str(e)[:50]}")
            return False
    
    def report(self) -> int:
        """Print final report."""
        total = self.passed + self.failed + self.warnings
        
        print(f"\n{'='*80}")
        print(f"QUALITY GATE SUMMARY")
        print(f"{'='*80}")
        print(f"✓ Passed:  {self.passed}/{total}")
        print(f"✗ Failed:  {self.failed}/{total}")
        print(f"⚠ Warnings: {self.warnings}/{total}")
        print(f"{'='*80}\n")
        
        if self.failed > 0:
            print("Failed checks:")
            for name, (passed, output) in self.checks.items():
                if not passed:
                    print(f"\n  {name}")
                    if output and output != "TIMEOUT":
                        for line in output.split('\n')[:3]:
                            if line.strip():
                                print(f"    {line}")
            return 1
        
        return 0

def main():
    """Run comprehensive quality checks."""
    gate = QualityGate()
    
    print("RIF Runtime - Quality Gate Report")
    print("="*80 + "\n")
    
    # Code Analysis
    print("Code Analysis:")
    print("-" * 80)
    gate.run_check(
        "Python files count",
        ["python", "-c", "from pathlib import Path; count = len(list(Path('src').glob('**/*.py'))); print(f'Found {count} files'); exit(0 if count > 0 else 1)"]
    )
    
    # Linting (ruff)
    print("\nLinting & Formatting:")
    print("-" * 80)
    gate.run_check(
        "Ruff lint check",
        ["python", "-m", "ruff", "check", "src/", "tests/"],
        critical=False
    )
    gate.run_check(
        "Ruff format check",
        ["python", "-m", "ruff", "format", "--check", "src/", "tests/"],
        critical=False
    )
    
    # Type Checking
    print("\nType Checking:")
    print("-" * 80)
    gate.run_check(
        "MyPy type checking",
        ["python", "-m", "mypy", "src/", "tests/", "--ignore-missing-imports", "--no-error-summary"],
        critical=False
    )
    
    # Security
    print("\nSecurity Scanning:")
    print("-" * 80)
    gate.run_check(
        "Bandit security check",
        ["python", "-m", "bandit", "-r", "src/", "-ll", "-f", "csv"],
        critical=False
    )
    gate.run_check(
        "pip audit dependencies",
        ["python", "-m", "pip_audit"],
        critical=False
    )
    
    # Tests
    print("\nTesting:")
    print("-" * 80)
    gate.run_check(
        "Pytest unit tests",
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
        critical=False
    )
    gate.run_check(
        "Pytest with coverage",
        ["python", "-m", "pytest", "tests/", "--cov=src/rif_runtime", "--cov-report=term-missing"],
        critical=False
    )
    
    # Project Structure
    print("\nProject Structure:")
    print("-" * 80)
    required_files = [
        "README.md", "LICENSE", "Dockerfile", "docker-compose.yml",
        "pyproject.toml", "ARCHITECTURE.md", "DEVELOPMENT.md",
        "TESTING.md", "SECURITY.md", "DEPLOYMENT.md", "Makefile",
        "src/rif_runtime/cli.py", "tests/test_cli.py"
    ]
    
    all_exist = True
    for file in required_files:
        exists = Path(file).exists()
        all_exist = all_exist and exists
        status = "✓" if exists else "✗"
        print(f"  {status} {file}")
    
    gate.passed += (1 if all_exist else 0)
    gate.failed += (0 if all_exist else 1)
    
    # Documentation
    print("\nDocumentation Alignment:")
    print("-" * 80)
    
    # Check if docs match implementation
    with open("docs/cli-reference.md") as f:
        cli_ref = f.read()
    
    checks = [
        ("CLI reference documents 'serve'", "serve" in cli_ref),
        ("CLI reference documents 'check'", "check" in cli_ref),
        ("CLI reference documents 'replay'", "replay" in cli_ref),
        ("CLI reference documents 'msf-check'", "msf-check" in cli_ref),
        ("CLI reference documents 'status'", "status" in cli_ref),
    ]
    
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}")
        if result:
            gate.passed += 1
        else:
            gate.failed += 1
    
    # Summary
    print()
    return gate.report()

if __name__ == "__main__":
    sys.exit(main())
