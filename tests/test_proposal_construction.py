from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.architecture_awareness import ArchitectureKnowledgeModel
from scripts.proposal_construction import (
    ProposalConstructionError,
    ProposalEvidenceInput,
    construct_enhancement_proposal,
)
from scripts.proposal_model import (
    Applicability,
    ConfidenceDimension,
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
from scripts.repository_awareness import (
    Importance,
    IndexLimits,
    RepositoryCategory,
    RepositoryFileMetadata,
    RepositoryIndex,
)


def awareness_inputs(root: str = "C:/example/repo"):
    repository_root = Path(root)
    index = RepositoryIndex(
        root=repository_root,
        files=(
            RepositoryFileMetadata(
                path="src/example.py",
                file_type="python",
                category=RepositoryCategory.SOURCE,
                importance=Importance.NORMAL,
            ),
            RepositoryFileMetadata(
                path="docs/need.md",
                file_type="markdown",
                category=RepositoryCategory.DOCUMENTATION,
                importance=Importance.NORMAL,
            ),
        ),
        indexed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        complete=True,
        excluded_count=0,
        warnings=(),
        limits=IndexLimits(),
    )
    architecture = ArchitectureKnowledgeModel(
        root=repository_root,
        documents=(),
        relationships=(),
        complete=True,
        warnings=(),
    )
    return index, architecture


def valid_input(**overrides):
    implementation = EvidenceItem(
        evidence_id="implementation",
        evidence_class=EvidenceClass.IMPLEMENTATION,
        claim="The supplied implementation evidence describes existing behavior.",
        source_path="src/example.py",
        locator="Example.run",
        provenance=EvidenceProvenance.COMMITTED,
        freshness=EvidenceFreshness.CURRENT,
        applicability=Applicability.APPLICABLE,
    )
    user_report = EvidenceItem(
        evidence_id="user-need",
        evidence_class=EvidenceClass.USER_REPORT,
        claim="The user reported a limitation in the workflow.",
        source_path="docs/need.md",
        locator="## User need",
        provenance=EvidenceProvenance.COMMITTED,
        freshness=EvidenceFreshness.CURRENT,
        applicability=Applicability.APPLICABLE,
    )
    values = {
        "proposal_id": "enhancement-1",
        "scope": "The example workflow.",
        "problem": "The current workflow has a reported limitation.",
        "evidence": (implementation, user_report),
        "rationale": "The supplied evidence describes existing behavior and a user need.",
        "options": (
            ProposalOption(
                option_id="defer",
                title="Do nothing / defer",
                description="Leave the current behavior unchanged.",
                expected_effect="No behavior change.",
                tradeoffs="The reported limitation remains.",
                effort="None",
                reversibility="No change is made.",
                defer=True,
            ),
            ProposalOption(
                option_id="review",
                title="Review an improvement",
                description="Consider an improvement through a separate review.",
                expected_effect="Could address the reported limitation.",
                tradeoffs="Requires independent planning and approval.",
                effort="Unknown",
                reversibility="Assess separately.",
            ),
        ),
        "recommendation": ProposalRecommendation(
            option_id="review",
            rationale="The explicitly supplied user need merits human review.",
        ),
    }
    values.update(overrides)
    return ProposalEvidenceInput(**values)


class ProposalConstructionTests(unittest.TestCase):
    def test_constructs_valid_enhancement_from_explicit_inputs(self):
        index, architecture = awareness_inputs()

        proposal = construct_enhancement_proposal(
            index, architecture, valid_input()
        )

        self.assertIsInstance(proposal, Proposal)
        self.assertEqual(proposal.proposal_type, ProposalType.ENHANCEMENT)
        self.assertEqual(proposal.status, ProposalStatus.READY_FOR_REVIEW)
        self.assertEqual(proposal.validate(), ())
        self.assertEqual(
            {assessment.dimension for assessment in proposal.confidence.dimensions},
            set(ConfidenceDimension),
        )
        self.assertEqual(proposal.confidence.level, ConfidenceLevel.MODERATE)
        self.assertEqual(
            proposal.recommendation,
            valid_input().recommendation,
        )

    def test_missing_evidence_returns_valid_needs_evidence_proposal(self):
        index, architecture = awareness_inputs()
        supplied = valid_input(
            evidence=(),
            options=(),
            recommendation=None,
        )

        proposal = construct_enhancement_proposal(index, architecture, supplied)

        self.assertEqual(proposal.status, ProposalStatus.NEEDS_EVIDENCE)
        self.assertEqual(proposal.confidence.level, ConfidenceLevel.INSUFFICIENT)
        self.assertIsNone(proposal.recommendation)
        self.assertTrue(proposal.unresolved_questions)
        self.assertEqual(proposal.validate(), ())

    def test_construction_does_not_invent_recommendation_or_options(self):
        index, architecture = awareness_inputs()
        supplied = valid_input(options=(), recommendation=None)

        proposal = construct_enhancement_proposal(index, architecture, supplied)

        self.assertEqual(proposal.status, ProposalStatus.NEEDS_EVIDENCE)
        self.assertEqual(proposal.options, ())
        self.assertIsNone(proposal.recommendation)

    def test_rejects_mismatched_repository_roots(self):
        index, _ = awareness_inputs()
        _, architecture = awareness_inputs("C:/other/repo")

        with self.assertRaises(ProposalConstructionError) as raised:
            construct_enhancement_proposal(index, architecture, valid_input())

        self.assertIn(
            "awareness inputs must refer to the same repository root",
            raised.exception.errors,
        )

    def test_rejects_duplicate_evidence_ids(self):
        index, architecture = awareness_inputs()
        item = valid_input().evidence[0]

        with self.assertRaises(ProposalConstructionError) as raised:
            construct_enhancement_proposal(
                index,
                architecture,
                valid_input(evidence=(item, item)),
            )

        self.assertIn("duplicate evidence_id: implementation", raised.exception.errors)

    def test_rejects_evidence_paths_outside_the_supplied_index(self):
        index, architecture = awareness_inputs()
        evidence = list(valid_input().evidence)
        evidence[0] = EvidenceItem(
            evidence_id="implementation",
            evidence_class=EvidenceClass.IMPLEMENTATION,
            claim="The implementation path is not indexed.",
            source_path="src/not-indexed.py",
            locator="Example.run",
            provenance=EvidenceProvenance.COMMITTED,
            freshness=EvidenceFreshness.CURRENT,
            applicability=Applicability.APPLICABLE,
        )

        with self.assertRaises(ProposalConstructionError) as raised:
            construct_enhancement_proposal(
                index,
                architecture,
                valid_input(evidence=tuple(evidence)),
            )

        self.assertIn(
            "evidence 'implementation' path is outside the supplied index",
            raised.exception.errors,
        )

    def test_incomplete_awareness_is_disclosed_and_blocks_ready_status(self):
        index, architecture = awareness_inputs()
        index = RepositoryIndex(
            root=index.root,
            files=index.files,
            indexed_at=index.indexed_at,
            complete=False,
            excluded_count=0,
            warnings=("Scan limit reached.",),
            limits=index.limits,
        )
        architecture = ArchitectureKnowledgeModel(
            root=architecture.root,
            documents=architecture.documents,
            relationships=architecture.relationships,
            complete=False,
            warnings=("Architecture document could not be read.",),
        )

        proposal = construct_enhancement_proposal(
            index, architecture, valid_input()
        )

        self.assertEqual(proposal.status, ProposalStatus.NEEDS_EVIDENCE)
        self.assertIn(
            "Repository index is incomplete.",
            proposal.assumptions,
        )
        self.assertEqual(proposal.validate(), ())

    def test_unrelated_exclusions_are_disclosed_without_claiming_absence(self):
        index, architecture = awareness_inputs()
        index = RepositoryIndex(
            root=index.root,
            files=index.files,
            indexed_at=index.indexed_at,
            complete=True,
            excluded_count=3,
            warnings=(),
            limits=index.limits,
        )

        proposal = construct_enhancement_proposal(
            index, architecture, valid_input()
        )

        self.assertEqual(proposal.status, ProposalStatus.READY_FOR_REVIEW)
        self.assertIn("Repository index excluded 3 item(s).", proposal.assumptions)
        self.assertEqual(proposal.validate(), ())

    def test_stale_evidence_produces_needs_evidence(self):
        index, architecture = awareness_inputs()
        evidence = list(valid_input().evidence)
        evidence[1] = EvidenceItem(
            evidence_id="user-need",
            evidence_class=EvidenceClass.USER_REPORT,
            claim="The user reported a limitation in the workflow.",
            source_path="docs/need.md",
            locator="## User need",
            provenance=EvidenceProvenance.COMMITTED,
            freshness=EvidenceFreshness.STALE,
            applicability=Applicability.APPLICABLE,
        )

        proposal = construct_enhancement_proposal(
            index,
            architecture,
            valid_input(evidence=tuple(evidence)),
        )

        self.assertEqual(proposal.status, ProposalStatus.NEEDS_EVIDENCE)
        self.assertTrue(
            any("is stale" in question for question in proposal.unresolved_questions)
        )
        self.assertEqual(proposal.validate(), ())

    def test_builder_methods_are_not_called_and_proposal_is_immutable(self):
        index, architecture = awareness_inputs()
        with (
            patch.object(RepositoryIndex, "build", side_effect=AssertionError),
            patch.object(ArchitectureKnowledgeModel, "build", side_effect=AssertionError),
            patch.object(
                ArchitectureKnowledgeModel,
                "from_repository",
                side_effect=AssertionError,
            ),
        ):
            proposal = construct_enhancement_proposal(
                index, architecture, valid_input()
            )

        with self.assertRaises(FrozenInstanceError):
            proposal.problem = "changed"


if __name__ == "__main__":
    unittest.main()
