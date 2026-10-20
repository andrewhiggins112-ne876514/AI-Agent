"""Construct in-memory Enhancement proposals from explicitly supplied evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os

from scripts.architecture_awareness import ArchitectureKnowledgeModel
from scripts.proposal_model import (
    Applicability,
    ConfidenceAssessment,
    ConfidenceDimension,
    ConfidenceDimensionAssessment,
    ConfidenceLevel,
    EvidenceClass,
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    Proposal,
    ProposalOption,
    ProposalRecommendation,
    ProposalStatus,
    ProposalType,
    TestRecommendation,
)
from scripts.repository_awareness import RepositoryIndex


@dataclass(frozen=True)
class ProposalEvidenceInput:
    """Explicit candidate content and evidence used to construct a proposal."""

    proposal_id: str
    scope: str
    problem: str
    evidence: tuple[EvidenceItem, ...]
    rationale: str = ""
    options: tuple[ProposalOption, ...] = ()
    recommendation: ProposalRecommendation | None = None
    affected_areas: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    testing_strategy: tuple[TestRecommendation, ...] = ()


class ProposalConstructionError(ValueError):
    """Raised when supplied construction inputs are structurally invalid."""

    def __init__(self, errors: tuple[str, ...]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def construct_enhancement_proposal(
    repository_index: RepositoryIndex,
    architecture_model: ArchitectureKnowledgeModel,
    proposal_input: ProposalEvidenceInput,
) -> Proposal:
    """Build and validate a Proposal using only supplied in-memory values.

    Missing or uncertain evidence produces a valid NEEDS_EVIDENCE proposal.
    Invalid inputs raise ProposalConstructionError. No repository I/O,
    recommendation generation, or downstream action is performed.
    """
    errors = _validate_inputs(repository_index, architecture_model, proposal_input)
    if errors:
        raise ProposalConstructionError(errors)

    evidence = proposal_input.evidence
    indexed_paths = {
        metadata.path.replace("\\", "/").casefold()
        for metadata in repository_index.files
    }
    implementation_items = tuple(
        item for item in evidence
        if item.evidence_class is EvidenceClass.IMPLEMENTATION
    )
    user_reports = tuple(
        item for item in evidence
        if item.evidence_class is EvidenceClass.USER_REPORT
    )

    missing_evidence: list[str] = []
    if not implementation_items:
        missing_evidence.append(
            "Supply explicitly located implementation evidence for existing behavior."
        )
    if not user_reports:
        missing_evidence.append("Supply an explicit user report describing the need.")
    if not proposal_input.options:
        missing_evidence.append(
            "Supply human-authored proposal options, including do nothing/defer."
        )
    elif len(proposal_input.options) < 2 or not any(
        option.defer for option in proposal_input.options
    ):
        missing_evidence.append(
            "Supply at least two human-authored options, including do nothing/defer."
        )
    if proposal_input.recommendation is None:
        missing_evidence.append(
            "Supply an advisory recommendation explicitly; construction does not "
            "generate recommendations."
        )

    limitations: list[str] = []
    blocking_limitations: list[str] = []
    if not repository_index.complete:
        limitation = "Repository index is incomplete."
        limitations.append(limitation)
        blocking_limitations.append(limitation)
    if repository_index.excluded_count:
        limitations.append(
            f"Repository index excluded {repository_index.excluded_count} item(s)."
        )
    if repository_index.warnings:
        warnings = [
            f"Repository index warning: {warning}"
            for warning in repository_index.warnings
        ]
        limitations.extend(warnings)
        blocking_limitations.extend(warnings)
    if not architecture_model.complete:
        limitation = "Architecture awareness model is incomplete."
        limitations.append(limitation)
        blocking_limitations.append(limitation)
    if architecture_model.warnings:
        warnings = [
            f"Architecture awareness warning: {warning}"
            for warning in architecture_model.warnings
        ]
        limitations.extend(warnings)
        blocking_limitations.extend(warnings)

    for item in implementation_items:
        if (
            item.source_path is None
            or item.source_path.replace("\\", "/").casefold() not in indexed_paths
        ):
            missing_evidence.append(
                f"Implementation evidence {item.evidence_id!r} is not in the "
                "supplied repository index."
            )
        if item.applicability is not Applicability.APPLICABLE:
            missing_evidence.append(
                f"Implementation evidence {item.evidence_id!r} is not explicitly "
                "applicable to the candidate."
            )

    for item in evidence:
        if item.freshness is EvidenceFreshness.STALE:
            missing_evidence.append(
                f"Evidence {item.evidence_id!r} is stale and requires refresh."
            )
        if item.applicability in {
            Applicability.NOT_APPLICABLE,
            Applicability.CONFLICTING,
        }:
            missing_evidence.append(
                f"Evidence {item.evidence_id!r} is not applicable or is conflicting."
            )

    unresolved_questions = tuple(dict.fromkeys(
        (
            *proposal_input.unresolved_questions,
            *missing_evidence,
            *(
                f"Resolve awareness limitation before review: {limitation}"
                for limitation in blocking_limitations
            ),
        )
    ))
    ready = not missing_evidence and not blocking_limitations
    confidence = _assess_confidence(evidence, limitations, missing_evidence)
    status = ProposalStatus.READY_FOR_REVIEW if ready else ProposalStatus.NEEDS_EVIDENCE

    proposal = Proposal(
        proposal_id=proposal_input.proposal_id,
        schema_version="1",
        proposal_type=ProposalType.ENHANCEMENT,
        status=status,
        created_at=datetime.now(timezone.utc),
        scope=proposal_input.scope,
        problem=proposal_input.problem,
        confidence=confidence,
        evidence=evidence,
        rationale=proposal_input.rationale,
        options=proposal_input.options,
        recommendation=proposal_input.recommendation if ready else None,
        testing_strategy=proposal_input.testing_strategy,
        affected_areas=proposal_input.affected_areas,
        assumptions=tuple(dict.fromkeys(
            (*proposal_input.assumptions, *limitations)
        )),
        unresolved_questions=unresolved_questions,
    )

    validation_errors = proposal.validate()
    if validation_errors:
        raise ProposalConstructionError(validation_errors)
    return proposal


def _validate_inputs(
    repository_index: RepositoryIndex,
    architecture_model: ArchitectureKnowledgeModel,
    proposal_input: ProposalEvidenceInput,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(repository_index, RepositoryIndex):
        errors.append("repository_index must be a RepositoryIndex")
    if not isinstance(architecture_model, ArchitectureKnowledgeModel):
        errors.append("architecture_model must be an ArchitectureKnowledgeModel")
    if not isinstance(proposal_input, ProposalEvidenceInput):
        errors.append("proposal_input must be a ProposalEvidenceInput")
    if errors:
        return tuple(errors)

    if _normalized_root(repository_index.root) != _normalized_root(
        architecture_model.root
    ):
        errors.append("awareness inputs must refer to the same repository root")

    for name, value in (
        ("proposal_id", proposal_input.proposal_id),
        ("scope", proposal_input.scope),
        ("problem", proposal_input.problem),
    ):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} must be non-empty")

    tuple_values = (
        ("evidence", proposal_input.evidence),
        ("options", proposal_input.options),
        ("affected_areas", proposal_input.affected_areas),
        ("assumptions", proposal_input.assumptions),
        ("unresolved_questions", proposal_input.unresolved_questions),
        ("testing_strategy", proposal_input.testing_strategy),
    )
    for name, value in tuple_values:
        if not isinstance(value, tuple):
            errors.append(f"{name} must be an immutable tuple")

    if any(not isinstance(value, tuple) for _, value in tuple_values):
        return tuple(errors)

    for option in proposal_input.options:
        if not isinstance(option, ProposalOption):
            errors.append("options must contain ProposalOption values")
    if (
        proposal_input.recommendation is not None
        and not isinstance(proposal_input.recommendation, ProposalRecommendation)
    ):
        errors.append("recommendation must be a ProposalRecommendation or None")
    for test in proposal_input.testing_strategy:
        if not isinstance(test, TestRecommendation):
            errors.append("testing_strategy must contain TestRecommendation values")

    evidence_ids: set[str] = set()
    indexed_paths = {
        metadata.path.replace("\\", "/").casefold()
        for metadata in repository_index.files
    }
    for item in proposal_input.evidence:
        if not isinstance(item, EvidenceItem):
            errors.append("evidence entries must be EvidenceItem values")
            continue
        if not isinstance(item.evidence_id, str) or not item.evidence_id.strip():
            errors.append("evidence_id must be non-empty")
        elif item.evidence_id in evidence_ids:
            errors.append(f"duplicate evidence_id: {item.evidence_id}")
        evidence_ids.add(item.evidence_id)
        if not isinstance(item.evidence_class, EvidenceClass):
            errors.append(f"evidence {item.evidence_id!r} has an invalid class")
        if not isinstance(item.claim, str) or not item.claim.strip():
            errors.append(f"evidence {item.evidence_id!r} claim must be non-empty")
        if item.source_path is not None:
            if not isinstance(item.source_path, str) or not item.source_path.strip():
                errors.append(f"evidence {item.evidence_id!r} path is invalid")
            elif not _is_repository_relative(item.source_path):
                errors.append(
                    f"evidence {item.evidence_id!r} path must be repository-relative"
                )
            elif item.source_path.replace("\\", "/").casefold() not in indexed_paths:
                errors.append(
                    f"evidence {item.evidence_id!r} path is outside the supplied index"
                )
            if not isinstance(item.locator, str) or not item.locator.strip():
                errors.append(
                    f"evidence {item.evidence_id!r} with a path needs a locator"
                )
        else:
            if not isinstance(item.limitations, tuple):
                errors.append(
                    f"evidence {item.evidence_id!r} limitations must be a tuple"
                )
            elif not item.limitations or any(
                not isinstance(value, str) or not value.strip()
                for value in item.limitations
            ):
                errors.append(
                    f"evidence {item.evidence_id!r} without a path needs limitations"
                )
        if not isinstance(item.provenance, EvidenceProvenance):
            errors.append(f"evidence {item.evidence_id!r} has invalid provenance")
        if not isinstance(item.freshness, EvidenceFreshness):
            errors.append(f"evidence {item.evidence_id!r} has invalid freshness")
        if not isinstance(item.applicability, Applicability):
            errors.append(f"evidence {item.evidence_id!r} has invalid applicability")

    return tuple(errors)


def _assess_confidence(
    evidence: tuple[EvidenceItem, ...],
    limitations: list[str],
    missing_evidence: list[str],
) -> ConfidenceAssessment:
    if missing_evidence:
        level = ConfidenceLevel.INSUFFICIENT
    elif limitations or any(
        item.provenance is not EvidenceProvenance.COMMITTED
        or item.freshness is not EvidenceFreshness.CURRENT
        or item.applicability is not Applicability.APPLICABLE
        or bool(item.limitations)
        for item in evidence
    ):
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.MODERATE

    rationale = (
        "Confidence is qualitative and based only on explicitly supplied "
        "evidence metadata; source contents were not inspected."
    )
    dimensions = tuple(
        ConfidenceDimensionAssessment(
            dimension=dimension,
            rationale=_dimension_rationale(dimension, evidence, limitations),
        )
        for dimension in ConfidenceDimension
    )
    limiting_conditions = tuple(dict.fromkeys(
        (*limitations, *missing_evidence, "Evidence claims were not independently verified.")
    ))
    return ConfidenceAssessment(
        level=level,
        explanation=rationale,
        dimensions=dimensions,
        limiting_conditions=limiting_conditions,
    )


def _dimension_rationale(
    dimension: ConfidenceDimension,
    evidence: tuple[EvidenceItem, ...],
    limitations: list[str],
) -> str:
    if dimension is ConfidenceDimension.TRACEABILITY:
        located = sum(item.source_path is not None and bool(item.locator) for item in evidence)
        return f"{located} of {len(evidence)} supplied evidence item(s) have a path and locator."
    if dimension is ConfidenceDimension.DIRECTNESS:
        has_implementation = any(
            item.evidence_class is EvidenceClass.IMPLEMENTATION
            for item in evidence
        )
        return (
            "Implementation evidence was explicitly supplied but not inspected."
            if has_implementation
            else "No implementation evidence was supplied."
        )
    if dimension is ConfidenceDimension.APPLICABILITY:
        return "Applicability is taken from supplied evidence metadata, not inferred."
    if dimension is ConfidenceDimension.REPRODUCIBILITY:
        return "No behavior or test was executed by proposal construction."
    if dimension is ConfidenceDimension.COMPLETENESS:
        return (
            "Awareness inputs report complete scans."
            if not limitations
            else "Awareness inputs report limitations: " + "; ".join(limitations)
        )
    if dimension is ConfidenceDimension.FRESHNESS:
        return "Freshness is preserved from supplied evidence and is not inferred."
    return "Evidence independence cannot be established from supplied metadata alone."


def _normalized_root(root: object) -> str:
    return os.path.normcase(os.path.normpath(os.fspath(root)))


def _is_repository_relative(path: str) -> bool:
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    return (
        bool(normalized)
        and not normalized.startswith("/")
        and not any(part in {"", ".", ".."} for part in parts)
        and not parts[0].endswith(":")
    )
