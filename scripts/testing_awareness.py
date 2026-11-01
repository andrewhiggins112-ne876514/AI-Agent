"""Read-only inventory of test files, configuration, and static indicators."""

from __future__ import annotations

import ast
import configparser
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

from .repository_awareness import RepositoryCategory, RepositoryIndex


_TEST_CONFIGURATION_FILENAMES = frozenset(
    {"pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"}
)
_TEST_DIRECTORY_NAMES = frozenset({"test", "tests"})
_FIXTURE_DIRECTORY_NAMES = frozenset({"fixture", "fixtures"})
_TEST_FILE_SUFFIXES = frozenset({".py", ".pyi"})
_MAX_EVIDENCE_FILE_BYTES = 64 * 1024
_PYTEST_CONFIGURATION_SECTIONS = frozenset({"pytest", "tool:pytest"})
_UNITTEST_LIFECYCLE_METHODS = frozenset(
    {
        "setUp",
        "tearDown",
        "setUpClass",
        "tearDownClass",
        "asyncSetUp",
        "asyncTearDown",
    }
)


@dataclass(frozen=True)
class TestingInventory:
    """Static testing evidence from one repository index."""

    test_files: tuple[str, ...]
    test_directories: tuple[str, ...]
    configuration_candidates: tuple[str, ...]
    frameworks: tuple[str, ...]
    fixture_indicators: tuple[str, ...]
    platform_indicators: tuple[str, ...]
    complete: bool
    warnings: tuple[str, ...]


def build_testing_inventory(snapshot: RepositoryIndex) -> TestingInventory:
    """Summarize bounded static evidence without importing or executing code."""
    test_files = tuple(
        sorted(
            (
                file.path
                for file in snapshot.files
                if _is_test_file(file.path, file.category)
            ),
            key=str.casefold,
        )
    )
    test_directories = tuple(
        sorted(
            {
                directory
                for path in test_files
                for directory in _directories_named(path, _TEST_DIRECTORY_NAMES)
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
    complete = snapshot.complete
    if not configuration_candidates:
        complete = False
        warnings.append(
            "No recognized test configuration file is present in the indexed "
            "snapshot; configuration evidence is incomplete."
        )
    else:
        warnings.append(
            "Configuration files were inspected only for supported "
            "framework markers; settings and runnable commands are unknown."
        )

    root = _resolve_root(snapshot.root, warnings)
    if root is None:
        complete = False

    candidate_paths = {
        *test_files,
        *configuration_candidates,
        *(
            file.path
            for file in snapshot.files
            if _is_fixture_source(file.path)
        ),
    }
    frameworks: set[str] = set()
    fixture_indicators: set[str] = set()
    platform_indicators: set[str] = set()

    for path in sorted(candidate_paths, key=str.casefold):
        if root is None:
            break
        content = _read_indexed_file(root, path, warnings)
        if content is None:
            complete = False
            continue

        filename = PurePosixPath(path).name.casefold()
        if filename in _TEST_CONFIGURATION_FILENAMES:
            config_framework, error = _configuration_framework(path, content)
            if error:
                complete = False
                warnings.append(f"{path}: {error}")
            if config_framework:
                frameworks.add(config_framework)

        if PurePosixPath(path).suffix.casefold() not in {".py", ".pyi"}:
            continue
        if any(
            part.casefold() in _FIXTURE_DIRECTORY_NAMES
            for part in PurePosixPath(path).parts[:-1]
        ):
            fixture_indicators.add(f"{path}: file is in a fixture directory")
        if filename == "conftest.py":
            fixture_indicators.add(f"{path}: pytest fixture discovery file")
        if PurePosixPath(path).suffix.casefold() != ".py":
            continue

        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError as error:
            complete = False
            warnings.append(f"{path}: cannot inspect Python syntax: {error.msg}")
            continue

        _collect_python_evidence(
            path,
            tree,
            frameworks,
            fixture_indicators,
            platform_indicators,
        )

    if not frameworks:
        warnings.append(
            "No supported test framework was identified from inspected "
            "configuration or Python imports; framework is unknown."
        )
    if not fixture_indicators:
        warnings.append(
            "No static fixture indicator was identified; dynamic or external "
            "fixtures may be missed."
        )
    if not platform_indicators:
        warnings.append(
            "No static platform indicator was identified; platform "
            "compatibility is unknown."
        )
    if tomllib is None and any(
        PurePosixPath(path).name.casefold() == "pyproject.toml"
        for path in configuration_candidates
    ):
        complete = False
        warnings.append(
            "pyproject.toml could not be validated because tomllib is "
            "unavailable in this Python runtime."
        )

    return TestingInventory(
        test_files=test_files,
        test_directories=test_directories,
        configuration_candidates=configuration_candidates,
        frameworks=tuple(sorted(frameworks)),
        fixture_indicators=tuple(sorted(fixture_indicators, key=str.casefold)),
        platform_indicators=tuple(sorted(platform_indicators, key=str.casefold)),
        complete=complete,
        warnings=tuple(warnings),
    )


def _resolve_root(root: Path, warnings: list[str]) -> Path | None:
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        warnings.append(
            "Repository snapshot root cannot be read "
            f"({type(error).__name__})."
        )
        return None
    if not resolved.is_dir():
        warnings.append("Repository snapshot root is not a directory.")
        return None
    return resolved


def _read_indexed_file(
    root: Path,
    relative_path: str,
    warnings: list[str],
) -> str | None:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        warnings.append(f"{relative_path}: unsafe indexed path was not inspected.")
        return None

    try:
        path = root.joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(root)
        if not path.is_file():
            warnings.append(f"{relative_path}: indexed evidence is not a file.")
            return None
        with path.open("rb") as file:
            content = file.read(_MAX_EVIDENCE_FILE_BYTES + 1)
    except (OSError, RuntimeError, ValueError) as error:
        warnings.append(
            f"{relative_path}: cannot read indexed evidence "
            f"({type(error).__name__})."
        )
        return None

    if len(content) > _MAX_EVIDENCE_FILE_BYTES:
        warnings.append(
            f"{relative_path}: exceeds the {_MAX_EVIDENCE_FILE_BYTES}-byte "
            "evidence limit and was not inspected."
        )
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        warnings.append(f"{relative_path}: evidence is not valid UTF-8.")
        return None


def _configuration_framework(
    path: str,
    content: str,
) -> tuple[str | None, str | None]:
    filename = PurePosixPath(path).name.casefold()
    if filename == "pyproject.toml":
        if tomllib is None:
            return None, None
        try:
            parsed = tomllib.loads(content)
        except tomllib.TOMLDecodeError as error:
            return None, (
                "malformed TOML configuration "
                f"({type(error).__name__}); contents were not included."
            )
        tool = parsed.get("tool", {})
        return (
            ("pytest", None)
            if isinstance(tool, dict) and "pytest" in tool
            else (None, None)
        )

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(content)
    except configparser.Error as error:
        return None, (
            "malformed INI configuration "
            f"({type(error).__name__}); contents were not included."
        )
    if parser.sections() and any(
        section.casefold() in _PYTEST_CONFIGURATION_SECTIONS
        for section in parser.sections()
    ):
        return "pytest", None
    return None, None


def _collect_python_evidence(
    path: str,
    tree: ast.AST,
    frameworks: set[str],
    fixture_indicators: set[str],
    platform_indicators: set[str],
) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules = (node.module or "",)
        else:
            modules = ()

        if "pytest" in modules:
            frameworks.add("pytest")
        if "unittest" in modules:
            frameworks.add("unittest")
        for module in modules:
            if module.startswith("win32"):
                platform_indicators.add(
                    f"{path}: imports Windows API module {module}"
                )

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in _UNITTEST_LIFECYCLE_METHODS:
                fixture_indicators.add(
                    f"{path}: unittest lifecycle method {node.name}"
                )
            if any(_decorator_name(item) == "fixture" for item in node.decorator_list):
                fixture_indicators.add(f"{path}: pytest fixture decorator")

        if isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "sys"
                and node.attr == "platform"
            ):
                platform_indicators.add(f"{path}: references sys.platform")
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "platform"
                and node.attr == "system"
            ):
                platform_indicators.add(f"{path}: references platform.system")


def _decorator_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Call):
        node = node.func
    while isinstance(node, ast.Attribute):
        if node.attr == "fixture":
            return "fixture"
        node = node.value
    return node.id if isinstance(node, ast.Name) and node.id == "fixture" else None


def _is_test_file(path: str, category: RepositoryCategory) -> bool:
    candidate = PurePosixPath(path)
    if candidate.suffix.casefold() not in _TEST_FILE_SUFFIXES:
        return False
    has_test_name = (
        candidate.name.casefold().startswith("test_")
        or candidate.stem.casefold().endswith("_test")
    )
    is_fixture_source = any(
        part.casefold() in _FIXTURE_DIRECTORY_NAMES
        for part in candidate.parts[:-1]
    )
    if is_fixture_source and not has_test_name:
        return False
    if category is RepositoryCategory.TEST:
        return True
    return (
        any(
            part.casefold() in _TEST_DIRECTORY_NAMES
            for part in candidate.parts[:-1]
        )
        or has_test_name
    )


def _is_fixture_source(path: str) -> bool:
    candidate = PurePosixPath(path)
    return (
        candidate.suffix.casefold() == ".py"
        and (
            candidate.name.casefold() == "conftest.py"
            or any(
                part.casefold() in _FIXTURE_DIRECTORY_NAMES
                for part in candidate.parts[:-1]
            )
        )
    )


def _directories_named(path: str, names: frozenset[str]) -> tuple[str, ...]:
    parts = PurePosixPath(path).parts[:-1]
    return tuple(
        PurePosixPath(*parts[:index]).as_posix()
        for index, part in enumerate(parts, start=1)
        if part.casefold() in names
    )
