"""Read-only inventory of test files and test configuration candidates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from .repository_awareness import RepositoryCategory, RepositoryIndex


_TEST_CONFIGURATION_FILENAMES = frozenset(
    {"pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"}
)


@dataclass(frozen=True)
class TestingInventory:
    """Discovered paths; completeness reflects index coverage and config presence."""

    test_files: tuple[str, ...]
    configuration_candidates: tuple[str, ...]
    complete: bool
    warnings: tuple[str, ...]


def build_testing_inventory(snapshot: RepositoryIndex) -> TestingInventory:
    """Summarize test files and conventional config candidates from an index.

    This uses only the supplied repository snapshot. Configuration contents
    are not read, and no tests or commands are executed.
    """
    test_files = tuple(
        file.path
        for file in snapshot.files
        if file.category is RepositoryCategory.TEST
    )
    configuration_candidates = tuple(
        file.path
        for file in snapshot.files
        if PurePosixPath(file.path).name.casefold()
        in _TEST_CONFIGURATION_FILENAMES
    )

    warnings = list(snapshot.warnings)
    if not configuration_candidates:
        warnings.append(
            "No recognized test configuration candidate was found; "
            "configuration is unknown."
        )
    else:
        warnings.append(
            "Configuration candidate contents were not inspected; "
            "validity and supported settings are unknown."
        )

    return TestingInventory(
        test_files=test_files,
        configuration_candidates=configuration_candidates,
        complete=snapshot.complete and bool(configuration_candidates),
        warnings=tuple(warnings),
    )
