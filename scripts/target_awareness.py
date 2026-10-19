"""Pure target identity assessment for desktop window candidates."""

from dataclasses import dataclass
from enum import Enum


class TargetConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class TargetMatchStatus(str, Enum):
    MATCHED = "matched"
    MISMATCH = "mismatch"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TargetIdentity:
    window_handle: int | None = None
    process_id: int | None = None
    title: str | None = None


@dataclass(frozen=True)
class TargetAssessment:
    expected: TargetIdentity | None
    matched: TargetIdentity | None
    confidence: TargetConfidence
    status: TargetMatchStatus
    reason: str
    candidate_count: int


def assess_target(
    expected: TargetIdentity | None,
    candidates: tuple[TargetIdentity, ...] | list[TargetIdentity],
) -> TargetAssessment:
    """Compare an expected identity with candidates without external access."""
    if expected is not None and not isinstance(expected, TargetIdentity):
        raise TypeError("expected must be a TargetIdentity or None")
    candidate_list = tuple(candidates)
    if any(not isinstance(candidate, TargetIdentity) for candidate in candidate_list):
        raise TypeError("candidates must contain only TargetIdentity values")

    candidate_count = len(candidate_list)
    if expected is None:
        return TargetAssessment(
            expected=None,
            matched=None,
            confidence=TargetConfidence.UNKNOWN,
            status=TargetMatchStatus.UNKNOWN,
            reason="No expected target was provided",
            candidate_count=candidate_count,
        )
    if candidate_count == 0:
        return TargetAssessment(
            expected=expected,
            matched=None,
            confidence=TargetConfidence.UNKNOWN,
            status=TargetMatchStatus.UNKNOWN,
            reason="No candidate windows were provided",
            candidate_count=0,
        )

    if expected.window_handle is not None:
        handle_matches = [
            candidate
            for candidate in candidate_list
            if candidate.window_handle == expected.window_handle
            and not (
                expected.process_id is not None
                and candidate.process_id is not None
                and candidate.process_id != expected.process_id
            )
        ]
        if len(handle_matches) == 1:
            return TargetAssessment(
                expected=expected,
                matched=handle_matches[0],
                confidence=TargetConfidence.HIGH,
                status=TargetMatchStatus.MATCHED,
                reason="Window handle matched",
                candidate_count=candidate_count,
            )
        if len(handle_matches) > 1:
            return _ambiguous_assessment(
                expected,
                candidate_count,
                "Multiple candidates have the expected window handle",
            )

    if expected.process_id is not None:
        process_matches = [
            candidate
            for candidate in candidate_list
            if candidate.process_id == expected.process_id
        ]
        if len(process_matches) == 1:
            return TargetAssessment(
                expected=expected,
                matched=process_matches[0],
                confidence=TargetConfidence.MEDIUM,
                status=TargetMatchStatus.MATCHED,
                reason="Process ID matched",
                candidate_count=candidate_count,
            )
        if len(process_matches) > 1:
            return _ambiguous_assessment(
                expected,
                candidate_count,
                "Multiple candidate windows belong to the expected process",
            )

    expected_title = expected.title.strip().casefold() if expected.title else ""
    if (
        expected_title
        and expected.window_handle is None
        and expected.process_id is None
    ):
        title_matches = [
            candidate
            for candidate in candidate_list
            if candidate.title
            and candidate.title.strip().casefold() == expected_title
        ]
        if len(title_matches) == 1:
            return TargetAssessment(
                expected=expected,
                matched=title_matches[0],
                confidence=TargetConfidence.LOW,
                status=TargetMatchStatus.MATCHED,
                reason="Title matched; title alone is not a strong identity",
                candidate_count=candidate_count,
            )
        if len(title_matches) > 1:
            return _ambiguous_assessment(
                expected,
                candidate_count,
                "Multiple candidate windows have the expected title",
            )

    return TargetAssessment(
        expected=expected,
        matched=None,
        confidence=TargetConfidence.UNKNOWN,
        status=TargetMatchStatus.NO_MATCH,
        reason="No candidate matched the expected target",
        candidate_count=candidate_count,
    )


def assess_foreground_target(
    expected: TargetIdentity | None,
    foreground: TargetIdentity | None,
) -> TargetAssessment:
    """Assess one foreground identity and distinguish known mismatches."""
    if foreground is None:
        return assess_target(expected, ())

    assessment = assess_target(expected, (foreground,))
    if (
        assessment.status is TargetMatchStatus.MATCHED
        and assessment.confidence is TargetConfidence.LOW
    ):
        return TargetAssessment(
            expected=expected,
            matched=None,
            confidence=TargetConfidence.LOW,
            status=TargetMatchStatus.UNKNOWN,
            reason="Title-only similarity is insufficient to confirm the target",
            candidate_count=1,
        )
    if assessment.status is not TargetMatchStatus.NO_MATCH or expected is None:
        return assessment

    if (
        expected.window_handle is not None
        and foreground.window_handle is not None
        and expected.window_handle != foreground.window_handle
    ):
        return TargetAssessment(
            expected=expected,
            matched=None,
            confidence=TargetConfidence.HIGH,
            status=TargetMatchStatus.MISMATCH,
            reason="Foreground window handle differs from the expected target",
            candidate_count=1,
        )

    if (
        expected.process_id is not None
        and foreground.process_id is not None
        and expected.process_id != foreground.process_id
    ):
        return TargetAssessment(
            expected=expected,
            matched=None,
            confidence=TargetConfidence.MEDIUM,
            status=TargetMatchStatus.MISMATCH,
            reason="Foreground process ID differs from the expected target",
            candidate_count=1,
        )

    return assessment


def _ambiguous_assessment(
    expected: TargetIdentity,
    candidate_count: int,
    reason: str,
) -> TargetAssessment:
    return TargetAssessment(
        expected=expected,
        matched=None,
        confidence=TargetConfidence.UNKNOWN,
        status=TargetMatchStatus.AMBIGUOUS,
        reason=reason,
        candidate_count=candidate_count,
    )
