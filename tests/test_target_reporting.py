import unittest

from scripts.target_awareness import (
    TargetAssessment,
    TargetConfidence,
    TargetIdentity,
    TargetMatchStatus,
)
from scripts.target_reporting import format_target_assessment
from scripts.tools import ForegroundWindowSnapshot


class TargetAssessmentReportingTests(unittest.TestCase):
    def test_reports_expected_and_observed_identity_with_confidence(self):
        assessment = TargetAssessment(
            expected=TargetIdentity(process_id=1234, title="Notepad"),
            matched=None,
            confidence=TargetConfidence.MEDIUM,
            status=TargetMatchStatus.MISMATCH,
            reason="Foreground process ID differs from the expected target",
            candidate_count=1,
        )
        foreground = ForegroundWindowSnapshot(
            title="AI Agent",
            window_handle=5678,
            process_id=9876,
        )

        lines = format_target_assessment(assessment, foreground)

        self.assertIn(
            "Target assessment: mismatch (medium confidence)",
            lines,
        )
        self.assertIn(
            "Expected target: title='Notepad', process id=1234",
            lines,
        )
        self.assertIn(
            "Observed foreground: title='AI Agent', "
            "handle=0x162E, process id=9876",
            lines,
        )
        self.assertIn(
            "Assessment detail: Foreground process ID differs from the expected target",
            lines,
        )
        self.assertFalse(any("Dispatch blocked:" in line for line in lines))

    def test_reports_blocked_dispatch_explanation(self):
        assessment = TargetAssessment(
            expected=TargetIdentity(process_id=1234),
            matched=None,
            confidence=TargetConfidence.MEDIUM,
            status=TargetMatchStatus.MISMATCH,
            reason="Foreground process ID differs from the expected target",
            candidate_count=1,
        )

        lines = format_target_assessment(
            assessment,
            ForegroundWindowSnapshot(title="AI Agent", process_id=9876),
            dispatch_blocked=True,
            error="TYPE_TEXT was not dispatched: expected Notepad",
        )

        self.assertIn(
            "Dispatch blocked: TYPE_TEXT was not dispatched: expected Notepad",
            lines,
        )

    def test_reports_missing_foreground_and_unknown_expected_target(self):
        assessment = TargetAssessment(
            expected=None,
            matched=None,
            confidence=TargetConfidence.UNKNOWN,
            status=TargetMatchStatus.UNKNOWN,
            reason="No expected target was provided",
            candidate_count=0,
        )

        lines = format_target_assessment(
            assessment,
            ForegroundWindowSnapshot(error="foreground API unavailable"),
        )

        self.assertIn("Expected target: unknown", lines)
        self.assertIn(
            "Observed foreground: observation error: foreground API unavailable",
            lines,
        )


if __name__ == "__main__":
    unittest.main()
