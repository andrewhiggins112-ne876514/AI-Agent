from datetime import datetime, timezone
from pathlib import Path
import unittest

from scripts.repository_awareness import (
    Importance,
    IndexLimits,
    RepositoryCategory,
    RepositoryFileMetadata,
    RepositoryIndex,
)
from scripts.testing_awareness import build_testing_inventory


def repository_index(files, *, complete=True, warnings=()):
    return RepositoryIndex(
        root=Path("."),
        files=tuple(files),
        indexed_at=datetime.now(timezone.utc),
        complete=complete,
        excluded_count=0,
        warnings=tuple(warnings),
        limits=IndexLimits(),
    )


def indexed_file(path, category=RepositoryCategory.SOURCE):
    return RepositoryFileMetadata(
        path=path,
        file_type="python",
        category=category,
        importance=Importance.NORMAL,
    )


class TestingAwarenessTests(unittest.TestCase):
    def test_discovers_test_paths_and_directories_despite_source_category(self):
        snapshot = repository_index(
            [
                indexed_file("Tests/test_sample.py"),
                indexed_file("scripts/worker_test.py"),
                indexed_file("src/ordinary.py"),
                indexed_file(
                    "Tests/README.md",
                    category=RepositoryCategory.DOCUMENTATION,
                ),
            ]
        )

        inventory = build_testing_inventory(snapshot)

        self.assertEqual(
            inventory.test_files,
            ("scripts/worker_test.py", "Tests/test_sample.py"),
        )
        self.assertEqual(inventory.test_directories, ("Tests",))

    def test_reports_configuration_candidate_without_claiming_it_is_valid(self):
        snapshot = repository_index(
            [
                indexed_file(
                    "PYPROJECT.TOML",
                    category=RepositoryCategory.OTHER,
                )
            ]
        )

        inventory = build_testing_inventory(snapshot)

        self.assertEqual(inventory.configuration_candidates, ("PYPROJECT.TOML",))
        self.assertTrue(inventory.complete)
        self.assertIn("contents were not inspected", inventory.warnings[0])

    def test_missing_configuration_and_incomplete_index_are_disclosed(self):
        snapshot = repository_index(
            [indexed_file("tests/test_sample.py")],
            complete=False,
            warnings=("tests: Maximum scan depth reached",),
        )

        inventory = build_testing_inventory(snapshot)

        self.assertFalse(inventory.complete)
        self.assertIn("framework configuration is unknown", inventory.warnings[-1])
        self.assertIn("Maximum scan depth reached", inventory.warnings[0])


if __name__ == "__main__":
    unittest.main()
