#!/usr/bin/env python
"""
RIF Runtime - Comprehensive Code Quality Report
Analyzes project for code smells, complexity, and best practices
"""

import json
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

class CodeSmellDetector:
    """Detects code smells and quality issues."""
    
    def __init__(self, src_dir: Path):
        self.src_dir = src_dir
        self.issues: Dict[str, List[str]] = defaultdict(list)
        self.stats = {
            "total_files": 0,
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "avg_function_lines": 0,
            "files_with_issues": 0,
        }
    
    def analyze(self) -> None:
        """Run full analysis."""
        print("Scanning Python files...")
        
        py_files = list(self.src_dir.glob("**/*.py"))
        self.stats["total_files"] = len(py_files)
        
        for py_file in py_files:
            self._analyze_file(py_file)
        
        if self.stats["total_functions"] > 0:
            self.stats["avg_function_lines"] = self.stats["total_lines"] // self.stats["total_functions"]
    
    def _analyze_file(self, py_file: Path) -> None:
        """Analyze individual file."""
        try:
            with open(py_file, "r") as f:
                content = f.read()
                lines = content.split("\n")
        except:
            return
        
        file_issues = []
        self.stats["total_lines"] += len(lines)
        
        # Issue 1: Long functions (>50 lines)
        self._check_long_functions(py_file, lines, file_issues)
        
        # Issue 2: Missing docstrings
        self._check_docstrings(py_file, lines, file_issues)
        
        # Issue 3: Type hints
        self._check_type_hints(py_file, lines, file_issues)
        
        # Issue 4: Complex conditionals
        self._check_complexity(py_file, lines, file_issues)
        
        # Issue 5: Code duplication
        self._check_duplication(py_file, content, file_issues)
        
        # Issue 6: Unused imports
        self._check_unused_imports(py_file, content, file_issues)
        
        # Issue 7: Magic numbers
        self._check_magic_numbers(py_file, lines, file_issues)
        
        # Issue 8: Global variables
        self._check_global_variables(py_file, lines, file_issues)
        
        if file_issues:
            self.stats["files_with_issues"] += 1
            self.issues[str(py_file)] = file_issues
    
    def _check_long_functions(self, py_file: Path, lines: List[str], issues: List[str]) -> None:
        """Detect functions longer than 50 lines."""
        in_func = False
        func_start = 0
        func_name = ""
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith("def "):
                if in_func and i - func_start > 50:
                    issues.append(f"  Long function '{func_name}' ({i - func_start} lines, line {func_start})")
                in_func = True
                func_start = i
                func_name = stripped.split("(")[0].replace("def ", "")
                indent_level = len(line) - len(line.lstrip())
                self.stats["total_functions"] += 1
            
            elif in_func and stripped and not stripped.startswith("#"):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and stripped and not stripped.startswith("@"):
                    if i - func_start > 50:
                        issues.append(f"  Long function '{func_name}' ({i - func_start} lines, line {func_start})")
                    in_func = False
            
            if stripped.startswith("class "):
                self.stats["total_classes"] += 1
    
    def _check_docstrings(self, py_file: Path, lines: List[str], issues: List[str]) -> None:
        """Check for missing docstrings on public functions/classes."""
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("def ") or line.strip().startswith("class "):
                if not line.strip().startswith("def _") and not line.strip().startswith("class _"):
                    if i + 1 < len(lines) and '"""' not in lines[i + 1] and "'''" not in lines[i + 1]:
                        name = line.strip().split("(")[0].replace("def ", "").replace("class ", "")
                        issues.append(f"  Missing docstring for public {line.strip().split()[0]} '{name}'")
            i += 1
    
    def _check_type_hints(self, py_file: Path, lines: List[str], issues: List[str]) -> None:
        """Check for missing type hints."""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") and " ->" not in stripped and "__init__" not in stripped:
                if not stripped.startswith("def _"):
                    name = stripped.split("(")[0].replace("def ", "")
                    if ":" in stripped and "->" not in stripped:
                        issues.append(f"  Missing return type hint for '{name}' (line {i+1})")
    
    def _check_complexity(self, py_file: Path, lines: List[str], issues: List[str]) -> None:
        """Check for overly complex conditionals."""
        for i, line in enumerate(lines):
            if_count = line.count(" if ") + line.count(" and ") + line.count(" or ")
            if if_count > 3:
                issues.append(f"  Complex conditional (line {i+1}): {if_count} operators")
    
    def _check_duplication(self, py_file: Path, content: str, issues: List[str]) -> None:
        """Check for potential code duplication."""
        lines = content.split("\n")
        patterns = defaultdict(int)
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) > 20 and not stripped.startswith("#"):
                patterns[stripped] += 1
        
        for pattern, count in patterns.items():
            if count > 3 and not any(kw in pattern for kw in ["import", "from", "return"]):
                issues.append(f"  Potential duplication: '{pattern[:40]}...' appears {count} times")
    
    def _check_unused_imports(self, py_file: Path, content: str, issues: List[str]) -> None:
        """Check for unused imports (basic check)."""
        lines = content.split("\n")
        imports = {}
        
        for i, line in enumerate(lines):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                # Extract imported name
                if "import " in line:
                    parts = line.split("import ")[-1]
                    name = parts.split(" as ")[-1].strip()
                    imports[name] = i
        
        for name, line_no in imports.items():
            if content.count(name) == 1 and name not in ["__future__"]:
                issues.append(f"  Potential unused import '{name}' (line {line_no+1})")
    
    def _check_magic_numbers(self, py_file: Path, lines: List[str], issues: List[str]) -> None:
        """Check for magic numbers."""
        magic_nums = set()
        for i, line in enumerate(lines):
            # Simple check: numeric literals not in constants or comments
            import re
            for match in re.finditer(r'[\s=\(]\d{2,}\b', line):
                if not line.strip().startswith("#"):
                    magic_nums.add((i+1, match.group().strip()))
        
        if len(magic_nums) > 5:
            issues.append(f"  Magic numbers detected ({len(magic_nums)} instances)")
    
    def _check_global_variables(self, py_file: Path, lines: List[str], issues: List[str]) -> None:
        """Check for global variables at module level."""
        in_class = False
        in_func = False
        for i, line in enumerate(lines):
            if line.strip().startswith("class "):
                in_class = True
            elif line.strip().startswith("def "):
                in_func = True
            elif line.strip() and not line.strip().startswith("#"):
                if not in_class and not in_func and "=" in line and not line.strip().startswith("@"):
                    if line[0] not in [" ", "\t"] and not line.strip().startswith("import"):
                        var = line.split("=")[0].strip()
                        if var.isupper():
                            continue  # Constants are OK
                        issues.append(f"  Global variable '{var}' (line {i+1})")
    
    def report(self) -> None:
        """Print comprehensive report."""
        print("\n" + "="*80)
        print(" CODE SMELL DETECTION REPORT")
        print("="*80)
        
        print(f"\nProject Statistics:")
        print(f"  Total Python files: {self.stats['total_files']}")
        print(f"  Total lines of code: {self.stats['total_lines']}")
        print(f"  Total functions: {self.stats['total_functions']}")
        print(f"  Total classes: {self.stats['total_classes']}")
        print(f"  Average function length: {self.stats['avg_function_lines']} lines")
        print(f"  Files with issues: {self.stats['files_with_issues']}")
        
        if not self.issues:
            print(f"\n✓ No code smells detected!")
            return
        
        print(f"\nCode Smells by File ({len(self.issues)} files):")
        print("-" * 80)
        
        total_issues = sum(len(v) for v in self.issues.values())
        
        # Sort by file
        for file_path in sorted(self.issues.keys()):
            issues = self.issues[file_path]
            rel_path = Path(file_path).relative_to(self.src_dir.parent) if self.src_dir.parent in Path(file_path).parents else Path(file_path).name
            print(f"\n{rel_path} ({len(issues)} issues):")
            for issue in sorted(set(issues))[:5]:  # Limit to 5 per file
                print(f"  {issue}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more")
        
        print(f"\n" + "="*80)
        print(f"Total Issues Found: {total_issues}")
        print(f"Severity: {'LOW' if total_issues < 20 else 'MEDIUM' if total_issues < 50 else 'HIGH'}")
        print("="*80 + "\n")

def main():
    """Main entry point."""
    src_dir = Path(__file__).parent / "src" / "rif_runtime"
    
    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        sys.exit(1)
    
    detector = CodeSmellDetector(src_dir)
    detector.analyze()
    detector.report()
    
    # Return exit code based on severity
    total_issues = sum(len(v) for v in detector.issues.values())
    if total_issues > 100:
        sys.exit(1)

if __name__ == "__main__":
    main()
