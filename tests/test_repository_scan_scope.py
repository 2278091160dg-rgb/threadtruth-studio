"""Exercise the public-contract consumers inside real disposable worktrees."""

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests import test_repository_contract as contracts


class RepositoryScanScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = (Path(temporary.name) / ".worktrees" / "checkout").resolve()
        self.root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write(".gitignore", ".threadtruth/\n.superpowers/\ndist/\n")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def check_contract(self, method):
        allowed = {self.root / name for name in ("CHANGELOG.md", "MIGRATION.md", "PROVENANCE.md")}
        with patch.object(contracts, "ROOT", self.root), patch.object(contracts, "ALLOWED_LEGACY_FILES", allowed):
            getattr(contracts.RepositoryContractTests(method), method)()

    def test_private_path_in_new_public_document_is_not_skipped_by_checkout_ancestor(self):
        self.write("new-document.md", "/" + "Users/" + "fixture/")
        with self.assertRaisesRegex(AssertionError, "new-document.md"):
            self.check_contract("test_public_text_has_no_private_paths_or_qq_email")

    def test_legacy_name_in_new_public_document_is_not_skipped_by_checkout_ancestor(self):
        self.write("new-document.md", "clothing" + "-portrait-studio")
        with self.assertRaisesRegex(AssertionError, "new-document.md"):
            self.check_contract("test_legacy_name_is_limited_to_migration_and_provenance")

    def test_ignored_local_records_are_excluded_until_force_tracked(self):
        marker = "/" + "Users/" + "fixture/\n" + "clothing" + "-portrait-studio"
        self.write(".threadtruth/draft.md", marker)
        self.write(".superpowers/review.md", marker)
        methods = (
            "test_public_text_has_no_private_paths_or_qq_email",
            "test_legacy_name_is_limited_to_migration_and_provenance",
        )
        for method in methods:
            self.check_contract(method)
        subprocess.run(["git", "add", "-f", ".threadtruth/draft.md"], cwd=self.root, check=True)
        for method in methods:
            with self.subTest(method=method), self.assertRaisesRegex(AssertionError, "draft.md"):
                self.check_contract(method)

    def test_migration_whitelist_does_not_exempt_other_tracked_documents(self):
        marker = "clothing" + "-portrait-studio"
        self.write("MIGRATION.md", marker)
        self.check_contract("test_legacy_name_is_limited_to_migration_and_provenance")
        self.write("README.md", marker)
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        with self.assertRaisesRegex(AssertionError, "README.md"):
            self.check_contract("test_legacy_name_is_limited_to_migration_and_provenance")

    def test_extracted_tree_under_worktree_named_ancestor_is_scanned_in_full(self):
        self.root = self.root.parent / "extracted"
        self.write(".threadtruth/included.md", "/" + "Users/" + "fixture/")
        with self.assertRaisesRegex(AssertionError, "included.md"):
            self.check_contract("test_public_text_has_no_private_paths_or_qq_email")
