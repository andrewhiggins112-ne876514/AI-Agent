import unittest

from scripts.target_awareness import (
    TargetConfidence,
    TargetIdentity,
    TargetMatchStatus,
    assess_target,
    assess_foreground_target,
)


class TargetAssessmentTests(unittest.TestCase):
    def test_exact_window_handle_match_has_high_confidence(self):
        expected = TargetIdentity(
            window_handle=101,
            process_id=202,
            title="Notepad",
        )
        candidate = TargetIdentity(
            window_handle=101,
            process_id=202,
            title="Untitled - Notepad",
        )

        assessment = assess_target(expected, [candidate])

        self.assertEqual(assessment.status, TargetMatchStatus.MATCHED)
        self.assertEqual(assessment.confidence, TargetConfidence.HIGH)
        self.assertIs(assessment.matched, candidate)

    def test_process_id_match_has_medium_confidence(self):
        expected = TargetIdentity(
            window_handle=101,
            process_id=202,
            title="Notepad",
        )
        candidate = TargetIdentity(
            window_handle=303,
            process_id=202,
            title="Untitled - Notepad",
        )

        assessment = assess_target(expected, [candidate])

        self.assertEqual(assessment.status, TargetMatchStatus.MATCHED)
        self.assertEqual(assessment.confidence, TargetConfidence.MEDIUM)
        self.assertIs(assessment.matched, candidate)

    def test_title_only_match_is_low_confidence(self):
        expected = TargetIdentity(title="  Untitled - Notepad ")
        candidate = TargetIdentity(
            window_handle=303,
            process_id=404,
            title="untitled - notepad",
        )

        assessment = assess_target(expected, [candidate])

        self.assertEqual(assessment.status, TargetMatchStatus.MATCHED)
        self.assertEqual(assessment.confidence, TargetConfidence.LOW)
        self.assertNotEqual(assessment.confidence, TargetConfidence.HIGH)
        self.assertIs(assessment.matched, candidate)

    def test_title_does_not_override_conflicting_process_identity(self):
        expected = TargetIdentity(process_id=202, title="Notepad")
        candidate = TargetIdentity(
            window_handle=303,
            process_id=404,
            title="Notepad",
        )

        assessment = assess_target(expected, [candidate])

        self.assertEqual(assessment.status, TargetMatchStatus.NO_MATCH)
        self.assertEqual(assessment.confidence, TargetConfidence.UNKNOWN)
        self.assertIsNone(assessment.matched)

    def test_unmatched_candidates_return_no_match(self):
        expected = TargetIdentity(window_handle=101, process_id=202, title="Notepad")
        candidates = [
            TargetIdentity(window_handle=303, process_id=404, title="Calculator")
        ]

        assessment = assess_target(expected, candidates)

        self.assertEqual(assessment.status, TargetMatchStatus.NO_MATCH)
        self.assertEqual(assessment.confidence, TargetConfidence.UNKNOWN)
        self.assertIsNone(assessment.matched)
        self.assertEqual(assessment.candidate_count, 1)

    def test_duplicate_title_matches_are_ambiguous(self):
        expected = TargetIdentity(title="Notepad")
        candidates = [
            TargetIdentity(window_handle=101, process_id=202, title="Notepad"),
            TargetIdentity(window_handle=303, process_id=404, title="notepad"),
        ]

        assessment = assess_target(expected, candidates)

        self.assertEqual(assessment.status, TargetMatchStatus.AMBIGUOUS)
        self.assertEqual(assessment.confidence, TargetConfidence.UNKNOWN)
        self.assertIsNone(assessment.matched)
        self.assertEqual(assessment.candidate_count, 2)

    def test_duplicate_process_matches_are_ambiguous_without_exact_handle(self):
        expected = TargetIdentity(window_handle=999, process_id=202)
        candidates = [
            TargetIdentity(window_handle=101, process_id=202, title="One"),
            TargetIdentity(window_handle=303, process_id=202, title="Two"),
        ]

        assessment = assess_target(expected, candidates)

        self.assertEqual(assessment.status, TargetMatchStatus.AMBIGUOUS)
        self.assertEqual(assessment.confidence, TargetConfidence.UNKNOWN)
        self.assertIsNone(assessment.matched)

    def test_missing_expected_target_is_unknown(self):
        assessment = assess_target(None, [TargetIdentity(title="Notepad")])

        self.assertEqual(assessment.status, TargetMatchStatus.UNKNOWN)
        self.assertEqual(assessment.confidence, TargetConfidence.UNKNOWN)
        self.assertIsNone(assessment.matched)

    def test_foreground_process_mismatch_has_medium_confidence(self):
        assessment = assess_foreground_target(
            TargetIdentity(process_id=202),
            TargetIdentity(process_id=303),
        )

        self.assertEqual(assessment.status, TargetMatchStatus.MISMATCH)
        self.assertEqual(assessment.confidence, TargetConfidence.MEDIUM)

    def test_foreground_handle_mismatch_has_high_confidence(self):
        assessment = assess_foreground_target(
            TargetIdentity(window_handle=101, process_id=202),
            TargetIdentity(window_handle=303, process_id=404),
        )

        self.assertEqual(assessment.status, TargetMatchStatus.MISMATCH)
        self.assertEqual(assessment.confidence, TargetConfidence.HIGH)

    def test_foreground_without_comparable_identity_is_unknown(self):
        assessment = assess_foreground_target(
            TargetIdentity(process_id=202),
            TargetIdentity(title="Other window"),
        )

        self.assertEqual(assessment.status, TargetMatchStatus.NO_MATCH)
        self.assertEqual(assessment.confidence, TargetConfidence.UNKNOWN)

    def test_foreground_title_only_similarity_does_not_claim_a_match(self):
        assessment = assess_foreground_target(
            TargetIdentity(title="Notepad"),
            TargetIdentity(title="Notepad"),
        )

        self.assertEqual(assessment.status, TargetMatchStatus.UNKNOWN)
        self.assertEqual(assessment.confidence, TargetConfidence.LOW)
        self.assertIsNone(assessment.matched)

    def test_invalid_candidate_type_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "TargetIdentity"):
            assess_target(TargetIdentity(title="Notepad"), ["Notepad"])

    def test_target_records_are_immutable(self):
        target = TargetIdentity(window_handle=101)

        with self.assertRaises(AttributeError):
            target.window_handle = 202


if __name__ == "__main__":
    unittest.main()
