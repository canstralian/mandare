from __future__ import annotations

from pathlib import Path

from .inventory import ModuleInfo, TestInfo


class RepositoryScanner:
    """
    Observes the structure of a local repository.

    The scanner performs no Git operations and makes no network requests.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def exists(self) -> bool:
        return self.root.exists()

    def modules(self) -> tuple[ModuleInfo, ...]:
        modules: list[ModuleInfo] = []

        for path in sorted(self.root.rglob("*.py")):
            if "tests" in path.parts:
                continue

            modules.append(
                ModuleInfo(
                    name=path.stem,
                    path=path,
                )
            )

        return tuple(modules)

    def tests(self) -> tuple[TestInfo, ...]:
        tests: list[TestInfo] = []

        for path in sorted(self.root.rglob("test_*.py")):
            tests.append(
                TestInfo(
                    name=path.stem,
                    path=path,
                )
            )

        return tuple(tests)

    def module_count(self) -> int:
        return len(self.modules())

    def test_count(self) -> int:
        return len(self.tests())
