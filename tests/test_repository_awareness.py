import tempfile
import unittest
from pathlib import Path

from scripts.repository_awareness import (
    Importance,
    IndexLimits,
    RepositoryCategory,
    RepositoryIndex,
)


class RepositoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def create_file(self, relative_path, content=""):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def metadata_for(self, index, relative_path):
        return next(item for item in index.files if item.path == relative_path)

    def test_initial_index_discovers_source_tests_and_documents_by_category(self):
        self.create_file("scripts/agent.py", "raise RuntimeError('must not run')")
        self.create_file("tests/test_agent.py")
        self.create_file("README.md")
        self.create_file("ARCHITECTURE_REVIEW.md")
        self.create_file("ROADMAP.md")
        self.create_file("DECISIONS.md")
        self.create_file("settings.toml")

        index = RepositoryIndex.build(self.root)

        self.assertTrue(index.complete)
        self.assertEqual(index.root, self.root.resolve())
        self.assertEqual(
            self.metadata_for(index, "scripts/agent.py").category,
            RepositoryCategory.SOURCE,
        )
        self.assertEqual(
            self.metadata_for(index, "tests/test_agent.py").category,
            RepositoryCategory.TEST,
        )
        self.assertEqual(
            self.metadata_for(index, "README.md").category,
            RepositoryCategory.DOCUMENTATION,
        )
        self.assertEqual(
            self.metadata_for(index, "ARCHITECTURE_REVIEW.md").category,
            RepositoryCategory.ARCHITECTURE,
        )
        self.assertEqual(
            self.metadata_for(index, "ROADMAP.md").category,
            RepositoryCategory.ROADMAP,
        )
        self.assertEqual(
            self.metadata_for(index, "DECISIONS.md").category,
            RepositoryCategory.DECISION,
        )
        self.assertEqual(
            self.metadata_for(index, "settings.toml").category,
            RepositoryCategory.OTHER,
        )

    def test_metadata_records_path_file_type_category_and_importance(self):
        self.create_file("PROJECT_VISION.md")
        self.create_file("PHASE4_EXECUTION_BACKENDS.md")
        self.create_file("tests/test_index.py")
        index = RepositoryIndex.build(self.root)

        vision = self.metadata_for(index, "PROJECT_VISION.md")
        architecture = self.metadata_for(index, "PHASE4_EXECUTION_BACKENDS.md")
        test_file = self.metadata_for(index, "tests/test_index.py")

        self.assertEqual(vision.file_type, "markdown")
        self.assertEqual(vision.importance, Importance.CORE)
        self.assertEqual(architecture.category, RepositoryCategory.ARCHITECTURE)
        self.assertEqual(architecture.importance, Importance.HIGH)
        self.assertEqual(test_file.file_type, "python")
        self.assertEqual(test_file.importance, Importance.HIGH)

    def test_gitignore_and_sensitive_paths_are_excluded(self):
        self.create_file(".gitignore", "*.tmp\n/private/\n")
        self.create_file("keep.py")
        self.create_file("scratch.tmp")
        self.create_file("private/notes.md")
        self.create_file(".env")
        self.create_file("api_token.py")
        self.create_file("credentials_notes.md")
        self.create_file("logs/runtime.log")
        self.create_file(".git/config")

        index = RepositoryIndex.build(self.root)
        indexed_paths = {item.path for item in index.files}

        self.assertEqual(indexed_paths, {"keep.py"})
        self.assertGreaterEqual(index.excluded_count, 5)

    def test_root_ignore_negation_reincludes_matching_file(self):
        self.create_file(".gitignore", "*.py\n!important.py\n")
        self.create_file("ignored.py")
        self.create_file("important.py")

        index = RepositoryIndex.build(self.root)

        self.assertEqual({item.path for item in index.files}, {"important.py"})

    def test_negation_does_not_reinclude_file_under_ignored_parent(self):
        self.create_file(".gitignore", "private/\n!private/keep.py\n")
        self.create_file("private/keep.py")

        index = RepositoryIndex.build(self.root)

        self.assertEqual(index.files, ())

    def test_nested_gitignore_rules_apply_to_their_subtree(self):
        self.create_file("module/.gitignore", "generated/\n")
        self.create_file("module/source.py")
        self.create_file("module/generated/output.py")

        index = RepositoryIndex.build(self.root)

        self.assertEqual(
            {item.path for item in index.files},
            {"module/source.py"},
        )

    def test_anchored_ignore_rule_does_not_match_nested_file(self):
        self.create_file(".gitignore", "/cache/\n")
        self.create_file("cache/root.py")
        self.create_file("nested/cache/kept.py")

        index = RepositoryIndex.build(self.root)

        self.assertEqual(
            {item.path for item in index.files},
            {"nested/cache/kept.py"},
        )

    def test_manual_refresh_rebuilds_index_from_same_root(self):
        self.create_file("old.py")
        initial = RepositoryIndex.build(self.root)
        (self.root / "old.py").unlink()
        self.create_file("ROADMAP.md")

        refreshed = initial.refresh()

        self.assertIsNot(refreshed, initial)
        self.assertEqual(refreshed.root, initial.root)
        self.assertEqual({item.path for item in refreshed.files}, {"ROADMAP.md"})
        self.assertGreaterEqual(refreshed.indexed_at, initial.indexed_at)

    def test_scan_limit_is_reported_as_partial(self):
        self.create_file("a.py")
        self.create_file("b.py")

        index = RepositoryIndex.build(self.root, IndexLimits(max_files=1))

        self.assertFalse(index.complete)
        self.assertTrue(any("Maximum file count" in warning for warning in index.warnings))
        self.assertEqual(len(index.files), 1)

    def test_depth_and_file_size_limits_are_reported(self):
        self.create_file("deep/child/file.py")
        self.create_file("large.py", "x" * 32)
        limits = IndexLimits(max_depth=1, max_file_bytes=16)

        index = RepositoryIndex.build(self.root, limits)

        self.assertFalse(index.complete)
        self.assertTrue(any("Maximum scan depth" in warning for warning in index.warnings))
        self.assertTrue(any("Maximum file size" in warning for warning in index.warnings))

    def test_invalid_root_and_limits_are_rejected(self):
        with self.assertRaises(NotADirectoryError):
            RepositoryIndex.build(self.create_file("not_a_directory.py"))
        with self.assertRaises(ValueError):
            IndexLimits(max_files=0)
        with self.assertRaises(ValueError):
            IndexLimits(max_file_bytes=0)
        with self.assertRaises(ValueError):
            IndexLimits(max_directories=0)
        with self.assertRaises(ValueError):
            IndexLimits(max_directory_entries=0)

    def test_directory_count_limit_is_reported_as_partial(self):
        self.create_file("nested/source.py")

        index = RepositoryIndex.build(self.root, IndexLimits(max_directories=1))

        self.assertFalse(index.complete)
        self.assertTrue(
            any("Maximum directory count" in warning for warning in index.warnings)
        )

    def test_directory_entry_limit_bounds_large_directory_listing(self):
        self.create_file("a.py")
        self.create_file("b.py")

        index = RepositoryIndex.build(
            self.root,
            IndexLimits(max_directory_entries=1),
        )

        self.assertFalse(index.complete)
        self.assertTrue(
            any("Maximum directory entry count" in warning for warning in index.warnings)
        )

    def test_indexing_does_not_execute_or_modify_source_files(self):
        source = self.create_file(
            "scripts/side_effect.py",
            "from pathlib import Path\nPath('should_not_exist').write_text('bad')\n",
        )
        original = source.read_bytes()
        original_paths = {path.relative_to(self.root) for path in self.root.rglob("*")}

        RepositoryIndex.build(self.root)

        after_paths = {path.relative_to(self.root) for path in self.root.rglob("*")}
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(after_paths, original_paths)
        self.assertFalse((self.root / "should_not_exist").exists())


if __name__ == "__main__":
    unittest.main()
