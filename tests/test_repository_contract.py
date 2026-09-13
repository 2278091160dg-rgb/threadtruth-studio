import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "threadtruth-studio"
LEGACY_NAME = "clothing" + "-portrait-studio"
PRIVATE_HOME_PATTERN = re.compile(r"/Users/[A-Za-z0-9._-]+/")
ALLOWED_LEGACY_FILES = {
    ROOT / "CHANGELOG.md",
    ROOT / "MIGRATION.md",
    ROOT / "PROVENANCE.md",
}


class RepositoryContractTests(unittest.TestCase):
    def test_demo_evidence_pipeline_is_development_only_and_locally_isolated(self):
        ignored = (ROOT / ".gitignore").read_text().splitlines()
        self.assertIn(".threadtruth/", ignored)
        self.assertTrue((ROOT / "tools" / "demo-media.py").is_file())
        self.assertTrue((ROOT / "tools" / "demo_media.py").is_file())
        self.assertFalse((SKILL / "tools" / "demo-media.py").exists())

    def test_demo_evidence_schemas_are_versioned_and_machine_readable(self):
        candidate = json.loads(
            (ROOT / "tools" / "schemas" / "demo-candidate-v1.schema.json").read_text()
        )
        rights = json.loads((ROOT / "docs" / "demo" / "rights-v1.schema.json").read_text())
        primary = json.loads(
            (ROOT / "docs" / "demo" / "primary-rights-v1.schema.json").read_text()
        )
        self.assertEqual(candidate["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(candidate["properties"]["schema_version"]["const"], "1.0")
        self.assertIn("human_review", candidate["required"])
        self.assertEqual(rights["properties"]["status"]["const"], "promoted")
        self.assertEqual(rights["properties"]["role"]["const"], "auxiliary")
        self.assertIn("media_license", rights["required"])
        self.assertEqual(primary["properties"]["role"]["const"], "primary")
        self.assertEqual(primary["properties"]["primary_demo_status"]["const"], "ready")
        self.assertIn("ai_content_label", primary["required"])

    def test_public_primary_demo_and_style_index_are_present(self):
        case = (
            ROOT
            / "docs"
            / "demo"
            / "primary-cases"
            / "white-hooded-puffer-vest-korean-cold"
        )
        rights = json.loads((case / "rights.json").read_text())
        self.assertEqual(rights["role"], "primary")
        self.assertEqual(rights["primary_demo_status"], "ready")
        self.assertEqual(rights["quality"]["state"], "image-ready")
        self.assertEqual(len(list(case.glob("look-*.jpg"))), 6)
        styles = json.loads((ROOT / "docs" / "demo" / "style-index.json").read_text())
        self.assertEqual(len(styles["styles"]), 24)
        self.assertEqual(sum(item["status"] == "ready" for item in styles["styles"]), 1)

    def test_demo_media_policy_states_rights_and_beta_boundaries(self):
        policy = (ROOT / "docs" / "demo" / "MEDIA-POLICY.md").read_text()
        for phrase in (
            "CC0-only",
            "does not imply endorsement",
            "Apache-2.0 does not cover media",
            "human review",
            "does not count toward the 30-day Beta",
        ):
            self.assertIn(phrase, policy)

    def test_plugin_manifest_has_public_identity(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "threadtruth-studio")
        self.assertEqual(manifest["version"], "1.0.0-beta.1")
        self.assertEqual(manifest["license"], "Apache-2.0")
        self.assertEqual(
            manifest["repository"],
            "https://github.com/2278091160dg-rgb/threadtruth-studio",
        )
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["interface"]["displayName"], "ThreadTruth Studio")
        self.assertIsInstance(manifest["interface"]["defaultPrompt"], list)
        self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("apps", manifest)

    def test_skill_identity_and_description_are_exact(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertIn("name: threadtruth-studio", text)
        expected = (
            "Create source-faithful fashion portrait sets from a real garment photo "
            "using 24 routed styles, explicit generation approval, six-image delivery, "
            "and commercial QA. Use for apparel model, editorial, and ecommerce portraits. "
            "Do not use for non-apparel products, text-only concepts, or general virtual "
            "try-on/API integration."
        )
        normalized = " ".join(text.split())
        self.assertIn(expected, normalized)

    def test_runtime_has_24_style_packs_and_canvas_checker(self):
        packs = list((SKILL / "references" / "styles").glob("*.pack.yaml"))
        packs = [path for path in packs if path.name != "_TEMPLATE.pack.yaml"]
        self.assertEqual(len(packs), 24)
        self.assertTrue((SKILL / "scripts" / "image-spec-check.py").is_file())
        for path in packs:
            self.assertRegex(path.read_text(), r"(?m)^maturity:\s+DRAFT(?:\s|$)")
            self.assertRegex(path.read_text(), r"(?m)^evals:\s+repo://evals/styles/")

    def test_development_evidence_is_outside_runtime(self):
        self.assertTrue((ROOT / "evals" / "evals.json").is_file())
        self.assertTrue((ROOT / "tools" / "pack-lint.py").is_file())
        for name in ("evals", "tests", "CHANGELOG.md", "RELEASE.md"):
            self.assertFalse((SKILL / name).exists(), name)

    def test_public_release_documents_exist(self):
        for name in (
            "LICENSE",
            "README.md",
            "README.zh-CN.md",
            "USER-GUIDE.html",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
            "ROADMAP.md",
            "MIGRATION.md",
            "PROVENANCE.md",
        ):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_active_runtime_does_not_use_legacy_name_or_model_id(self):
        for path in SKILL.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(errors="ignore")
            self.assertNotIn(LEGACY_NAME, text, str(path))
            self.assertIsNone(
                re.search(r"\bgpt-image-[\w.-]+", text, re.I),
                str(path),
            )

    def test_public_text_has_no_private_paths_or_qq_email(self):
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "dist" in path.parts:
                continue
            if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml", ".html", ".py"}:
                continue
            text = path.read_text(errors="ignore")
            if PRIVATE_HOME_PATTERN.search(text) or re.search(r"[\w.+-]+@qq\.com", text, re.I):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_legacy_name_is_limited_to_migration_and_provenance(self):
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "dist" in path.parts:
                continue
            if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml", ".html", ".py"}:
                continue
            if LEGACY_NAME in path.read_text(errors="ignore"):
                if path not in ALLOWED_LEGACY_FILES:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_user_guide_is_offline_and_release_sections_are_present(self):
        text = (ROOT / "USER-GUIDE.html").read_text()
        for section in (
            "capabilities",
            "boundaries",
            "installation",
            "quick-start",
            "privacy",
            "statuses",
            "rollback",
            "troubleshooting",
            "provenance",
        ):
            self.assertIn(f'data-release-section="{section}"', text)
        self.assertNotRegex(text, r'<(?:script|link)[^>]+https?://')

    def test_trigger_suite_covers_public_identity_and_adjacent_isolation(self):
        cases = json.loads((ROOT / "evals" / "trigger-evals.json").read_text())
        by_id = {case["id"]: case for case in cases}
        self.assertTrue(by_id["public-explicit"]["should_trigger"])
        for case_id in (
            "public-old-name-negative",
            "public-virtual-tryon-negative",
            "public-api-integration-negative",
        ):
            self.assertFalse(by_id[case_id]["should_trigger"])


if __name__ == "__main__":
    unittest.main()
