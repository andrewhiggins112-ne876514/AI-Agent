"""In-memory human review boundary for validated Enhancement proposals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from scripts.proposal_model import Proposal, ProposalStatus, ProposalType
from scripts.proposal_validation import (
    ProposalValidationResult,
    ValidationDecision,
)


class ReviewState(str, Enum):
    DRAFT = "draft"
    NEEDS_EVIDENCE = "needs_evidence"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


class ReviewDisposition(str, Enum):
    ACCEPTED_FOR_PLANNING = "accepted_for_planning"
    REQUEST_EVIDENCE = "request_evidence"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ReviewActor(str, Enum):
    VALIDATOR = "validator"
    HUMAN = "human"


@dataclass(frozen=True)
class ReviewAuditEntry:
    event_id: str
    proposal_id: str
    event_type: str
    actor: ReviewActor
    validation_decision: ValidationDecision
    validation_reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...]
    occurred_at: datetime
    disposition: ReviewDisposition | None = None
    reviewed_scope: str | None = None
    reviewer_reference: str | None = None
    rationale: str | None = None
    evidence_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalReviewRecord:
    proposal: Proposal
    validation: ProposalValidationResult
    state: ReviewState
    audit_entries: tuple[ReviewAuditEntry, ...]
    disposition: ReviewDisposition | None = None
    reviewer_reference: str | None = None
    reviewed_at: datetime | None = None
    acknowledged_scope: str | None = None
    rationale: str | None = None
    evidence_questions: tuple[str, ...] = ()


class ReviewWorkflowError(ValueError):
    """Raised when a human disposition cannot be safely recorded."""


def begin_proposal_review(
    proposal: Proposal,
    validation: ProposalValidationResult,
) -> ProposalReviewRecord:
    """Create an in-memory eligibility record without changing its inputs."""
    if not isinstance(proposal, Proposal):
        raise TypeError("proposal must be a Proposal")
    if not isinstance(validation, ProposalValidationResult):
        raise TypeError("validation must be a ProposalValidationResult")

    reasons = tuple(reason.code for reason in validation.reasons)
    evidence_references = tuple(
        f"{item.evidence_id}:{item.source_path or 'user-supplied'}:"
        f"{item.locator or 'no-locator'}"
        for item in proposal.evidence
    )

    if validation.proposal is not proposal:
        state = ReviewState.REJECTED
        reason_codes = (*reasons, "proposal_validation_reference_mismatch")
    elif validation.decision is ValidationDecision.REJECT:
        state = ReviewState.REJECTED
        reason_codes = reasons
    elif proposal.proposal_type is not ProposalType.ENHANCEMENT:
        state = ReviewState.REJECTED
        reason_codes = (*reasons, "unsupported_proposal_type")
    elif validation.decision is ValidationDecision.NEEDS_EVIDENCE:
        state = (
            ReviewState.DRAFT
            if proposal.status is ProposalStatus.DRAFT
            else ReviewState.NEEDS_EVIDENCE
        )
        reason_codes = reasons
    elif (
        proposal.status is ProposalStatus.READY_FOR_REVIEW
        and validation.eligible_for_review
    ):
        state = ReviewState.READY_FOR_REVIEW
        reason_codes = reasons
    else:
        state = ReviewState.REJECTED
        reason_codes = (*reasons, "inconsistent_review_eligibility")

    audit_entry = ReviewAuditEntry(
        event_id=str(uuid4()),
        proposal_id=proposal.proposal_id,
        event_type="quality_gate",
        actor=ReviewActor.VALIDATOR,
        validation_decision=validation.decision,
        validation_reason_codes=tuple(dict.fromkeys(reason_codes)),
        evidence_references=evidence_references,
        occurred_at=datetime.now(timezone.utc),
    )
    return ProposalReviewRecord(
        proposal=proposal,
        validation=validation,
        state=state,
        audit_entries=(audit_entry,),
    )


def record_human_disposition(
    record: ProposalReviewRecord,
    disposition: ReviewDisposition,
    acknowledged_scope: str,
    *,
    reviewer_reference: str | None = None,
    rationale: str | None = None,
    evidence_questions: tuple[str, ...] = (),
    reviewed_at: datetime | None = None,
) -> ProposalReviewRecord:
    """Return a new record for an explicit human decision; trigger no action."""
    if not isinstance(record, ProposalReviewRecord):
        raise TypeError("record must be a ProposalReviewRecord")
    if not isinstance(disposition, ReviewDisposition):
        raise TypeError("disposition must be a ReviewDisposition")
    if not isinstance(record.proposal, Proposal) or not isinstance(
        record.validation, ProposalValidationResult
    ):
        raise ReviewWorkflowError("review record has invalid proposal references")
    if record.state is not ReviewState.READY_FOR_REVIEW:
        raise ReviewWorkflowError("human disposition requires a ready proposal")
    if (
        record.proposal.proposal_type is not ProposalType.ENHANCEMENT
        or record.validation.proposal is not record.proposal
        or record.validation.decision is not ValidationDecision.ACCEPT
        or not record.validation.eligible_for_review
        or record.proposal.status is not ProposalStatus.READY_FOR_REVIEW
    ):
        raise ReviewWorkflowError("review eligibility is inconsistent")
    if not isinstance(acknowledged_scope, str) or (
        acknowledged_scope != record.proposal.scope
    ):
        raise ReviewWorkflowError("acknowledged_scope must match proposal scope")
    if reviewer_reference is not None and (
        not isinstance(reviewer_reference, str) or not reviewer_reference.strip()
    ):
        raise ReviewWorkflowError("reviewer_reference cannot be blank")
    if rationale is not None and (
        not isinstance(rationale, str) or not rationale.strip()
    ):
        raise ReviewWorkflowError("rationale cannot be blank")
    if not isinstance(evidence_questions, tuple) or any(
        not isinstance(question, str) or not question.strip()
        for question in evidence_questions
    ):
        raise ReviewWorkflowError("evidence_questions must be non-empty text values")
    if disposition is ReviewDisposition.REQUEST_EVIDENCE and not evidence_questions:
        raise ReviewWorkflowError(
            "request_evidence disposition requires at least one question"
        )

    event_time = reviewed_at or datetime.now(timezone.utc)
    if (
        not isinstance(event_time, datetime)
        or event_time.tzinfo is None
        or event_time.utcoffset() is None
    ):
        raise ReviewWorkflowError("reviewed_at must be timezone-aware")

    state = (
        ReviewState.REJECTED
        if disposition is ReviewDisposition.REJECTED
        else (
            ReviewState.NEEDS_EVIDENCE
            if disposition is ReviewDisposition.REQUEST_EVIDENCE
            else ReviewState.REVIEWED
        )
    )
    audit_entry = ReviewAuditEntry(
        event_id=str(uuid4()),
        proposal_id=record.proposal.proposal_id,
        event_type="human_disposition",
        actor=ReviewActor.HUMAN,
        validation_decision=record.validation.decision,
        validation_reason_codes=tuple(
            reason.code for reason in record.validation.reasons
        ),
        evidence_references=tuple(
            f"{item.evidence_id}:{item.source_path or 'user-supplied'}:"
            f"{item.locator or 'no-locator'}"
            for item in record.proposal.evidence
        ),
        occurred_at=event_time,
        disposition=disposition,
        reviewed_scope=acknowledged_scope,
        reviewer_reference=reviewer_reference,
        rationale=rationale,
        evidence_questions=evidence_questions,
    )
    return ProposalReviewRecord(
        proposal=record.proposal,
        validation=record.validation,
        state=state,
        audit_entries=(*record.audit_entries, audit_entry),
        disposition=disposition,
        reviewer_reference=reviewer_reference,
        reviewed_at=event_time,
        acknowledged_scope=acknowledged_scope,
        rationale=rationale,
        evidence_questions=evidence_questions,
    )
