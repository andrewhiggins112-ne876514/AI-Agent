"""Immutable, in-memory records for representing reviewed engineering proposals.

This module performs no repository I/O and does not generate proposals,
patches, code, commands, or actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath


class ProposalType(str, Enum):
    BUG_FIX = "bug_fix"
    GAP = "gap"
    ENHANCEMENT = "enhancement"
    REFACTORING = "refactoring"
    ARCHITECTURE = "architecture"


class ProposalStatus(str, Enum):
    NEEDS_EVIDENCE = "needs_evidence"
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"


class EvidenceClass(str, Enum):
    IMPLEMENTATION = "implementation"
    TEST_DEFINITION = "test_definition"
    TEST_RUN = "test_run"
    APPROVED_DECISION = "approved_decision"
    PROPOSED_DESIGN = "proposed_design"
    ROADMAP_STATEMENT = "roadmap_statement"
    USER_REPORT = "user_report"
    SIGNAL = "signal"
    INFERENCE = "inference"


class EvidenceProvenance(str, Enum):
    COMMITTED = "committed"
    MODIFIED = "modified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class EvidenceFreshness(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class Applicability(str, Enum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    PROPOSED = "proposed"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class ConfidenceDimension(str, Enum):
    TRACEABILITY = "traceability"
    DIRECTNESS = "directness"
    APPLICABILITY = "applicability"
    REPRODUCIBILITY = "reproducibility"
    COMPLETENESS = "completeness"
    FRESHNESS = "freshness"
    INDEPENDENCE = "independence"


class ProposalRiskCategory(str, Enum):
    SAFETY = "safety"
    SECURITY = "security"
    PRIVACY = "privacy"
    COMPATIBILITY = "compatibility"
    RELIABILITY = "reliability"
    ACCESSIBILITY = "accessibility"
    OPERATIONS = "operations"
    OTHER = "other"


class TestKind(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    MANUAL = "manual"


class TestExecutionStatus(str, Enum):
    NOT_RUN = "not_run"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    evidence_class: EvidenceClass
    claim: str
    source_path: str | None = None
    locator: str | None = None
    provenance: EvidenceProvenance = EvidenceProvenance.UNKNOWN
    freshness: EvidenceFreshness = EvidenceFreshness.UNKNOWN
    applicability: Applicability = Applicability.UNKNOWN
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfidenceDimensionAssessment:
    dimension: ConfidenceDimension
    rationale: str


@dataclass(frozen=True)
class ConfidenceAssessment:
    level: ConfidenceLevel
    explanation: str
    dimensions: tuple[ConfidenceDimensionAssessment, ...] = ()
    limiting_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalOption:
    option_id: str
    title: str
    description: str
    expected_effect: str
    tradeoffs: str
    effort: str
    reversibility: str
    evidence_ids: tuple[str, ...] = ()
    defer: bool = False


@dataclass(frozen=True)
class ProposalRecommendation:
    option_id: str
    rationale: str
    assumptions: tuple[str, ...] = ()
    conditions_that_change_recommendation: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposalRisk:
    risk_id: str
    category: ProposalRiskCategory
    description: str
    evidence_ids: tuple[str, ...] = ()
    mitigation_or_open_question: str = ""


@dataclass(frozen=True)
class TestRecommendation:
    test_id: str
    kind: TestKind
    objective: str
    expected_result: str
    side_effect_notes: str = ""
    approval_required: bool = True
    evidence_ids: tuple[str, ...] = ()
    execution_status: TestExecutionStatus = TestExecutionStatus.NOT_RUN


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    schema_version: str
    proposal_type: ProposalType
    status: ProposalStatus
    created_at: datetime
    scope: str
    problem: str
    confidence: ConfidenceAssessment
    evidence: tuple[EvidenceItem, ...] = ()
    repository_snapshot: str | None = None
    secondary_classifications: tuple[ProposalType, ...] = ()
    rationale: str = ""
    options: tuple[ProposalOption, ...] = ()
    recommendation: ProposalRecommendation | None = None
    risks: tuple[ProposalRisk, ...] = ()
    testing_strategy: tuple[TestRecommendation, ...] = ()
    affected_areas: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    behavior_preservation: str | None = None

    def validate(self) -> tuple[str, ...]:
        """Return structural and status-specific validation errors.

        Validation checks the representation only. It cannot establish that
        claims are true, evidence is genuinely applicable, or a proposal is
        approved.
        """
        errors: list[str] = []

        if not isinstance(self.confidence, ConfidenceAssessment):
            errors.append("confidence must be a ConfidenceAssessment")
            return tuple(errors)

        required_text = {
            "proposal_id": self.proposal_id,
            "schema_version": self.schema_version,
            "scope": self.scope,
            "problem": self.problem,
            "confidence explanation": self.confidence.explanation,
        }
        for field_name, value in required_text.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must be non-empty")

        if not isinstance(self.created_at, datetime):
            errors.append("created_at must be a datetime")
        elif self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            errors.append("created_at must include a timezone")

        tuple_fields = (
            ("evidence", self.evidence),
            ("secondary_classifications", self.secondary_classifications),
            ("options", self.options),
            ("risks", self.risks),
            ("testing_strategy", self.testing_strategy),
            ("affected_areas", self.affected_areas),
            ("assumptions", self.assumptions),
            ("unresolved_questions", self.unresolved_questions),
            ("dependencies", self.dependencies),
            ("confidence dimensions", self.confidence.dimensions),
            ("confidence limiting conditions", self.confidence.limiting_conditions),
        )
        for field_name, value in tuple_fields:
            if not isinstance(value, tuple):
                errors.append(f"{field_name} must be an immutable tuple")
        if any(not isinstance(value, tuple) for _, value in tuple_fields):
            return tuple(errors)

        if not isinstance(self.proposal_type, ProposalType):
            errors.append("proposal_type is not supported")
        if not isinstance(self.status, ProposalStatus):
            errors.append("status is invalid")
        if not isinstance(self.confidence.level, ConfidenceLevel):
            errors.append("confidence level is invalid")
        if any(not isinstance(item, ProposalType) for item in self.secondary_classifications):
            errors.append("secondary classifications must be supported proposal types")
        if self.proposal_type in self.secondary_classifications:
            errors.append("primary proposal type cannot also be a secondary classification")
        if any(
            not isinstance(area, str) or not area.strip()
            for area in self.affected_areas
        ):
            errors.append("affected areas must be non-empty descriptive labels")

        evidence_by_id: dict[str, EvidenceItem] = {}
        for item in self.evidence:
            if not isinstance(item, EvidenceItem):
                errors.append("evidence entries must be EvidenceItem values")
                continue
            if not isinstance(item.evidence_id, str) or not item.evidence_id.strip():
                errors.append("evidence_id must be non-empty")
            elif item.evidence_id in evidence_by_id:
                errors.append(f"duplicate evidence_id: {item.evidence_id}")
            else:
                evidence_by_id[item.evidence_id] = item
            if not isinstance(item.claim, str) or not item.claim.strip():
                errors.append(f"evidence {item.evidence_id} must describe its claim")
            if not isinstance(item.evidence_class, EvidenceClass):
                errors.append(f"evidence {item.evidence_id} has an invalid class")
            if item.source_path is not None and (
                not isinstance(item.source_path, str)
                or not _is_repository_relative(item.source_path)
            ):
                errors.append(
                    f"evidence {item.evidence_id} path must be repository-relative"
                )
            if item.locator is not None and (
                not isinstance(item.locator, str) or not item.locator.strip()
            ):
                errors.append(f"evidence {item.evidence_id} locator cannot be blank")
            if item.source_path is not None and item.locator is None:
                errors.append(
                    f"evidence {item.evidence_id} with a source path needs a locator"
                )
            if not isinstance(item.provenance, EvidenceProvenance):
                errors.append(f"evidence {item.evidence_id} has invalid provenance")
            if not isinstance(item.freshness, EvidenceFreshness):
                errors.append(f"evidence {item.evidence_id} has invalid freshness")
            if not isinstance(item.applicability, Applicability):
                errors.append(f"evidence {item.evidence_id} has invalid applicability")
            if not isinstance(item.limitations, tuple):
                errors.append(f"evidence {item.evidence_id} limitations must be a tuple")
            elif item.source_path is None and not item.limitations:
                errors.append(
                    f"evidence {item.evidence_id} without a source needs a limitation"
                )
            elif any(
                not isinstance(limitation, str) or not limitation.strip()
                for limitation in item.limitations
            ):
                errors.append(
                    f"evidence {item.evidence_id} limitations must be non-empty text"
                )

        dimension_ids: set[ConfidenceDimension] = set()
        for item in self.confidence.dimensions:
            if not isinstance(item, ConfidenceDimensionAssessment):
                errors.append("confidence dimensions must be typed assessments")
                continue
            if not isinstance(item.dimension, ConfidenceDimension):
                errors.append("confidence dimension is invalid")
                continue
            if item.dimension in dimension_ids:
                errors.append(f"duplicate confidence dimension: {item.dimension}")
            dimension_ids.add(item.dimension)
            if not isinstance(item.rationale, str) or not item.rationale.strip():
                errors.append(f"confidence dimension {item.dimension} needs rationale")

        option_ids: set[str] = set()
        for option in self.options:
            if not isinstance(option, ProposalOption):
                errors.append("options must be ProposalOption values")
                continue
            option_text = (
                option.title,
                option.description,
                option.expected_effect,
                option.tradeoffs,
                option.effort,
                option.reversibility,
            )
            if any(not isinstance(value, str) or not value.strip() for value in option_text):
                errors.append(f"option {option.option_id} has empty required text")
            if (
                not isinstance(option.option_id, str)
                or not option.option_id.strip()
                or option.option_id in option_ids
            ):
                errors.append(f"option_id must be non-empty and unique: {option.option_id}")
            elif option.option_id:
                option_ids.add(option.option_id)
            if not isinstance(option.evidence_ids, tuple):
                errors.append(f"option {option.option_id} evidence_ids must be a tuple")
                continue
            for evidence_id in option.evidence_ids:
                if evidence_id not in evidence_by_id:
                    errors.append(
                        f"option {option.option_id} references unknown evidence {evidence_id}"
                    )

        if self.recommendation is not None:
            if not isinstance(self.recommendation, ProposalRecommendation):
                errors.append("recommendation must be a ProposalRecommendation")
            else:
                if (
                    not isinstance(self.recommendation.option_id, str)
                    or self.recommendation.option_id not in option_ids
                ):
                    errors.append("recommendation must reference an existing option")
                if (
                    not isinstance(self.recommendation.rationale, str)
                    or not self.recommendation.rationale.strip()
                ):
                    errors.append("recommendation rationale must be non-empty")
                if not isinstance(self.recommendation.assumptions, tuple):
                    errors.append("recommendation assumptions must be an immutable tuple")
                if not isinstance(
                    self.recommendation.conditions_that_change_recommendation,
                    tuple,
                ):
                    errors.append(
                        "recommendation conditions must be an immutable tuple"
                    )

        for risk in self.risks:
            if not isinstance(risk, ProposalRisk):
                errors.append("risks must be ProposalRisk values")
                continue
            if not isinstance(risk.risk_id, str) or not risk.risk_id.strip():
                errors.append("risk_id must be non-empty")
            if not isinstance(risk.category, ProposalRiskCategory):
                errors.append(f"risk {risk.risk_id} has an invalid category")
            if not isinstance(risk.description, str) or not risk.description.strip():
                errors.append(f"risk {risk.risk_id} needs a description")
            if not isinstance(risk.evidence_ids, tuple):
                errors.append(f"risk {risk.risk_id} evidence_ids must be a tuple")
                continue
            for evidence_id in risk.evidence_ids:
                if evidence_id not in evidence_by_id:
                    errors.append(
                        f"risk {risk.risk_id} references unknown evidence {evidence_id}"
                    )

        test_ids: set[str] = set()
        for test in self.testing_strategy:
            if not isinstance(test, TestRecommendation):
                errors.append("testing_strategy entries must be TestRecommendation values")
                continue
            if (
                not isinstance(test.test_id, str)
                or not test.test_id.strip()
                or test.test_id in test_ids
            ):
                errors.append(f"test_id must be non-empty and unique: {test.test_id}")
            elif test.test_id:
                test_ids.add(test.test_id)
            if not isinstance(test.kind, TestKind):
                errors.append(f"test recommendation {test.test_id} has an invalid kind")
            if (
                not isinstance(test.objective, str)
                or not test.objective.strip()
                or not isinstance(test.expected_result, str)
                or not test.expected_result.strip()
            ):
                errors.append(f"test recommendation {test.test_id} needs objective and result")
            if not isinstance(test.execution_status, TestExecutionStatus):
                errors.append(f"test recommendation {test.test_id} has invalid execution status")
            if test.execution_status is not TestExecutionStatus.NOT_RUN:
                errors.append(f"test recommendation {test.test_id} must remain not_run")
            if not isinstance(test.evidence_ids, tuple):
                errors.append(f"test recommendation {test.test_id} evidence_ids must be a tuple")
                continue
            for evidence_id in test.evidence_ids:
                if evidence_id not in evidence_by_id:
                    errors.append(
                        f"test {test.test_id} references unknown evidence {evidence_id}"
                    )

        if self.status is ProposalStatus.NEEDS_EVIDENCE:
            if not self.unresolved_questions:
                errors.append("needs_evidence proposals must list unresolved questions")
        elif self.status is ProposalStatus.READY_FOR_REVIEW:
            errors.extend(self._ready_for_review_errors(evidence_by_id, dimension_ids))

        return tuple(errors)

    def _ready_for_review_errors(
        self,
        evidence_by_id: dict[str, EvidenceItem],
        dimension_ids: set[ConfidenceDimension],
    ) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            errors.append("ready_for_review proposals need a rationale")
        if not evidence_by_id:
            errors.append("ready_for_review proposals need evidence")
        if self.confidence.level is ConfidenceLevel.INSUFFICIENT:
            errors.append("insufficient confidence cannot be ready for review")
        if dimension_ids != set(ConfidenceDimension):
            errors.append("ready_for_review confidence needs all seven dimensions")
        if len(self.options) < 2:
            errors.append("ready_for_review proposals need at least two options")
        if not any(
            isinstance(option, ProposalOption) and option.defer
            for option in self.options
        ):
            errors.append("ready_for_review proposals need a do-nothing/defer option")
        if self.recommendation is None:
            errors.append("ready_for_review proposals need an advisory recommendation")
        if self.status is ProposalStatus.READY_FOR_REVIEW:
            errors.extend(self._type_evidence_errors(evidence_by_id))
            if (
                self.confidence.level is ConfidenceLevel.HIGH
                and any(
                    not isinstance(item.freshness, EvidenceFreshness)
                    or not isinstance(item.provenance, EvidenceProvenance)
                    or not isinstance(item.applicability, Applicability)
                    or item.freshness is not EvidenceFreshness.CURRENT
                    or item.provenance in {
                        EvidenceProvenance.MODIFIED,
                        EvidenceProvenance.UNVERIFIED,
                        EvidenceProvenance.UNKNOWN,
                    }
                    or item.applicability in {
                        Applicability.UNKNOWN,
                        Applicability.CONFLICTING,
                    }
                    for item in evidence_by_id.values()
                )
            ):
                errors.append(
                    "high confidence requires current, verified, non-conflicting evidence"
                )
        return errors

    def _type_evidence_errors(self, evidence: dict[str, EvidenceItem]) -> list[str]:
        classes = {
            item.evidence_class
            for item in evidence.values()
            if isinstance(item.evidence_class, EvidenceClass)
        }
        errors: list[str] = []

        if self.proposal_type is ProposalType.BUG_FIX:
            if EvidenceClass.IMPLEMENTATION not in classes:
                errors.append("bug fix proposals need implementation evidence")
            if EvidenceClass.TEST_RUN not in classes:
                errors.append("bug fix proposals need reproducible test-run evidence")
            if not classes & {
                EvidenceClass.APPROVED_DECISION,
                EvidenceClass.TEST_DEFINITION,
            }:
                errors.append("bug fix proposals need an applicable expectation")
        elif self.proposal_type is ProposalType.GAP:
            decisions = [
                item for item in evidence.values()
                if item.evidence_class is EvidenceClass.APPROVED_DECISION
            ]
            if not any(
                item.applicability is Applicability.APPLICABLE
                for item in decisions
            ):
                errors.append("gap proposals need an applicable approved decision")
            if EvidenceClass.IMPLEMENTATION not in classes:
                errors.append("gap proposals need inspected implementation evidence")
            if not classes & {
                EvidenceClass.TEST_DEFINITION,
                EvidenceClass.TEST_RUN,
            }:
                errors.append("gap proposals need relevant test evidence")
        elif self.proposal_type is ProposalType.ENHANCEMENT:
            if EvidenceClass.IMPLEMENTATION not in classes:
                errors.append("enhancement proposals need existing-behavior evidence")
            if EvidenceClass.USER_REPORT not in classes:
                errors.append("enhancement proposals need a stated user need")
        elif self.proposal_type is ProposalType.REFACTORING:
            if EvidenceClass.IMPLEMENTATION not in classes:
                errors.append("refactoring proposals need implementation evidence")
            if not classes & {
                EvidenceClass.TEST_DEFINITION,
                EvidenceClass.TEST_RUN,
            }:
                errors.append("refactoring proposals need regression-test evidence")
            if not self.behavior_preservation or not self.behavior_preservation.strip():
                errors.append("refactoring proposals need a behavior-preservation boundary")
        elif self.proposal_type is ProposalType.ARCHITECTURE:
            if EvidenceClass.IMPLEMENTATION not in classes:
                errors.append("architecture proposals need current implementation evidence")
            if not classes & {
                EvidenceClass.APPROVED_DECISION,
                EvidenceClass.PROPOSED_DESIGN,
            }:
                errors.append("architecture proposals need decision or design evidence")

        return errors


def _is_repository_relative(path: str) -> bool:
    if not path or "\\" in path:
        return False
    parsed = PurePosixPath(path)
    return (
        not parsed.is_absolute()
        and bool(parsed.parts)
        and all(part not in {"", ".", ".."} for part in parsed.parts)
        and not (parsed.parts[0].endswith(":"))
    )
