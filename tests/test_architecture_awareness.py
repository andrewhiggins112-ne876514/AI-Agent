import tempfile
import unittest
from pathlib import Path

from scripts.architecture_awareness import (
    ArchitectureDocumentType,
    ArchitectureKnowledgeModel,
    ArchitectureRelationType,
)
from scripts.repository_awareness import IndexLimits, RepositoryIndex


class ArchitectureKnowledgeModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def create_file(self, relative_path, content=""):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_discovers_document_types_and_answers_phase_and_area_queries(self):
        self.create_file(
            "PROJECT_VISION.md",
            "# Project Vision\n\nLong-term goals.\n",
        )
        self.create_file(
            "ROADMAP.md",
            "# AI-Agent Roadmap\n\n"
            "## Phase 3: Task Execution Engine\n\n"
            "## Phase 4: Persistent Memory\n",
        )
        self.create_file("DECISIONS.md", "# Architectural Decisions\n")
        self.create_file(
            "PHASE5_1_ARCHITECTURE_AWARENESS.md",
            "# Phase 5.1.1 Architecture Awareness\n\n"
            "## Repository Awareness\n\n"
            "## Execution\n",
        )
        self.create_file(
            "PHASE5_1_IMPLEMENTATION_PLAN.md",
            "# Phase 5.1 Repository Awareness Implementation Plan\n",
        )
        self.create_file("DESIGN.md", "# Execution Design\n")
        self.create_file("README.md", "# General Documentation\n")

        model = ArchitectureKnowledgeModel.from_repository(self.root)

        self.assertTrue(model.complete)
        self.assertEqual(
            model.document_type("PROJECT_VISION.md"),
            ArchitectureDocumentType.VISION,
        )
        self.assertEqual(
            model.document_type(r"PHASE5_1_ARCHITECTURE_AWARENESS.md"),
            ArchitectureDocumentType.ARCHITECTURE,
        )
        self.assertEqual(
            model.document_type("PHASE5_1_IMPLEMENTATION_PLAN.md"),
            ArchitectureDocumentType.IMPLEMENTATION_PLAN,
        )
        self.assertEqual(model.document_type("README.md"), None)
        self.assertEqual(
            model.phases_for_document("PHASE5_1_ARCHITECTURE_AWARENESS.md"),
            ("5.1.1",),
        )
        self.assertEqual(
            {document.path for document in model.documents_for_phase("Phase 3")},
            {"ROADMAP.md"},
        )
        self.assertEqual(
            {document.path for document in model.documents_for_area("repository awareness")},
            {
                "PHASE5_1_ARCHITECTURE_AWARENESS.md",
                "PHASE5_1_IMPLEMENTATION_PLAN.md",
            },
        )
        self.assertEqual(
            {document.path for document in model.documents_for_area("execution")},
            {
                "DESIGN.md",
                "PHASE5_1_ARCHITECTURE_AWARENESS.md",
                "ROADMAP.md",
            },
        )

    def test_document_relationships_resolve_local_document_links(self):
        self.create_file("ROADMAP.md", "# Roadmap\n## Phase 3: Execution\n")
        self.create_file("DECISIONS.md", "# Decisions\n")
        architecture = self.create_file(
            "ARCHITECTURE.md",
            "# Architecture\n\n"
            "[Roadmap](ROADMAP.md#phase-3)\n"
            "[Decision](DECISIONS.md)\n"
            "[Missing](MISSING.md)\n"
            "[External](https://example.invalid/architecture)\n"
            "[Outside](../../outside.md)\n",
        )

        model = ArchitectureKnowledgeModel.from_repository(self.root)
        links = [
            relation
            for relation in model.relationships
            if relation.source_path == "ARCHITECTURE.md"
            and relation.relation_type is ArchitectureRelationType.REFERENCES
        ]

        self.assertEqual(
            {(relation.target, relation.resolved) for relation in links},
            {("ROADMAP.md", True), ("DECISIONS.md", True), ("MISSING.md", False)},
        )
        self.assertTrue(any("unresolved" in warning for warning in model.warnings))
        self.assertEqual(architecture.read_text(encoding="utf-8").count("["), 5)

    def test_relationship_metadata_links_document_to_phase_and_area(self):
        self.create_file(
            "PHASE4_EXECUTION_BACKENDS.md",
            "# Phase 4 Execution Backends\n## Workspace Automation\n",
        )

        model = ArchitectureKnowledgeModel.from_repository(self.root)
        relations = {
            (relation.relation_type, relation.target)
            for relation in model.relationships
            if relation.source_path == "PHASE4_EXECUTION_BACKENDS.md"
        }

        self.assertIn(
            (ArchitectureRelationType.BELONGS_TO_PHASE, "4"),
            relations,
        )
        self.assertIn(
            (ArchitectureRelationType.DESCRIBES_AREA, "workspace automation"),
            relations,
        )

    def test_model_is_read_only_and_does_not_execute_source(self):
        source = self.create_file(
            "scripts/side_effect.py",
            "from pathlib import Path\nPath('created_by_execution').touch()\n",
        )
        document = self.create_file(
            "ARCHITECTURE.md",
            "# Architecture\n[Decision](DECISIONS.md)\n",
        )
        decision = self.create_file("DECISIONS.md", "# Decisions\n")
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

        ArchitectureKnowledgeModel.build(RepositoryIndex.build(self.root))

        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertTrue(source.exists())
        self.assertTrue(document.exists())
        self.assertTrue(decision.exists())
        self.assertFalse((self.root / "created_by_execution").exists())

    def test_unreadable_document_marks_model_incomplete(self):
        document = self.create_file("ARCHITECTURE.md")
        document.write_bytes(b"\xff")
        index = RepositoryIndex.build(self.root)

        model = ArchitectureKnowledgeModel.build(index)

        self.assertFalse(model.complete)
        self.assertEqual(model.documents, ())
        self.assertTrue(any("cannot read document" in warning for warning in model.warnings))

    def test_incomplete_repository_index_remains_incomplete(self):
        self.create_file("ARCHITECTURE.md", "# Architecture\n")
        self.create_file("extra.py")
        index = RepositoryIndex.build(self.root, IndexLimits(max_files=1))

        model = ArchitectureKnowledgeModel.build(index)

        self.assertFalse(model.complete)


if __name__ == "__main__":
    unittest.main()
