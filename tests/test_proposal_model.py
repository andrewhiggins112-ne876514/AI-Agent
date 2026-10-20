from dataclasses import FrozenInstanceError
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
    TestExecutionStatus,
    TestKind,
    TestRecommendation,
)


def confidence(level=ConfidenceLevel.MODERATE):
    return ConfidenceAssessment(
        level=level,
        explanation="The available evidence supports a candidate with limitations.",
        dimensions=tuple(
            ConfidenceDimensionAssessment(
                dimension=dimension,
                rationale=f"Assessment for {dimension.value}.",
            )
            for dimension in ConfidenceDimension
        ),
        limiting_conditions=("Repository provenance is not independently verified.",),
    )


def implementation_evidence(evidence_id="implementation"):
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_class=EvidenceClass.IMPLEMENTATION,
        claim="The existing behavior is described by inspected implementation evidence.",
        source_path="src/example.py",
        locator="Example.run",
        provenance=EvidenceProvenance.COMMITTED,
        freshness=EvidenceFreshness.CURRENT,
        applicability=Applicability.APPLICABLE,
    )


def cited_evidence(evidence_id, evidence_class, applicability=Applicability.APPLICABLE):
    suffix = evidence_id.replace("-", "_")
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_class=evidence_class,
        claim=f"Evidence for {evidence_id}.",
        source_path=f"docs/{suffix}.md",
        locator=f"## {evidence_id}",
        provenance=EvidenceProvenance.COMMITTED,
        freshness=EvidenceFreshness.CURRENT,
        applicability=applicability,
    )


def ready_enhancement(**overrides):
    evidence = (
        implementation_evidence(),
        EvidenceItem(
            evidence_id="user-need",
            evidence_class=EvidenceClass.USER_REPORT,
            claim="The user reported a limitation in the existing workflow.",
            limitations=("User-provided report; no repository locator.",),
        ),
    )
    values = {
        "proposal_id": "proposal-1",
        "schema_version": "1",
        "proposal_type": ProposalType.ENHANCEMENT,
        "status": ProposalStatus.READY_FOR_REVIEW,
        "created_at": datetime.now(timezone.utc),
        "scope": "The existing example workflow.",
        "problem": "The existing workflow has a reported usability limitation.",
        "confidence": confidence(),
        "evidence": evidence,
        "rationale": "The candidate is supported by existing behavior and a user report.",
        "options": (
            ProposalOption(
                option_id="defer",
                title="Do nothing / defer",
                description="Leave current behavior unchanged.",
                expected_effect="No behavior change.",
                tradeoffs="The reported limitation remains.",
                effort="None",
                reversibility="Fully reversible because no change is made.",
                defer=True,
            ),
            ProposalOption(
                option_id="consider",
                title="Consider an improvement",
                description="Review an improvement option with a human.",
                expected_effect="Could address the reported limitation.",
                tradeoffs="Requires separate planning and authorization.",
                effort="Unknown",
                reversibility="To be assessed during planning.",
            ),
        ),
        "recommendation": ProposalRecommendation(
            option_id="consider",
            rationale="The user-reported need merits human review.",
            conditions_that_change_recommendation=("Further evidence contradicts the report.",),
        ),
    }
    values.update(overrides)
    return Proposal(**values)


class ProposalModelTests(unittest.TestCase):
    def test_supports_the_five_phase_52_proposal_types(self):
        self.assertEqual(
            {proposal_type.value for proposal_type in ProposalType},
            {"bug_fix", "gap", "enhancement", "refactoring", "architecture"},
        )

    def test_validates_a_structurally_complete_enhancement_proposal(self):
        proposal = ready_enhancement()

        self.assertEqual(proposal.validate(), ())

    def test_all_supported_proposal_types_validate_with_required_evidence(self):
        cases = (
            (
                ProposalType.BUG_FIX,
                (
                    implementation_evidence(),
                    cited_evidence("test-run", EvidenceClass.TEST_RUN),
                    cited_evidence("test-definition", EvidenceClass.TEST_DEFINITION),
                ),
                None,
            ),
            (
                ProposalType.GAP,
                (
                    implementation_evidence(),
                    cited_evidence("decision", EvidenceClass.APPROVED_DECISION),
                    cited_evidence("test-definition", EvidenceClass.TEST_DEFINITION),
                ),
                None,
            ),
            (
                ProposalType.ENHANCEMENT,
                (
                    implementation_evidence(),
                    EvidenceItem(
                        evidence_id="user-need",
                        evidence_class=EvidenceClass.USER_REPORT,
                        claim="A user described a need.",
                        limitations=("User report has no repository source.",),
                    ),
                ),
                None,
            ),
            (
                ProposalType.REFACTORING,
                (
                    implementation_evidence(),
                    cited_evidence("regression-test", EvidenceClass.TEST_DEFINITION),
                ),
                "Preserve documented external behavior.",
            ),
            (
                ProposalType.ARCHITECTURE,
                (
                    implementation_evidence(),
                    cited_evidence("design", EvidenceClass.PROPOSED_DESIGN),
                ),
                None,
            ),
        )

        for proposal_type, evidence, behavior_preservation in cases:
            with self.subTest(proposal_type=proposal_type):
                proposal = ready_enhancement(
                    proposal_type=proposal_type,
                    evidence=evidence,
                    behavior_preservation=behavior_preservation,
                )

                self.assertEqual(proposal.validate(), ())

    def test_proposal_and_nested_records_are_immutable(self):
        proposal = ready_enhancement()

        with self.assertRaises(FrozenInstanceError):
            proposal.problem = "changed"
        with self.assertRaises(FrozenInstanceError):
            proposal.evidence[0].claim = "changed"

    def test_needs_evidence_requires_open_questions(self):
        proposal = ready_enhancement(
            status=ProposalStatus.NEEDS_EVIDENCE,
            unresolved_questions=(),
        )

        self.assertIn(
            "needs_evidence proposals must list unresolved questions",
            proposal.validate(),
        )

    def test_ready_proposal_requires_evidence_options_and_recommendation(self):
        proposal = ready_enhancement(
            evidence=(),
            options=(),
            recommendation=None,
        )

        errors = proposal.validate()
        self.assertIn("ready_for_review proposals need evidence", errors)
        self.assertIn("ready_for_review proposals need at least two options", errors)
        self.assertIn("ready_for_review proposals need an advisory recommendation", errors)

    def test_ready_proposal_requires_all_qualitative_dimensions(self):
        assessment = ConfidenceAssessment(
            level=ConfidenceLevel.MODERATE,
            explanation="Evidence is partial.",
            dimensions=(
                ConfidenceDimensionAssessment(
                    ConfidenceDimension.TRACEABILITY,
                    "The source can be located.",
                ),
            ),
        )
        proposal = ready_enhancement(confidence=assessment)

        self.assertIn(
            "ready_for_review confidence needs all seven dimensions",
            proposal.validate(),
        )

    def test_insufficient_confidence_cannot_be_ready_for_review(self):
        proposal = ready_enhancement(confidence=confidence(ConfidenceLevel.INSUFFICIENT))

        self.assertIn(
            "insufficient confidence cannot be ready for review",
            proposal.validate(),
        )

    def test_high_confidence_is_capped_by_unknown_or_stale_evidence(self):
        proposal = ready_enhancement(
            confidence=confidence(ConfidenceLevel.HIGH),
        )

        self.assertIn(
            "high confidence requires current, verified, non-conflicting evidence",
            proposal.validate(),
        )

    def test_bug_fix_requires_implementation_and_relevant_test_evidence(self):
        proposal = ready_enhancement(
            proposal_type=ProposalType.BUG_FIX,
            evidence=(
                EvidenceItem(
                    evidence_id="report",
                    evidence_class=EvidenceClass.USER_REPORT,
                    claim="The user reports unexpected behavior.",
                    limitations=("User report is not a reproduction.",),
                ),
            ),
        )

        errors = proposal.validate()
        self.assertIn("bug fix proposals need implementation evidence", errors)
        self.assertIn(
            "bug fix proposals need reproducible test-run evidence",
            errors,
        )
        self.assertIn("bug fix proposals need an applicable expectation", errors)

    def test_gap_requires_an_applicable_approved_decision(self):
        proposal = ready_enhancement(
            proposal_type=ProposalType.GAP,
            evidence=(
                implementation_evidence(),
                EvidenceItem(
                    evidence_id="proposed",
                    evidence_class=EvidenceClass.PROPOSED_DESIGN,
                    claim="A design proposes a future capability.",
                    source_path="DESIGN.md",
                    locator="## Future capability",
                    provenance=EvidenceProvenance.COMMITTED,
                    freshness=EvidenceFreshness.CURRENT,
                    applicability=Applicability.PROPOSED,
                ),
                EvidenceItem(
                    evidence_id="test",
                    evidence_class=EvidenceClass.TEST_DEFINITION,
                    claim="A test defines relevant expected behavior.",
                    source_path="tests/test_example.py",
                    locator="test_expected_behavior",
                    provenance=EvidenceProvenance.COMMITTED,
                    freshness=EvidenceFreshness.CURRENT,
                    applicability=Applicability.APPLICABLE,
                ),
            ),
        )

        self.assertIn(
            "gap proposals need an applicable approved decision",
            proposal.validate(),
        )

    def test_evidence_references_must_be_repository_relative_and_located(self):
        proposal = ready_enhancement(
            evidence=(
                EvidenceItem(
                    evidence_id="bad-path",
                    evidence_class=EvidenceClass.IMPLEMENTATION,
                    claim="A claim with an invalid source path.",
                    source_path="../outside.py",
                    locator="line 1",
                ),
                EvidenceItem(
                    evidence_id="user-need",
                    evidence_class=EvidenceClass.USER_REPORT,
                    claim="The user reported a limitation.",
                    limitations=("No repository source.",),
                ),
            ),
        )

        self.assertIn(
            "evidence bad-path path must be repository-relative",
            proposal.validate(),
        )

    def test_recommendations_for_tests_are_never_marked_as_executed(self):
        test_plan = TestRecommendation(
            test_id="regression",
            kind=TestKind.REGRESSION,
            objective="Check behavior remains unchanged.",
            expected_result="The documented behavior is preserved.",
            execution_status="passed",
        )
        proposal = ready_enhancement(testing_strategy=(test_plan,))

        self.assertIn(
            "test recommendation regression has invalid execution status",
            proposal.validate(),
        )
        self.assertIn(
            "test recommendation regression must remain not_run",
            proposal.validate(),
        )

    def test_model_records_a_source_locator_without_reading_the_repository(self):
        item = implementation_evidence()
        proposal = ready_enhancement(
            status=ProposalStatus.DRAFT,
            evidence=(
                EvidenceItem(
                    evidence_id=item.evidence_id,
                    evidence_class=item.evidence_class,
                    claim=item.claim,
                    source_path="not-present.py",
                    locator=item.locator,
                    provenance=item.provenance,
                    freshness=item.freshness,
                    applicability=item.applicability,
                ),
            ),
            options=(),
            recommendation=None,
        )

        self.assertEqual(proposal.evidence[0].source_path, "not-present.py")
        self.assertEqual(proposal.validate(), ())


if __name__ == "__main__":
    unittest.main()
