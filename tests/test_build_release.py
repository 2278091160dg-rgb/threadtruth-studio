import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "build-release.py"


class ReleaseBuildTests(unittest.TestCase):
    def test_allowlist_release_excludes_development_material(self):
        spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as output_dir:
            archive, checksum = module.build_release(ROOT, Path(output_dir))
            self.assertTrue(archive.is_file())
            self.assertTrue(checksum.is_file())
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())

            version = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"]
            prefix = f"threadtruth-studio-{version}/"
            self.assertIn(prefix + ".codex-plugin/plugin.json", names)
            self.assertIn(prefix + "skills/threadtruth-studio/SKILL.md", names)
            self.assertIn(prefix + "USER-GUIDE.html", names)
            self.assertIn(prefix + "install-local.py", names)
            self.assertIn(prefix + "CONTRIBUTING.md", names)
            self.assertIn(prefix + "SECURITY.md", names)
            self.assertIn(prefix + "ROADMAP.md", names)
            self.assertIn(prefix + "docs/COMPETITIVE-LANDSCAPE.md", names)
            self.assertIn(
                prefix
                + "docs/demo/primary-cases/white-hooded-puffer-vest-korean-cold/look-1.jpg",
                names,
            )
            self.assertIn(prefix + "docs/demo/STYLES.md", names)
            self.assertIn(prefix + "docs/demo/style-preview-v1.schema.json", names)
            self.assertIn(prefix + "docs/demo/style-preview-v2.schema.json", names)
            self.assertFalse(any("/evals/" in name for name in names))
            self.assertFalse(any("/tests/" in name for name in names))
            self.assertFalse(any("/tools/" in name for name in names))
            self.assertFalse(any("/.threadtruth/" in name for name in names))

    def test_release_rejects_tampered_primary_demo_media(self):
        spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            clone = Path(temp_dir) / "repo"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", "dist", ".threadtruth", "__pycache__"),
            )
            target = (
                clone
                / "docs"
                / "demo"
                / "primary-cases"
                / "white-hooded-puffer-vest-korean-cold"
                / "look-4.jpg"
            )
            target.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "public demo rights validation failed"):
                module.build_release(clone, Path(temp_dir) / "out")

    def test_release_fails_when_public_demo_rights_are_invalid(self):
        spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            clone = Path(temp_dir) / "repo"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", "dist", ".threadtruth", "__pycache__"),
            )
            case = clone / "docs" / "demo" / "cases" / "bad-case"
            case.mkdir(parents=True)
            (case / "source.jpg").write_bytes(b"tampered")
            (case / "source-metadata.json").write_text(
                json.dumps({"objectID": 1, "isPublicDomain": False, "primaryImage": ""})
            )
            (case / "rights.json").write_text(
                json.dumps(
                    {
                        "status": "promoted",
                        "role": "auxiliary",
                        "source_license": {"id": "CC-BY-4.0"},
                        "media_license": {"id": "CC-BY-4.0"},
                        "asset": {"sha256": "wrong"},
                        "source": {"object_id": 1},
                    }
                )
            )
            (case / "README.md").write_text("invalid")
            with self.assertRaisesRegex(ValueError, "public demo rights validation failed"):
                module.build_release(clone, Path(temp_dir) / "out")

    def test_release_rejects_unregistered_demo_media(self):
        spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            clone = Path(temp_dir) / "repo"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", "dist", ".threadtruth", "__pycache__"),
            )
            for name in ("unregistered.jpg", "unregistered.jfif", "unregistered.mp4", "unregistered"):
                path = clone / "docs" / "demo" / name
                path.write_bytes(b"not registered")
                with self.assertRaisesRegex(ValueError, "unregistered demo"):
                    module.build_release(clone, Path(temp_dir) / "out")
                path.unlink()

    def test_release_rejects_stale_rights_index_without_cases_directory(self):
        spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            clone = Path(temp_dir) / "repo"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", "dist", ".threadtruth", "__pycache__"),
            )
            shutil.rmtree(clone / "docs" / "demo" / "cases", ignore_errors=True)
            (clone / "docs" / "demo" / "RIGHTS.md").write_text("stale")
            with self.assertRaisesRegex(ValueError, "rights index is stale"):
                module.build_release(clone, Path(temp_dir) / "out")

    def test_release_rejects_superseded_v1_public_preview_evidence(self):
        spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            clone = Path(temp_dir) / "repo"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", "dist", ".threadtruth", "__pycache__"),
            )
            public = clone / "docs/demo/style-previews/legacy"
            public.mkdir(parents=True)
            (public / "evidence.json").write_text(
                json.dumps({"schema_version": "1.0", "run_id": "legacy", "status": "approved", "boards": []})
            )
            with self.assertRaisesRegex(ValueError, "public demo rights validation failed"):
                module.build_release(clone, Path(temp_dir) / "out")


if __name__ == "__main__":
    unittest.main()
