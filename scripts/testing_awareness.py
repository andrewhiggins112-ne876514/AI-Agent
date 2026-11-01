"""Read-only inventory of test files and test configuration candidates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from .repository_awareness import RepositoryCategory, RepositoryIndex


_TEST_CONFIGURATION_FILENAMES = frozenset(
    {"pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"}
)
_TEST_DIRECTORY_NAMES = frozenset({"test", "tests"})
_TEST_FILE_SUFFIXES = frozenset({".py", ".pyi"})


@dataclass(frozen=True)
class TestingInventory:
    """Discovered paths; complete means the index and config candidate are present."""

    test_files: tuple[str, ...]
    test_directories: tuple[str, ...]
    configuration_candidates: tuple[str, ...]
    complete: bool
    warnings: tuple[str, ...]


def build_testing_inventory(snapshot: RepositoryIndex) -> TestingInventory:
    """Summarize test files and conventional config candidates from an index.

    This uses only the supplied repository snapshot. Configuration contents
    are not read, and no tests or commands are executed.
    """
    test_file_paths = tuple(
        file.path
        for file in snapshot.files
        if _is_test_file(file.path, file.category)
    )
    test_files = tuple(sorted(test_file_paths, key=str.casefold))
    test_directories = tuple(
        sorted(
            {
                directory
                for file in snapshot.files
                for directory in _test_directories_for_path(file.path)
            },
            key=str.casefold,
        )
    )
    configuration_candidates = tuple(
        sorted(
            (
                file.path
                for file in snapshot.files
                if PurePosixPath(file.path).name.casefold()
                in _TEST_CONFIGURATION_FILENAMES
            ),
            key=str.casefold,
        )
    )

    warnings = list(snapshot.warnings)
    if not configuration_candidates:
        warnings.append(
            "No recognized test configuration file is present in the indexed "
            "snapshot; framework configuration is unknown."
        )
    else:
        warnings.append(
            "Test configuration candidate paths were found, but file contents "
            "were not inspected; supported settings and runnable commands "
            "remain unknown."
        )

    return TestingInventory(
        test_files=test_files,
        test_directories=test_directories,
        configuration_candidates=configuration_candidates,
        complete=snapshot.complete and bool(configuration_candidates),
        warnings=tuple(warnings),
    )


def _is_test_file(path: str, category: RepositoryCategory) -> bool:
    if category is RepositoryCategory.TEST:
        return True

    candidate = PurePosixPath(path)
    if candidate.suffix.casefold() not in _TEST_FILE_SUFFIXES:
        return False
    return (
        any(
            part.casefold() in _TEST_DIRECTORY_NAMES
            for part in candidate.parts[:-1]
        )
        or candidate.name.casefold().startswith("test_")
        or candidate.stem.casefold().endswith("_test")
    )


def _test_directories_for_path(path: str) -> tuple[str, ...]:
    parts = PurePosixPath(path).parts[:-1]
    return tuple(
        PurePosixPath(*parts[:index]).as_posix()
        for index, part in enumerate(parts, start=1)
        if part.casefold() in _TEST_DIRECTORY_NAMES
    )
