"""Read-only architecture metadata derived from indexed Markdown documents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlsplit

from scripts.repository_awareness import (
    IndexLimits,
    RepositoryCategory,
    RepositoryIndex,
)


class ArchitectureDocumentType(str, Enum):
    VISION = "vision"
    ROADMAP = "roadmap"
    DECISION = "decision"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION_PLAN = "implementation_plan"


class ArchitectureRelationType(str, Enum):
    REFERENCES = "references"
    BELONGS_TO_PHASE = "belongs_to_phase"
    DESCRIBES_AREA = "describes_area"


@dataclass(frozen=True)
class ArchitectureDocument:
    path: str
    document_type: ArchitectureDocumentType
    title: str
    phase_ids: tuple[str, ...]
    architecture_areas: tuple[str, ...]
    headings: tuple[str, ...]


@dataclass(frozen=True)
class ArchitectureRelationship:
    source_path: str
    relation_type: ArchitectureRelationType
    target: str
    evidence_locator: str
    resolved: bool = True


@dataclass(frozen=True)
class ArchitectureKnowledgeModel:
    root: Path
    documents: tuple[ArchitectureDocument, ...]
    relationships: tuple[ArchitectureRelationship, ...]
    complete: bool
    warnings: tuple[str, ...]

    @classmethod
    def build(cls, index: RepositoryIndex) -> ArchitectureKnowledgeModel:
        """Build a bounded in-memory model from an existing file inventory."""
        documents: list[ArchitectureDocument] = []
        relationships: list[ArchitectureRelationship] = []
        warnings = list(index.warnings)
        complete = index.complete

        for metadata in index.files:
            if metadata.file_type != "markdown":
                continue

            candidate_type = _document_type(metadata.path, metadata.category)
            if candidate_type is None:
                continue

            try:
                text = _read_indexed_document(index, metadata.path)
            except (OSError, UnicodeError, ValueError) as error:
                complete = False
                warnings.append(f"{metadata.path}: cannot read document: {error}")
                continue

            lines = text.splitlines()
            headings = tuple(
                (line_number, match.group(2).strip())
                for line_number, line in enumerate(lines, start=1)
                if (match := _HEADING.match(line)) is not None
            )
            title = next(
                (heading for _, heading in headings if heading),
                PurePosixPath(metadata.path).stem.replace("_", " "),
            )
            phase_sources = _document_phases(
                metadata.path,
                headings,
                title,
                candidate_type,
            )
            area_sources = _document_areas(headings, title)
            document = ArchitectureDocument(
                path=metadata.path,
                document_type=candidate_type,
                title=title,
                phase_ids=tuple(dict.fromkeys(phase for phase, _ in phase_sources)),
                architecture_areas=tuple(dict.fromkeys(area for area, _ in area_sources)),
                headings=tuple(heading for _, heading in headings),
            )
            documents.append(document)

            for phase_id, locator in phase_sources:
                relationships.append(
                    ArchitectureRelationship(
                        source_path=metadata.path,
                        relation_type=ArchitectureRelationType.BELONGS_TO_PHASE,
                        target=phase_id,
                        evidence_locator=locator,
                    )
                )
            for area, locator in area_sources:
                relationships.append(
                    ArchitectureRelationship(
                        source_path=metadata.path,
                        relation_type=ArchitectureRelationType.DESCRIBES_AREA,
                        target=area,
                        evidence_locator=locator,
                    )
                )

            relationships.extend(
                _document_links(metadata.path, text)
            )

        documents.sort(key=lambda item: item.path.casefold())
        relationships.sort(
            key=lambda item: (
                item.source_path.casefold(),
                item.relation_type.value,
                item.target.casefold(),
                item.evidence_locator,
            )
        )
        known_paths = {document.path.casefold() for document in documents}
        resolved_relationships = tuple(
            ArchitectureRelationship(
                source_path=relation.source_path,
                relation_type=relation.relation_type,
                target=relation.target,
                evidence_locator=relation.evidence_locator,
                resolved=relation.target.casefold() in known_paths,
            )
            if relation.relation_type is ArchitectureRelationType.REFERENCES
            else relation
            for relation in relationships
        )
        unresolved_count = sum(
            1 for relation in resolved_relationships
            if relation.relation_type is ArchitectureRelationType.REFERENCES
            and not relation.resolved
        )
        if unresolved_count:
            warnings.append(f"{unresolved_count} local document reference(s) unresolved")

        return cls(
            root=index.root,
            documents=tuple(documents),
            relationships=resolved_relationships,
            complete=complete,
            warnings=tuple(warnings),
        )

    @classmethod
    def from_repository(
        cls,
        root: str | Path,
        limits: IndexLimits | None = None,
    ) -> ArchitectureKnowledgeModel:
        """Discover and describe architecture documents in one repository."""
        return cls.build(RepositoryIndex.build(root, limits))

    def document_type(self, path: str) -> ArchitectureDocumentType | None:
        document = self._find_document(path)
        return document.document_type if document is not None else None

    def phases_for_document(self, path: str) -> tuple[str, ...]:
        document = self._find_document(path)
        return document.phase_ids if document is not None else ()

    def documents_for_phase(self, phase_id: str) -> tuple[ArchitectureDocument, ...]:
        normalized = _normalize_phase_id(phase_id)
        return tuple(
            document
            for document in self.documents
            if normalized in document.phase_ids
        )

    def documents_for_area(self, area: str) -> tuple[ArchitectureDocument, ...]:
        normalized = _normalize_area(area)
        return tuple(
            document
            for document in self.documents
            if normalized in document.architecture_areas
        )

    def _find_document(self, path: str) -> ArchitectureDocument | None:
        normalized = path.replace("\\", "/").casefold()
        return next(
            (document for document in self.documents if document.path.casefold() == normalized),
            None,
        )


_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_PHASE = re.compile(r"\bphase\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE)
_FILE_PHASE = re.compile(r"^phase(\d+(?:_\d+)*)", re.IGNORECASE)
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_AREA_ALIASES = {
    "architecture awareness": ("architecture awareness", "architecture-awareness"),
    "automated testing": ("automated testing", "test execution"),
    "browser automation": ("browser automation", "browser backend"),
    "capability evolution": ("capability evolution",),
    "configuration": ("configuration", "config"),
    "execution": ("execution", "task execution"),
    "home assistant": ("home assistant",),
    "memory": ("memory",),
    "proposal generation": ("proposal generation",),
    "repository awareness": ("repository awareness",),
    "sandbox validation": ("sandbox validation", "sandbox"),
    "verification": ("verification",),
    "vision": ("vision system", "vision integration"),
    "workspace automation": ("workspace automation", "workspace backend"),
}


def _document_type(
    path: str,
    category: RepositoryCategory,
) -> ArchitectureDocumentType | None:
    normalized = PurePosixPath(path).stem.casefold().replace("-", "_")
    tokens = set(re.split(r"[^a-z0-9]+", normalized))
    if "vision" in tokens:
        return ArchitectureDocumentType.VISION
    if "roadmap" in tokens or category is RepositoryCategory.ROADMAP:
        return ArchitectureDocumentType.ROADMAP
    if tokens & {"decision", "decisions"} or category is RepositoryCategory.DECISION:
        return ArchitectureDocumentType.DECISION
    if "implementation_plan" in normalized or "implementationplan" in normalized:
        return ArchitectureDocumentType.IMPLEMENTATION_PLAN
    if category is RepositoryCategory.ARCHITECTURE:
        return ArchitectureDocumentType.ARCHITECTURE
    return None


def _document_phases(
    path: str,
    headings: tuple[tuple[int, str], ...],
    title: str,
    document_type: ArchitectureDocumentType,
) -> list[tuple[str, str]]:
    title_match = _PHASE.search(title)
    if title_match is not None:
        phase_id = title_match.group(1)
        title_line = next(
            (line_number for line_number, heading in headings if heading == title),
            None,
        )
        return [(phase_id, f"line:{title_line}" if title_line else "title")]

    filename_match = _FILE_PHASE.match(PurePosixPath(path).stem)
    if filename_match is not None:
        phase_id = filename_match.group(1).replace("_", ".")
        return [(phase_id, "filename")]

    if document_type is not ArchitectureDocumentType.ROADMAP:
        return []

    results = []
    for line_number, heading in headings:
        match = _PHASE.search(heading)
        if match is not None:
            results.append((match.group(1), f"line:{line_number}"))
    return results


def _document_areas(
    headings: tuple[tuple[int, str], ...],
    title: str,
) -> list[tuple[str, str]]:
    sources = [(title, next(
        (f"line:{line_number}" for line_number, heading in headings if heading == title),
        "title",
    ))]
    sources.extend((heading, f"line:{line_number}") for line_number, heading in headings)
    matches: list[tuple[str, str]] = []
    for area, aliases in _AREA_ALIASES.items():
        for text, locator in sources:
            normalized_text = text.casefold().replace("-", " ")
            if any(alias.replace("-", " ") in normalized_text for alias in aliases):
                matches.append((area, locator))
                break
    return matches


def _document_links(
    source_path: str,
    text: str,
) -> list[ArchitectureRelationship]:
    path_lines = text.splitlines()
    relationships: list[ArchitectureRelationship] = []
    for line_number, line in enumerate(path_lines, start=1):
        for match in _MARKDOWN_LINK.finditer(line):
            destination = match.group(1).strip().strip("<>")
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            decoded_path = unquote(parsed.path).replace("\\", "/")
            if decoded_path.startswith("/"):
                continue
            source_parent = PurePosixPath(source_path).parent
            target = PurePosixPath(source_parent, decoded_path)
            normalized_parts: list[str] = []
            escapes_root = False
            for part in target.parts:
                if part in {"", "."}:
                    continue
                if part == "..":
                    if not normalized_parts:
                        escapes_root = True
                        break
                    normalized_parts.pop()
                else:
                    normalized_parts.append(part)
            if escapes_root:
                continue
            target_path = PurePosixPath(*normalized_parts).as_posix()
            relationships.append(
                ArchitectureRelationship(
                    source_path=source_path,
                    relation_type=ArchitectureRelationType.REFERENCES,
                    target=target_path,
                    evidence_locator=f"line:{line_number}",
                    resolved=False,
                )
            )
    return relationships


def _read_indexed_document(index: RepositoryIndex, relative_path: str) -> str:
    root = index.root.resolve(strict=True)
    candidate = root.joinpath(*PurePosixPath(relative_path).parts)
    current = root
    for part in PurePosixPath(relative_path).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("document path contains a symbolic link")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("document path resolves outside repository root") from error

    with resolved.open("rb") as document_file:
        content = document_file.read(index.limits.max_file_bytes + 1)
    if len(content) > index.limits.max_file_bytes:
        raise ValueError("document exceeds indexed size limit")
    return content.decode("utf-8")


def _normalize_phase_id(phase_id: str) -> str:
    normalized = phase_id.strip().casefold()
    if normalized.startswith("phase "):
        normalized = normalized[6:].strip()
    return normalized.replace("_", ".")


def _normalize_area(area: str) -> str:
    normalized = " ".join(area.casefold().replace("-", " ").split())
    return normalized
