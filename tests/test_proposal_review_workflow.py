from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import unittest

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
)
from scripts.proposal_review_workflow import (
    ProposalReviewRecord,
    ReviewActor,
    ReviewDisposition,
    ReviewState,
    ReviewWorkflowError,
    begin_proposal_review,
    record_human_disposition,
)
from scripts.proposal_validation import (
    ProposalValidationResult,
    ValidationDecision,
    ValidationReason,
    ValidationCategory,
    validate_proposal,
)


def ready_proposal() -> Proposal:
    return Proposal(
        proposal_id="proposal-review-1",
        schema_version="1",
        proposal_type=ProposalType.ENHANCEMENT,
        status=ProposalStatus.READY_FOR_REVIEW,
        created_at=datetime.now(timezone.utc),
        scope="The documented example workflow.",
        problem="The workflow has a user-reported limitation.",
        confidence=ConfidenceAssessment(
            level=ConfidenceLevel.MODERATE,
            explanation="Evidence supports review with bounded uncertainty.",
            dimensions=tuple(
                ConfidenceDimensionAssessment(
                    dimension=dimension,
                    rationale=f"Assessment for {dimension.value}.",
                )
                for dimension in ConfidenceDimension
            ),
        ),
        evidence=(
            EvidenceItem(
                evidence_id="implementation",
                evidence_class=EvidenceClass.IMPLEMENTATION,
                claim="Supplied evidence describes existing behavior.",
                source_path="src/example.py",
                locator="Example.run",
                provenance=EvidenceProvenance.COMMITTED,
                freshness=EvidenceFreshness.CURRENT,
                applicability=Applicability.APPLICABLE,
            ),
            EvidenceItem(
                evidence_id="need",
                evidence_class=EvidenceClass.USER_REPORT,
                claim="The user reported a workflow limitation.",
                limitations=("User report; no repository source.",),
                provenance=EvidenceProvenance.COMMITTED,
                freshness=EvidenceFreshness.CURRENT,
                applicability=Applicability.APPLICABLE,
            ),
        ),
        rationale="The stated need and existing behavior merit consideration.",
        options=(
            ProposalOption(
                option_id="defer",
                title="Do nothing / defer",
                description="Leave behavior unchanged.",
                expected_effect="No change.",
                tradeoffs="The reported limitation remains.",
                effort="None",
                reversibility="No action is taken.",
                defer=True,
            ),
            ProposalOption(
                option_id="consider",
                title="Consider improvement",
                description="Consider alternatives in planning.",
                expected_effect="Could address the reported need.",
                tradeoffs="Requires separate approvals.",
                effort="Unknown",
                reversibility="Assess separately.",
            ),
        ),
        recommendation=ProposalRecommendation(
            option_id="consider",
            rationale="The explicit user-need report supports consideration.",
            assumptions=("The report reflects a current user need.",),
            conditions_that_change_recommendation=(
                "Contradictory evidence changes the assessment.",
            ),
        ),
    )


def needs_evidence_proposal() -> Proposal:
    proposal = ready_proposal()
    evidence = (
        replace(proposal.evidence[0], freshness=EvidenceFreshness.STALE),
        proposal.evidence[1],
    )
    return replace(proposal, evidence=evidence)


class ProposalReviewWorkflowTests(unittest.TestCase):
    def test_accept_enters_ready_for_review_with_validator_audit_entry(self):
        proposal = ready_proposal()
        validation = validate_proposal(proposal)

        record = begin_proposal_review(proposal, validation)

        self.assertEqual(record.state, ReviewState.READY_FOR_REVIEW)
        self.assertIs(record.proposal, proposal)
        self.assertIs(record.validation, validation)
        self.assertIsNone(record.disposition)
        self.assertIsNone(record.reviewed_at)
        self.assertEqual(len(record.audit_entries), 1)
        self.assertEqual(record.audit_entries[0].actor, ReviewActor.VALIDATOR)
        self.assertEqual(record.audit_entries[0].event_type, "quality_gate")
        self.assertEqual(
            record.audit_entries[0].validation_decision,
            ValidationDecision.ACCEPT,
        )

    def test_needs_evidence_is_blocked_and_preserves_reasons(self):
        proposal = needs_evidence_proposal()
        validation = validate_proposal(proposal)

        record = begin_proposal_review(proposal, validation)

        self.assertEqual(validation.decision, ValidationDecision.NEEDS_EVIDENCE)
        self.assertEqual(record.state, ReviewState.NEEDS_EVIDENCE)
        self.assertIsNone(record.disposition)
        self.assertIn(
            "supporting_evidence_not_current",
            record.audit_entries[0].validation_reason_codes,
        )

    def test_draft_is_distinct_and_blocked(self):
        proposal = replace(ready_proposal(), status=ProposalStatus.DRAFT)
        validation = validate_proposal(proposal)

        record = begin_proposal_review(proposal, validation)

        self.assertEqual(record.state, ReviewState.DRAFT)
        self.assertEqual(validation.decision, ValidationDecision.NEEDS_EVIDENCE)

    def test_accept_with_non_ready_status_fails_closed(self):
        proposal = replace(
            ready_proposal(),
            status=ProposalStatus.NEEDS_EVIDENCE,
        )
        validation = ProposalValidationResult(
            decision=ValidationDecision.ACCEPT,
            reasons=(),
            proposal=proposal,
        )

        record = begin_proposal_review(proposal, validation)

        self.assertEqual(record.state, ReviewState.REJECTED)
        self.assertIn(
            "inconsistent_review_eligibility",
            record.audit_entries[0].validation_reason_codes,
        )

    def test_reject_outcome_enters_rejected_without_human_disposition(self):
        proposal = ready_proposal()
        validation = ProposalValidationResult(
            decision=ValidationDecision.REJECT,
            reasons=(
                ValidationReason(
                    code="unsafe_input",
                    category=ValidationCategory.EVIDENCE,
                    message="Input cannot be safely reviewed.",
                ),
            ),
            proposal=proposal,
        )

        record = begin_proposal_review(proposal, validation)

        self.assertEqual(record.state, ReviewState.REJECTED)
        self.assertIsNone(record.disposition)
        self.assertEqual(record.audit_entries[0].actor, ReviewActor.VALIDATOR)

    def test_mismatched_proposal_reference_fails_closed(self):
        proposal = ready_proposal()
        other = ready_proposal()
        validation = validate_proposal(other)

        record = begin_proposal_review(proposal, validation)

        self.assertEqual(record.state, ReviewState.REJECTED)
        self.assertIn(
            "proposal_validation_reference_mismatch",
            record.audit_entries[0].validation_reason_codes,
        )

    def test_human_dispositions_are_recorded_without_changing_proposal(self):
        for disposition, expected_state, questions in (
            (ReviewDisposition.ACCEPTED_FOR_PLANNING, ReviewState.REVIEWED, ()),
            (ReviewDisposition.REQUEST_EVIDENCE, ReviewState.NEEDS_EVIDENCE, ("Confirm scope.",)),
            (ReviewDisposition.REJECTED, ReviewState.REJECTED, ()),
            (ReviewDisposition.DEFERRED, ReviewState.REVIEWED, ()),
        ):
            with self.subTest(disposition=disposition):
                proposal = ready_proposal()
                validation = validate_proposal(proposal)
                initial = begin_proposal_review(proposal, validation)
                reviewed = record_human_disposition(
                    initial,
                    disposition,
                    proposal.scope,
                    reviewer_reference="reviewer-1",
                    rationale="Human disposition recorded.",
                    evidence_questions=questions,
                )

                self.assertEqual(reviewed.state, expected_state)
                self.assertEqual(reviewed.disposition, disposition)
                self.assertIs(reviewed.proposal, proposal)
                self.assertEqual(proposal.status, ProposalStatus.READY_FOR_REVIEW)
                self.assertEqual(len(initial.audit_entries), 1)
                self.assertEqual(len(reviewed.audit_entries), 2)
                self.assertEqual(reviewed.audit_entries[1].actor, ReviewActor.HUMAN)
                self.assertEqual(
                    reviewed.audit_entries[1].disposition,
                    disposition,
                )
                self.assertEqual(
                    reviewed.audit_entries[1].reviewed_scope,
                    proposal.scope,
                )
                self.assertIsNotNone(reviewed.reviewed_at.tzinfo)

    def test_request_evidence_requires_questions(self):
        proposal = ready_proposal()
        record = begin_proposal_review(proposal, validate_proposal(proposal))

        with self.assertRaises(ReviewWorkflowError):
            record_human_disposition(
                record,
                ReviewDisposition.REQUEST_EVIDENCE,
                record.proposal.scope,
            )

    def test_disposition_requires_exact_scope_and_review_eligibility(self):
        proposal = ready_proposal()
        stale_proposal = needs_evidence_proposal()
        blocked = begin_proposal_review(
            proposal,
            validate_proposal(stale_proposal),
        )

        with self.assertRaises(ReviewWorkflowError):
            record_human_disposition(
                blocked,
                ReviewDisposition.DEFERRED,
                proposal.scope,
            )

        ready = begin_proposal_review(proposal, validate_proposal(proposal))
        with self.assertRaises(ReviewWorkflowError):
            record_human_disposition(
                ready,
                ReviewDisposition.DEFERRED,
                "different scope",
            )

    def test_review_records_and_audit_entries_are_immutable(self):
        proposal = ready_proposal()
        record = begin_proposal_review(proposal, validate_proposal(proposal))

        with self.assertRaises(FrozenInstanceError):
            record.state = ReviewState.REJECTED
        with self.assertRaises(FrozenInstanceError):
            record.audit_entries[0].event_type = "human_disposition"

        reviewed = record_human_disposition(
            record,
            ReviewDisposition.DEFERRED,
            proposal.scope,
        )
        self.assertIsInstance(reviewed, ProposalReviewRecord)
        self.assertEqual(record.state, ReviewState.READY_FOR_REVIEW)
        self.assertEqual(len(record.audit_entries), 1)
        self.assertEqual(len(reviewed.audit_entries), 2)

    def test_human_disposition_cannot_be_recorded_twice(self):
        proposal = ready_proposal()
        record = begin_proposal_review(proposal, validate_proposal(proposal))
        reviewed = record_human_disposition(
            record,
            ReviewDisposition.DEFERRED,
            proposal.scope,
        )

        with self.assertRaises(ReviewWorkflowError):
            record_human_disposition(
                reviewed,
                ReviewDisposition.ACCEPTED_FOR_PLANNING,
                proposal.scope,
            )


if __name__ == "__main__":
    unittest.main()
