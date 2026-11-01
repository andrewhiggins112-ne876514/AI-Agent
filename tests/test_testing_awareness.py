from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from scripts.repository_awareness import (
    Importance,
    IndexLimits,
    RepositoryCategory,
    RepositoryFileMetadata,
    RepositoryIndex,
)
from scripts.testing_awareness import (
    TestingInventory,
    build_testing_inventory,
    format_testing_report,
)


def repository_index(root, entries, *, complete=True, warnings=()):
    files = []
    for path, (content, category) in entries.items():
        file_path = Path(root) / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        files.append(
            RepositoryFileMetadata(
                path=path,
                file_type=file_path.suffix.lstrip("."),
                category=category,
                importance=Importance.NORMAL,
            )
        )

    return RepositoryIndex(
        root=Path(root),
        files=tuple(files),
        indexed_at=datetime.now(timezone.utc),
        complete=complete,
        excluded_count=0,
        warnings=tuple(warnings),
        limits=IndexLimits(),
    )


class TestingAwarenessTests(unittest.TestCase):
    def test_discovers_test_paths_and_directories_despite_source_category(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = repository_index(
                root,
                {
                    "Tests/test_sample.py": (
                        "import pytest\n"
                        "@pytest.fixture\n"
                        "def sample():\n"
                        "    return sys.platform\n"
                        "raise RuntimeError('must not execute')\n",
                        RepositoryCategory.SOURCE,
                    ),
                    "scripts/worker_test.py": (
                        "import unittest\n"
                        "import win32gui\n"
                        "class Example(unittest.TestCase):\n"
                        "    def setUp(self): pass\n",
                        RepositoryCategory.SOURCE,
                    ),
                    "Tests/README.md": (
                        "Test notes",
                        RepositoryCategory.DOCUMENTATION,
                    ),
                    "tests/fixtures/helpers.py": (
                        "def helper(): return 1\n",
                        RepositoryCategory.SOURCE,
                    ),
                    "src/ordinary.py": (
                        "raise RuntimeError('must not execute')\n",
                        RepositoryCategory.SOURCE,
                    ),
                    "pytest.ini": (
                        "[pytest]\naddopts = -q\n",
                        RepositoryCategory.OTHER,
                    ),
                },
            )

            inventory = build_testing_inventory(snapshot)

        self.assertEqual(
            inventory.test_files,
            ("scripts/worker_test.py", "Tests/test_sample.py"),
        )
        self.assertEqual(inventory.test_directories, ("Tests",))
        self.assertEqual(inventory.frameworks, ("pytest", "unittest"))
        self.assertIn(
            "Tests/test_sample.py: pytest fixture decorator",
            inventory.fixture_indicators,
        )
        self.assertIn(
            "scripts/worker_test.py: unittest lifecycle method setUp",
            inventory.fixture_indicators,
        )
        self.assertIn(
            "tests/fixtures/helpers.py: file is in a fixture directory",
            inventory.fixture_indicators,
        )
        self.assertIn(
            "scripts/worker_test.py: imports Windows API module win32gui",
            inventory.platform_indicators,
        )
        self.assertIn(
            "Tests/test_sample.py: references sys.platform",
            inventory.platform_indicators,
        )
        self.assertTrue(inventory.complete)

    def test_parses_pytest_configuration_candidate(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = repository_index(
                root,
                {
                    "pyproject.toml": (
                        "[tool.pytest.ini_options]\naddopts = '-q'\n",
                        RepositoryCategory.OTHER,
                    )
                },
            )

            inventory = build_testing_inventory(snapshot)

        self.assertEqual(inventory.configuration_candidates, ("pyproject.toml",))
        self.assertEqual(inventory.frameworks, ("pytest",))
        self.assertTrue(inventory.complete)

    def test_malformed_and_oversized_evidence_is_incomplete(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = repository_index(
                root,
                {
                    "pytest.ini": (
                        "not a valid section header\n",
                        RepositoryCategory.OTHER,
                    ),
                    "tests/test_large.py": (
                        " " * (64 * 1024 + 1),
                        RepositoryCategory.TEST,
                    ),
                },
            )

            inventory = build_testing_inventory(snapshot)

        self.assertFalse(inventory.complete)
        self.assertTrue(
            any(
                "malformed INI configuration" in warning
                for warning in inventory.warnings
            )
        )
        self.assertFalse(
            any(
                "not a valid section header" in warning
                for warning in inventory.warnings
            )
        )
        self.assertTrue(
            any(
                "exceeds the 65536-byte evidence limit" in warning
                for warning in inventory.warnings
            )
        )

    def test_missing_configuration_and_incomplete_index_are_disclosed(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = repository_index(
                root,
                {
                    "tests/test_sample.py": (
                        "import unittest\n",
                        RepositoryCategory.TEST,
                    )
                },
                complete=False,
                warnings=("tests: Maximum scan depth reached",),
            )

            inventory = build_testing_inventory(snapshot)

        self.assertFalse(inventory.complete)
        self.assertIn(
            "No recognized test configuration file",
            "\n".join(inventory.warnings),
        )
        self.assertIn("Maximum scan depth reached", inventory.warnings[0])


class TestingReportFormattingTests(unittest.TestCase):
    def test_formats_all_inventory_sections_and_not_run_status(self):
        inventory = TestingInventory(
            test_files=("tests/test_sample.py",),
            test_directories=("tests",),
            configuration_candidates=("pytest.ini",),
            frameworks=("pytest",),
            fixture_indicators=("tests/conftest.py: pytest fixture discovery file",),
            platform_indicators=("tests/test_sample.py: references sys.platform",),
            complete=True,
            warnings=("Configuration contents are unknown.",),
        )

        report = format_testing_report(inventory)

        self.assertEqual(
            report,
            "\n".join(
                (
                    "Testing status report",
                    "======================",
                    "Tests have not been run: NOT RUN",
                    "Inventory completeness: COMPLETE",
                    "Test directories:",
                    "- tests",
                    "Test files:",
                    "- tests/test_sample.py",
                    "Configuration candidates:",
                    "- pytest.ini",
                    "Framework indicators:",
                    "- pytest",
                    "Fixture indicators:",
                    "- tests/conftest.py: pytest fixture discovery file",
                    "Platform indicators:",
                    "- tests/test_sample.py: references sys.platform",
                    "Warnings:",
                    "- Configuration contents are unknown.",
                )
            ),
        )

    def test_empty_incomplete_inventory_shows_each_section(self):
        inventory = TestingInventory(
            test_files=(),
            test_directories=(),
            configuration_candidates=(),
            frameworks=(),
            fixture_indicators=(),
            platform_indicators=(),
            complete=False,
            warnings=(),
        )

        report = format_testing_report(inventory)

        self.assertIn("Tests have not been run: NOT RUN", report)
        self.assertIn("Inventory completeness: INCOMPLETE", report)
        for heading in (
            "Test directories:",
            "Test files:",
            "Configuration candidates:",
            "Framework indicators:",
            "Fixture indicators:",
            "Platform indicators:",
            "Warnings:",
        ):
            self.assertIn(heading, report)
            self.assertIn(f"{heading}\n- None found", report)


class RepositoryTestingReportIntegrationTests(unittest.TestCase):
    def test_repository_snapshot_exposes_testing_status_report(self):
        with tempfile.TemporaryDirectory() as root:
            snapshot = repository_index(
                root,
                {
                    "tests/test_sample.py": (
                        "import unittest\n",
                        RepositoryCategory.TEST,
                    ),
                    "pytest.ini": (
                        "[pytest]\n",
                        RepositoryCategory.OTHER,
                    ),
                },
            )

            report = snapshot.testing_status_report()

        self.assertIn("Tests have not been run: NOT RUN", report)
        self.assertIn("Inventory completeness: COMPLETE", report)
        self.assertIn("- tests/test_sample.py", report)
        self.assertIn("- pytest.ini", report)


if __name__ == "__main__":
    unittest.main()
