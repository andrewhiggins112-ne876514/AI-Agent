"""Read-only discovery and metadata indexing for one repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatchcase
import os
from pathlib import Path, PurePosixPath
import re


class RepositoryCategory(str, Enum):
    SOURCE = "source"
    TEST = "test"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    ROADMAP = "roadmap"
    DECISION = "decision"
    OTHER = "other"


class Importance(str, Enum):
    CORE = "core"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass(frozen=True)
class RepositoryFileMetadata:
    path: str
    file_type: str
    category: RepositoryCategory
    importance: Importance


@dataclass(frozen=True)
class IndexLimits:
    max_depth: int = 20
    max_files: int = 5000
    max_file_bytes: int = 10 * 1024 * 1024
    max_directories: int = 5000
    max_directory_entries: int = 10000

    def __post_init__(self) -> None:
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        if self.max_files < 1:
            raise ValueError("max_files must be at least 1")
        if self.max_file_bytes < 1:
            raise ValueError("max_file_bytes must be at least 1")
        if self.max_directories < 1:
            raise ValueError("max_directories must be at least 1")
        if self.max_directory_entries < 1:
            raise ValueError("max_directory_entries must be at least 1")


@dataclass(frozen=True)
class RepositoryIndex:
    root: Path
    files: tuple[RepositoryFileMetadata, ...]
    indexed_at: datetime
    complete: bool
    excluded_count: int
    warnings: tuple[str, ...]
    limits: IndexLimits

    @classmethod
    def build(
        cls,
        root: str | os.PathLike[str],
        limits: IndexLimits | None = None,
    ) -> RepositoryIndex:
        """Build an in-memory index without writing to or executing the repo."""
        repository_root = Path(root).expanduser().resolve(strict=True)
        if not repository_root.is_dir():
            raise NotADirectoryError(f"Repository root is not a directory: {root}")

        scan_limits = limits or IndexLimits()
        scanner = _RepositoryScanner(repository_root, scan_limits)
        return scanner.scan()

    def refresh(self) -> RepositoryIndex:
        """Manually rebuild this snapshot from its original repository root."""
        return type(self).build(self.root, self.limits)


class _RepositoryScanner:
    _SOURCE_TYPES = {".py", ".pyi"}
    _DOCUMENT_TYPES = {".md", ".markdown", ".rst", ".txt"}
    _OTHER_TYPES = {".toml", ".ini", ".cfg", ".yaml", ".yml", ".json"}
    _HARD_EXCLUDED_DIRECTORIES = {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        "site-packages",
        "logs",
        "memory",
        "build",
        "dist",
        "target",
        "coverage",
    }
    _HARD_EXCLUDED_FILENAMES = {
        ".env",
        ".git-credentials",
        "credentials",
        "credentials.json",
        "secrets",
        "secrets.json",
    }
    _SENSITIVE_FILENAME_PARTS = {
        "credential",
        "credentials",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
    _HARD_EXCLUDED_SUFFIXES = {
        ".bak",
        ".db",
        ".key",
        ".log",
        ".p12",
        ".pfx",
        ".pem",
        ".sqlite",
        ".sqlite3",
        ".temp",
        ".tmp",
    }
    _CORE_DOCUMENTS = {
        "decisions",
        "project_status",
        "project_vision",
        "roadmap",
    }
    _ARCHITECTURE_MARKERS = {
        "architecture",
        "awareness",
        "backend",
        "design",
        "developer_agent",
        "implementation_plan",
        "options",
        "spec",
        "specification",
    }

    def __init__(self, root: Path, limits: IndexLimits) -> None:
        self.root = root
        self.limits = limits
        self.files: list[RepositoryFileMetadata] = []
        self.warnings: list[str] = []
        self.excluded_count = 0
        self.complete = True
        self._visited_files = 0
        self._visited_directories = 0
        self._limit_reached = False

    def scan(self) -> RepositoryIndex:
        self._scan_directory(self.root, depth=0, inherited_rules=())
        return RepositoryIndex(
            root=self.root,
            files=tuple(sorted(self.files, key=lambda item: item.path.casefold())),
            indexed_at=datetime.now(timezone.utc),
            complete=self.complete,
            excluded_count=self.excluded_count,
            warnings=tuple(self.warnings),
            limits=self.limits,
        )

    def _scan_directory(
        self,
        directory: Path,
        depth: int,
        inherited_rules: tuple[_IgnoreRule, ...],
    ) -> None:
        if self._limit_reached:
            return

        self._visited_directories += 1
        if self._visited_directories > self.limits.max_directories:
            self.complete = False
            self._limit_reached = True
            self._warn(
                directory.relative_to(self.root).as_posix(),
                "Maximum directory count reached",
            )
            return

        relative_directory = directory.relative_to(self.root).as_posix()
        rules = inherited_rules + self._read_ignore_rules(
            directory,
            relative_directory,
        )

        try:
            with os.scandir(directory) as iterator:
                entries = []
                for entry in iterator:
                    entries.append(entry)
                    if len(entries) > self.limits.max_directory_entries:
                        self.complete = False
                        self._limit_reached = True
                        self._warn(
                            relative_directory,
                            "Maximum directory entry count reached",
                        )
                        return
                entries.sort(key=lambda item: item.name.casefold())
        except OSError as error:
            self._warn(relative_directory, f"Cannot read directory: {error}")
            return

        for entry in entries:
            if self._limit_reached:
                return

            if entry.name == ".gitignore":
                continue

            entry_path = Path(entry.path)
            relative_path = entry_path.relative_to(self.root).as_posix()

            try:
                if entry.is_symlink():
                    self.excluded_count += 1
                    continue
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError as error:
                self._warn(relative_path, f"Cannot inspect entry: {error}")
                continue

            if is_directory:
                if entry.name.casefold() in self._HARD_EXCLUDED_DIRECTORIES:
                    self.excluded_count += 1
                    continue
                if depth >= self.limits.max_depth:
                    self.complete = False
                    self.excluded_count += 1
                    self._warn(relative_path, "Maximum scan depth reached")
                    continue
                self._scan_directory(entry_path, depth + 1, rules)
                continue

            self._visited_files += 1
            if self._visited_files > self.limits.max_files:
                self.complete = False
                self._limit_reached = True
                self._warn(relative_path, "Maximum file count reached")
                return

            try:
                if not entry.is_file(follow_symlinks=False):
                    self.excluded_count += 1
                    continue
                file_size = entry.stat(follow_symlinks=False).st_size
            except OSError as error:
                self._warn(relative_path, f"Cannot inspect file: {error}")
                continue

            if self._is_hard_excluded_file(entry.name):
                self.excluded_count += 1
                continue

            if _is_gitignored(relative_path, is_directory=False, rules=rules):
                self.excluded_count += 1
                continue

            if file_size > self.limits.max_file_bytes:
                self.complete = False
                self.excluded_count += 1
                self._warn(relative_path, "Maximum file size exceeded")
                continue

            metadata = _classify_file(relative_path)
            if metadata is not None:
                self.files.append(metadata)

    def _read_ignore_rules(
        self,
        directory: Path,
        relative_directory: str,
    ) -> tuple[_IgnoreRule, ...]:
        ignore_file = directory / ".gitignore"
        try:
            if ignore_file.is_symlink():
                self.excluded_count += 1
                return ()
            if not ignore_file.is_file():
                return ()
            if ignore_file.stat().st_size > 128 * 1024:
                self.complete = False
                self._warn(relative_directory, ".gitignore exceeds size limit")
                return ()
            lines = ignore_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            self.complete = False
            self._warn(relative_directory, f"Cannot read .gitignore: {error}")
            return ()

        parsed_rules = []
        for line in lines:
            rule = _parse_ignore_rule(line, relative_directory)
            if rule is not None:
                parsed_rules.append(rule)
        return tuple(parsed_rules)

    def _is_hard_excluded_file(self, filename: str) -> bool:
        lowered = filename.casefold()
        name_parts = set(re.split(r"[^a-z0-9]+", lowered))
        return (
            lowered in self._HARD_EXCLUDED_FILENAMES
            or lowered.startswith(".env.")
            or Path(lowered).suffix in self._HARD_EXCLUDED_SUFFIXES
            or bool(name_parts & self._SENSITIVE_FILENAME_PARTS)
        )

    def _warn(self, relative_path: str, message: str) -> None:
        self.complete = False
        location = relative_path or "."
        self.warnings.append(f"{location}: {message}")


@dataclass(frozen=True)
class _IgnoreRule:
    base: str
    pattern: str
    negated: bool
    directory_only: bool
    anchored: bool


def _parse_ignore_rule(line: str, base: str) -> _IgnoreRule | None:
    value = line.rstrip()
    if not value or value.startswith("#"):
        return None
    if value.startswith(r"\#"):
        value = value[1:]
    negated = value.startswith("!")
    if negated:
        value = value[1:]
    elif value.startswith(r"\!"):
        value = value[1:]
    if not value:
        return None
    anchored = value.startswith("/")
    value = value.lstrip("/")
    directory_only = value.endswith("/")
    value = value.rstrip("/")
    if not value:
        return None
    return _IgnoreRule(
        base=base,
        pattern=value,
        negated=negated,
        directory_only=directory_only,
        anchored=anchored,
    )


def _is_gitignored(
    relative_path: str,
    is_directory: bool,
    rules: tuple[_IgnoreRule, ...],
) -> bool:
    parts = PurePosixPath(relative_path).parts
    parent_ignored = False
    directory_prefixes = parts if is_directory else parts[:-1]
    for index in range(len(directory_prefixes)):
        directory_path = PurePosixPath(
            *directory_prefixes[:index + 1]
        ).as_posix()
        parent_ignored = _apply_ignore_rules(
            directory_path,
            is_directory=True,
            inherited=parent_ignored,
            rules=rules,
        )
    if is_directory:
        return parent_ignored
    if parent_ignored:
        return True
    return _apply_ignore_rules(
        relative_path,
        is_directory=False,
        inherited=parent_ignored,
        rules=rules,
    )


def _apply_ignore_rules(
    relative_path: str,
    is_directory: bool,
    inherited: bool,
    rules: tuple[_IgnoreRule, ...],
) -> bool:
    ignored = inherited
    for rule in rules:
        if _rule_matches_exact(rule, relative_path, is_directory):
            ignored = not rule.negated
    return ignored


def _rule_matches_exact(
    rule: _IgnoreRule,
    relative_path: str,
    is_directory: bool,
) -> bool:
    if rule.directory_only and not is_directory:
        return False
    try:
        candidate = PurePosixPath(relative_path).relative_to(
            PurePosixPath(rule.base)
        )
    except ValueError:
        return False
    if not candidate.parts:
        return False
    if "/" not in rule.pattern:
        if rule.anchored and len(candidate.parts) != 1:
            return False
        return fnmatchcase(candidate.name, rule.pattern)
    return candidate.match(rule.pattern)


def _classify_file(relative_path: str) -> RepositoryFileMetadata | None:
    path = PurePosixPath(relative_path)
    suffix = path.suffix.casefold()
    if suffix not in (
        _RepositoryScanner._SOURCE_TYPES
        | _RepositoryScanner._DOCUMENT_TYPES
        | _RepositoryScanner._OTHER_TYPES
    ):
        return None

    category = _classify_category(path, suffix)
    importance = _classify_importance(path, category)
    return RepositoryFileMetadata(
        path=path.as_posix(),
        file_type=_file_type(suffix),
        category=category,
        importance=importance,
    )


def _classify_category(
    path: PurePosixPath,
    suffix: str,
) -> RepositoryCategory:
    stem = path.stem.casefold()
    tokens = set(stem.replace("-", "_").split("_"))
    if suffix in _RepositoryScanner._SOURCE_TYPES:
        if (
            path.name.casefold().startswith("test_")
            or path.stem.casefold().endswith("_test")
            or any(part.casefold() in {"test", "tests"} for part in path.parts[:-1])
        ):
            return RepositoryCategory.TEST
        return RepositoryCategory.SOURCE

    if "roadmap" in tokens:
        return RepositoryCategory.ROADMAP
    if "decision" in tokens or "decisions" in tokens:
        return RepositoryCategory.DECISION
    if (
        tokens & _RepositoryScanner._ARCHITECTURE_MARKERS
        or "implementation_plan" in stem.replace("-", "_")
        or "developer_agent" in stem.replace("-", "_")
        or "backends" in tokens
    ):
        return RepositoryCategory.ARCHITECTURE
    if suffix in _RepositoryScanner._DOCUMENT_TYPES:
        return RepositoryCategory.DOCUMENTATION
    return RepositoryCategory.OTHER


def _classify_importance(
    path: PurePosixPath,
    category: RepositoryCategory,
) -> Importance:
    stem = path.stem.casefold().replace("-", "_")
    if stem in _RepositoryScanner._CORE_DOCUMENTS:
        return Importance.CORE
    if category in {
        RepositoryCategory.ARCHITECTURE,
        RepositoryCategory.ROADMAP,
        RepositoryCategory.DECISION,
        RepositoryCategory.TEST,
    }:
        return Importance.HIGH
    if category in {RepositoryCategory.SOURCE, RepositoryCategory.DOCUMENTATION}:
        return Importance.NORMAL
    return Importance.LOW


def _file_type(suffix: str) -> str:
    known_types = {
        ".cfg": "configuration",
        ".ini": "configuration",
        ".json": "json",
        ".markdown": "markdown",
        ".md": "markdown",
        ".py": "python",
        ".pyi": "python_stub",
        ".rst": "restructured_text",
        ".toml": "toml",
        ".txt": "plain_text",
        ".yaml": "yaml",
        ".yml": "yaml",
    }
    return known_types[suffix]
