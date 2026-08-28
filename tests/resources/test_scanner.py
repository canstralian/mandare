from pathlib import Path

from mandare.resources import RepositoryScanner


def test_repository_exists() -> None:
    scanner = RepositoryScanner(Path("."))
    assert scanner.exists()


def test_module_count_is_positive() -> None:
    scanner = RepositoryScanner(Path("."))
    assert scanner.module_count() > 0


def test_test_count_is_positive() -> None:
    scanner = RepositoryScanner(Path("."))
    assert scanner.test_count() > 0


def test_missing_repository() -> None:
    scanner = RepositoryScanner(Path("definitely-not-a-real-directory"))
    assert not scanner.exists()
