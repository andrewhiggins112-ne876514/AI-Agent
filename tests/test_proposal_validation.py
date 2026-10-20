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
from scripts.proposal_validation import (
    ProposalValidationResult,
    ValidationCategory,
    ValidationDecision,
    validate_proposal,
)


def reviewable_enhancement() -> Proposal:
    evidence = (
        EvidenceItem(
            evidence_id="implementation",
            evidence_class=EvidenceClass.IMPLEMENTATION,
            claim="The existing behavior is described by supplied evidence.",
            source_path="src/example.py",
            locator="Example.run",
            provenance=EvidenceProvenance.COMMITTED,
            freshness=EvidenceFreshness.CURRENT,
            applicability=Applicability.APPLICABLE,
        ),
        EvidenceItem(
            evidence_id="user-need",
            evidence_class=EvidenceClass.USER_REPORT,
            claim="The user reported a limitation in the workflow.",
            limitations=("Explicit user report without a repository source.",),
            provenance=EvidenceProvenance.COMMITTED,
            freshness=EvidenceFreshness.CURRENT,
            applicability=Applicability.APPLICABLE,
        ),
    )
    confidence = ConfidenceAssessment(
        level=ConfidenceLevel.MODERATE,
        explanation="The supplied evidence supports review with bounded limitations.",
        dimensions=tuple(
            ConfidenceDimensionAssessment(
                dimension=dimension,
                rationale=f"Evidence assessment for {dimension.value}.",
            )
            for dimension in ConfidenceDimension
        ),
    )
    return Proposal(
        proposal_id="proposal-1",
        schema_version="1",
        proposal_type=ProposalType.ENHANCEMENT,
        status=ProposalStatus.READY_FOR_REVIEW,
        created_at=datetime.now(timezone.utc),
        scope="The example workflow.",
        problem="The workflow has a reported limitation.",
        confidence=confidence,
        evidence=evidence,
        rationale="Existing behavior and the reported need support human review.",
        options=(
            ProposalOption(
                option_id="defer",
                title="Do nothing / defer",
                description="Leave existing behavior unchanged.",
                expected_effect="No change.",
                tradeoffs="The reported limitation remains.",
                effort="None",
                reversibility="No change is made.",
                defer=True,
            ),
            ProposalOption(
                option_id="review",
                title="Review an enhancement",
                description="Consider options in a separate human review.",
                expected_effect="Could address the reported limitation.",
                tradeoffs="Requires separately approved planning.",
                effort="Unknown",
                reversibility="To be assessed.",
            ),
        ),
        recommendation=ProposalRecommendation(
            option_id="review",
            rationale="The user-reported need merits consideration.",
            assumptions=("The report accurately reflects the user's need.",),
            conditions_that_change_recommendation=(
                "Contradictory evidence changes the assessment.",
            ),
        ),
    )


class ProposalValidationTests(unittest.TestCase):
    def test_accept_means_review_eligibility_only_and_preserves_proposal(self):
        proposal = reviewable_enhancement()

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.ACCEPT)
        self.assertTrue(result.eligible_for_review)
        self.assertIs(result.proposal, proposal)
        self.assertEqual(result.reasons, ())

    def test_unknown_or_stale_supporting_freshness_needs_evidence(self):
        for freshness in (EvidenceFreshness.UNKNOWN, EvidenceFreshness.STALE):
            with self.subTest(freshness=freshness):
                proposal = reviewable_enhancement()
                evidence = (
                    replace(proposal.evidence[0], freshness=freshness),
                    proposal.evidence[1],
                )
                proposal = replace(proposal, evidence=evidence)

                result = validate_proposal(proposal)

                self.assertEqual(result.decision, ValidationDecision.NEEDS_EVIDENCE)
                self.assertFalse(result.eligible_for_review)
                self.assertIn(
                    "supporting_evidence_not_current",
                    {reason.code for reason in result.reasons},
                )

    def test_needs_evidence_status_is_not_review_eligible(self):
        proposal = replace(
            reviewable_enhancement(),
            status=ProposalStatus.NEEDS_EVIDENCE,
            unresolved_questions=("Confirm current behavior.",),
        )

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.NEEDS_EVIDENCE)
        self.assertIn(
            "proposal_not_ready_for_review",
            {reason.code for reason in result.reasons},
        )

    def test_insufficient_confidence_needs_evidence(self):
        proposal = reviewable_enhancement()
        proposal = replace(
            proposal,
            confidence=replace(
                proposal.confidence,
                level=ConfidenceLevel.INSUFFICIENT,
            ),
        )

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.NEEDS_EVIDENCE)
        self.assertIn(
            "insufficient_confidence",
            {reason.code for reason in result.reasons},
        )

    def test_high_confidence_needs_verifiable_counter_evidence(self):
        proposal = reviewable_enhancement()
        proposal = replace(
            proposal,
            confidence=replace(
                proposal.confidence,
                level=ConfidenceLevel.HIGH,
            ),
        )

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.NEEDS_EVIDENCE)
        self.assertIn(
            "high_confidence_not_verifiable",
            {reason.code for reason in result.reasons},
        )

    def test_incomplete_recommendation_context_needs_evidence(self):
        proposal = reviewable_enhancement()
        proposal = replace(
            proposal,
            recommendation=replace(
                proposal.recommendation,
                conditions_that_change_recommendation=(),
            ),
        )

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.NEEDS_EVIDENCE)
        self.assertIn(
            "incomplete_recommendation_context",
            {reason.code for reason in result.reasons},
        )

    def test_invalid_structure_is_rejected_with_model_errors(self):
        proposal = replace(reviewable_enhancement(), options=())

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.REJECT)
        self.assertIn(
            ValidationCategory.STRUCTURE,
            {reason.category for reason in result.reasons},
        )
        self.assertIs(result.proposal, proposal)

    def test_only_enhancement_proposals_are_supported(self):
        proposal = reviewable_enhancement()
        proposal = replace(
            proposal,
            proposal_type=ProposalType.ARCHITECTURE,
            evidence=proposal.evidence + (
                EvidenceItem(
                    evidence_id="design",
                    evidence_class=EvidenceClass.PROPOSED_DESIGN,
                    claim="A proposed architecture describes a target.",
                    source_path="docs/design.md",
                    locator="## Target",
                    provenance=EvidenceProvenance.COMMITTED,
                    freshness=EvidenceFreshness.CURRENT,
                    applicability=Applicability.PROPOSED,
                ),
            ),
        )

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.REJECT)
        self.assertIn(
            "unsupported_proposal_type",
            {reason.code for reason in result.reasons},
        )

    def test_conflicting_evidence_needs_evidence(self):
        proposal = reviewable_enhancement()
        conflict = EvidenceItem(
            evidence_id="conflict",
            evidence_class=EvidenceClass.PROPOSED_DESIGN,
            claim="A supplied design conflicts with another applicable source.",
            source_path="docs/design.md",
            locator="## Conflict",
            provenance=EvidenceProvenance.COMMITTED,
            freshness=EvidenceFreshness.CURRENT,
            applicability=Applicability.CONFLICTING,
        )
        proposal = replace(proposal, evidence=proposal.evidence + (conflict,))

        result = validate_proposal(proposal)

        self.assertEqual(result.decision, ValidationDecision.NEEDS_EVIDENCE)
        self.assertIn(
            "conflicting_evidence",
            {reason.code for reason in result.reasons},
        )

    def test_invalid_non_proposal_input_is_rejected(self):
        result = validate_proposal(object())

        self.assertEqual(result.decision, ValidationDecision.REJECT)
        self.assertIsNone(result.proposal)
        self.assertEqual(len(result.reasons), 1)

    def test_result_and_input_proposal_are_immutable(self):
        proposal = reviewable_enhancement()
        result = validate_proposal(proposal)

        with self.assertRaises(FrozenInstanceError):
            result.decision = ValidationDecision.REJECT
        with self.assertRaises(FrozenInstanceError):
            proposal.problem = "changed"

    def test_result_is_a_validation_record_with_reason_categories(self):
        result = validate_proposal(
            replace(reviewable_enhancement(), rationale="")
        )

        self.assertIsInstance(result, ProposalValidationResult)
        self.assertEqual(result.decision, ValidationDecision.REJECT)
        self.assertTrue(
            all(isinstance(reason.category, ValidationCategory) for reason in result.reasons)
        )


if __name__ == "__main__":
    unittest.main()
