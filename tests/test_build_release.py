import importlib.util
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

            prefix = "threadtruth-studio-1.0.0-beta.1/"
            self.assertIn(prefix + ".codex-plugin/plugin.json", names)
            self.assertIn(prefix + "skills/threadtruth-studio/SKILL.md", names)
            self.assertIn(prefix + "USER-GUIDE.html", names)
            self.assertIn(prefix + "CONTRIBUTING.md", names)
            self.assertIn(prefix + "SECURITY.md", names)
            self.assertIn(prefix + "ROADMAP.md", names)
            self.assertIn(prefix + "docs/COMPETITIVE-LANDSCAPE.md", names)
            self.assertFalse(any("/evals/" in name for name in names))
            self.assertFalse(any("/tests/" in name for name in names))
            self.assertFalse(any("/tools/" in name for name in names))


if __name__ == "__main__":
    unittest.main()
