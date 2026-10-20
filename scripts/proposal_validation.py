"""Read-only quality gates for in-memory Enhancement proposals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scripts.proposal_model import (
    Applicability,
    ConfidenceDimension,
    ConfidenceLevel,
    EvidenceClass,
    EvidenceFreshness,
    EvidenceProvenance,
    Proposal,
    ProposalStatus,
    ProposalType,
)


class ValidationDecision(str, Enum):
    ACCEPT = "accept"
    NEEDS_EVIDENCE = "needs_evidence"
    REJECT = "reject"


class ValidationCategory(str, Enum):
    STRUCTURE = "structure"
    EVIDENCE = "evidence"
    CONFIDENCE = "confidence"
    COMPLETENESS = "completeness"
    ELIGIBILITY = "eligibility"


@dataclass(frozen=True)
class ValidationReason:
    code: str
    category: ValidationCategory
    message: str


@dataclass(frozen=True)
class ProposalValidationResult:
    decision: ValidationDecision
    reasons: tuple[ValidationReason, ...]
    proposal: Proposal | None

    @property
    def eligible_for_review(self) -> bool:
        return self.decision is ValidationDecision.ACCEPT


_READINESS_ERRORS = {
    "insufficient confidence cannot be ready for review",
    "high confidence requires current, verified, non-conflicting evidence",
}


def validate_proposal(proposal: object) -> ProposalValidationResult:
    """Validate an existing Enhancement proposal without changing it.

    ACCEPT means eligible for human review only. Structural defects and
    unsupported proposal types are rejected; unresolved evidence or quality
    gates return NEEDS_EVIDENCE.
    """
    if not isinstance(proposal, Proposal):
        return ProposalValidationResult(
            decision=ValidationDecision.REJECT,
            reasons=(
                ValidationReason(
                    code="invalid_proposal_type",
                    category=ValidationCategory.STRUCTURE,
                    message="Input must be a Proposal record.",
                ),
            ),
            proposal=None,
        )

    structural_errors = proposal.validate()
    hard_errors = tuple(
        error for error in structural_errors if error not in _READINESS_ERRORS
    )
    if hard_errors:
        return ProposalValidationResult(
            decision=ValidationDecision.REJECT,
            reasons=(
                ValidationReason(
                    code="structural_validation_failed",
                    category=ValidationCategory.STRUCTURE,
                    message=(
                        "Proposal.validate() reported "
                        f"{len(hard_errors)} structural validation error(s)."
                    ),
                ),
            ),
            proposal=proposal,
        )

    reasons: list[ValidationReason] = []
    for error in structural_errors:
        reasons.append(
            ValidationReason(
                code="confidence_readiness_gate",
                category=ValidationCategory.CONFIDENCE,
                message=error,
            )
        )

    if proposal.proposal_type is not ProposalType.ENHANCEMENT:
        reasons.append(
            ValidationReason(
                code="unsupported_proposal_type",
                category=ValidationCategory.ELIGIBILITY,
                message=(
                    "This validation slice supports Enhancement proposals only."
                ),
            )
        )
        return _result(ValidationDecision.REJECT, reasons, proposal)

    evidence_by_class = {
        evidence_class: tuple(
            item
            for item in proposal.evidence
            if item.evidence_class is evidence_class
        )
        for evidence_class in EvidenceClass
    }
    implementation = evidence_by_class[EvidenceClass.IMPLEMENTATION]
    user_reports = evidence_by_class[EvidenceClass.USER_REPORT]

    if not implementation:
        reasons.append(
            ValidationReason(
                code="missing_implementation_evidence",
                category=ValidationCategory.EVIDENCE,
                message="Enhancement review requires evidence of existing behavior.",
            )
        )
    if not user_reports:
        reasons.append(
            ValidationReason(
                code="missing_user_need",
                category=ValidationCategory.EVIDENCE,
                message="Enhancement review requires an explicit user-need report.",
            )
        )

    for evidence in (*implementation, *user_reports):
        if evidence.freshness is not EvidenceFreshness.CURRENT:
            reasons.append(
                ValidationReason(
                    code="supporting_evidence_not_current",
                    category=ValidationCategory.EVIDENCE,
                    message=(
                        "Supporting implementation or user-need evidence is "
                        "stale or has unknown freshness."
                    ),
                )
            )
        if evidence.applicability is not Applicability.APPLICABLE:
            reasons.append(
                ValidationReason(
                    code="supporting_evidence_applicability_unresolved",
                    category=ValidationCategory.EVIDENCE,
                    message=(
                        "Supporting implementation or user-need evidence is "
                        "not explicitly applicable."
                    ),
                )
            )
        if evidence.provenance in {
            EvidenceProvenance.UNKNOWN,
            EvidenceProvenance.UNVERIFIED,
            EvidenceProvenance.MODIFIED,
        } and proposal.confidence.level is ConfidenceLevel.HIGH:
            reasons.append(
                ValidationReason(
                    code="high_confidence_provenance_mismatch",
                    category=ValidationCategory.CONFIDENCE,
                    message=(
                        "High confidence requires verified, committed "
                        "supporting evidence."
                    ),
                )
            )

    if any(
        item.applicability is Applicability.CONFLICTING
        for item in proposal.evidence
    ):
        reasons.append(
            ValidationReason(
                code="conflicting_evidence",
                category=ValidationCategory.EVIDENCE,
                message="Evidence contains an unresolved applicability conflict.",
            )
        )

    if proposal.confidence.level is ConfidenceLevel.INSUFFICIENT:
        reasons.append(
            ValidationReason(
                code="insufficient_confidence",
                category=ValidationCategory.CONFIDENCE,
                message=(
                    "Insufficient confidence cannot pass the review quality gate."
                ),
            )
        )
    else:
        dimension_ids = {
            assessment.dimension
            for assessment in proposal.confidence.dimensions
            if hasattr(assessment, "dimension")
        }
        if dimension_ids != set(ConfidenceDimension):
            reasons.append(
                ValidationReason(
                    code="incomplete_confidence_dimensions",
                    category=ValidationCategory.CONFIDENCE,
                    message=(
                        "Confidence assessment must explain all seven dimensions."
                    ),
                )
            )
        if proposal.confidence.level is ConfidenceLevel.HIGH:
            reasons.append(
                ValidationReason(
                    code="high_confidence_not_verifiable",
                    category=ValidationCategory.CONFIDENCE,
                    message=(
                        "The current proposal model cannot independently verify "
                        "that material counter-evidence was checked."
                    ),
                )
            )

    if not isinstance(proposal.rationale, str) or not proposal.rationale.strip():
        reasons.append(
            ValidationReason(
                code="missing_proposal_rationale",
                category=ValidationCategory.COMPLETENESS,
                message="A reviewable proposal requires a rationale.",
            )
        )
    if len(proposal.options) < 2 or not any(
        getattr(option, "defer", False) for option in proposal.options
    ):
        reasons.append(
            ValidationReason(
                code="incomplete_options",
                category=ValidationCategory.COMPLETENESS,
                message=(
                    "A reviewable proposal requires at least two options, "
                    "including do nothing/defer."
                ),
            )
        )
    if proposal.recommendation is None:
        reasons.append(
            ValidationReason(
                code="missing_advisory_recommendation",
                category=ValidationCategory.COMPLETENESS,
                message="A reviewable proposal requires an advisory recommendation.",
            )
        )
    elif (
        not proposal.recommendation.assumptions
        or not proposal.recommendation.conditions_that_change_recommendation
    ):
        reasons.append(
            ValidationReason(
                code="incomplete_recommendation_context",
                category=ValidationCategory.COMPLETENESS,
                message=(
                    "The advisory recommendation requires assumptions and "
                    "conditions that could change it."
                ),
            )
        )
    if any(
        test.execution_status.value != "not_run"
        for test in proposal.testing_strategy
    ):
        reasons.append(
            ValidationReason(
                code="test_execution_status_invalid",
                category=ValidationCategory.COMPLETENESS,
                message="Test recommendations must remain marked not run.",
            )
        )

    if proposal.status is not ProposalStatus.READY_FOR_REVIEW:
        reasons.append(
            ValidationReason(
                code="proposal_not_ready_for_review",
                category=ValidationCategory.ELIGIBILITY,
                message=(
                    "Proposal status is not READY_FOR_REVIEW; human review "
                    "eligibility has not been established."
                ),
            )
        )

    if reasons:
        return _result(ValidationDecision.NEEDS_EVIDENCE, reasons, proposal)
    return ProposalValidationResult(
        decision=ValidationDecision.ACCEPT,
        reasons=(),
        proposal=proposal,
    )


def _result(
    decision: ValidationDecision,
    reasons: list[ValidationReason],
    proposal: Proposal,
) -> ProposalValidationResult:
    return ProposalValidationResult(
        decision=decision,
        reasons=tuple(reasons),
        proposal=proposal,
    )
