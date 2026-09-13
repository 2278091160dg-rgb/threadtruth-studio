"""Behavior gates for development-only preview evidence (synthetic test pixels)."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def module():
    path = ROOT / "tools/style_preview.py"
    assert path.exists(), "preview pipeline is missing"
    spec = importlib.util.spec_from_file_location("style_preview", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("docs/demo", "skills/threadtruth-studio/references"):
            shutil.copytree(ROOT / name, self.root / name)

    def prepare(self):
        self.m = module()
        return self.m.prepare(self.root, "test-run")

    def generation(self, preview, number, *, call_id=None):
        return {
            "tool": "native-imagegen",
            "call_id": call_id or f"test-call-{number}",
            "generated_at": "2026-09-13T01:00:00Z",
            "prompt_sha256": preview["prompt_sha256"],
        }

    def image(self, number):
        path = self.root / f"input-{number}.png"
        Image.new("RGB", (601, 607), ((number * 31) % 256, 100, 150)).save(path)
        return path

    def ingest_all(self):
        run = self.prepare()
        for number, preview in enumerate(run["previews"], start=1):
            self.m.ingest(
                self.root,
                "test-run",
                preview["style"],
                self.image(number),
                self.generation(preview, number),
            )
        return self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")

    def approve_all(self):
        run = self.ingest_all()
        for preview in run["previews"]:
            current = self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")
            review = self.m.review_template(current, preview["style"])
            review.update(
                reviewer="github:test-human",
                reviewed_at="2026-09-13T02:00:00Z",
                confirmation=self.m.confirmation(preview["style"]),
                public_use_approved=True,
            )
            for pose in review["poses"]:
                pose.update(product="pass", pose_layout="pass", identity_style="pass", ai_disclosure="pass")
            self.m.approve(self.root, "test-run", preview["style"], review)
        return self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")

    def test_prepare_builds_24_single_style_six_pose_previews(self):
        run = self.prepare()
        self.assertEqual(run["schema_version"], "2.0")
        self.assertEqual(len(run["previews"]), 24)
        self.assertEqual(len({p["style"] for p in run["previews"]}), 24)
        for preview in run["previews"]:
            self.assertEqual([pose["ordinal"] for pose in preview["poses"]], list(range(1, 7)))
            self.assertTrue(all("style" not in pose for pose in preview["poses"]))

    def test_prepare_binds_registry_packs_runtime_rules_and_canonical_action_zero_prompt(self):
        run = self.prepare()
        self.assertEqual(set(run["rules"]), {"prompt_build", "modes_scenes", "safety_core", "style_router"})
        self.assertEqual(len(run["source"]["assets"]), 4)
        self.assertEqual(run["identity_anchor"]["role"], "identity-only")
        masters = [
            "SIDE_TURN_STANDING", "SIDE_LEANING_WALL", "UPRIGHT_SEATED",
            "FRONT_LIGHT_STEP", "SLIGHT_FORWARD_LEAN", "BACK_TURN_GLANCE",
        ]
        all_styles = {preview["style"] for preview in run["previews"]}
        for preview in run["previews"]:
            self.assertEqual([pose["master"] for pose in preview["poses"]], masters)
            prompt = (self.m.run_dir(self.root, "test-run") / "prompts" / f"{preview['style']}.txt").read_text()
            self.assertIn("single 2x3 grid contact-sheet preview", prompt)
            self.assertIn("PREVIEW ONLY — NOT FINAL", prompt)
            self.assertIn(preview["style"], prompt)
            self.assertNotIn("no grid", prompt.lower())
            for other in all_styles - {preview["style"]}:
                self.assertNotIn(other, prompt)
        self.assertEqual(self.m.prepare(self.root, "test-run"), run)

    def test_tension_pack_clothing_suggestions_are_filtered_out_of_mood_sections(self):
        run = self.prepare()
        previews = {preview["style"]: preview for preview in run["previews"]}
        for slug, forbidden in [
            ("gorpcore", "nylon"), ("preppy", "knitwear"),
            ("american-street", "oversized proportions"), ("balletcore", "tulle"),
            ("coquette-ladylike", "bows"), ("neo-chinese", "oriental structure"),
        ]:
            self.assertNotIn(forbidden, previews[slug]["visual"]["mood"])
        self.assertIn("graceful elongated posture", previews["balletcore"]["visual"]["mood"])

    def test_incomplete_audit_and_gallery_report_real_missing_styles(self):
        run = self.prepare()
        findings = self.m.audit(self.root, "test-run")
        self.assertEqual(len(findings), 24)
        self.assertTrue(all("missing native output" in finding for finding in findings))
        style = run["previews"][0]["style"]
        self.assertEqual(self.m.audit(self.root, "test-run", style=style), [f"{style}: missing native output"])
        gallery = self.m.gallery(self.root, "test-run")
        content = gallery.read_text()
        self.assertIn("24 single-style, six-pose sheets", content)
        self.assertEqual(content.count("Not generated"), 24)
        self.assertIn(run["previews"][0]["display_name"], content)
        self.assertIn(run["previews"][0]["poses"][0]["description"], content)
        self.assertIn(run["previews"][0]["poses"][0]["head_gaze"], content)
        self.assertIn("@media(max-width:480px){ol{grid-template-columns:1fr}}", content)

    def test_style_ingest_preserves_native_dimensions_and_requires_exact_receipt(self):
        run = self.prepare()
        preview = run["previews"][0]
        image = self.image(1)
        generation = self.generation(preview, 1)
        record = self.m.ingest(self.root, "test-run", preview["style"], image, generation)
        stored = record["previews"][0]
        self.assertEqual((stored["width"], stored["height"]), (601, 607))
        receipt = self.m.run_dir(self.root, "test-run") / "native-receipts" / f"{preview['style']}.json"
        self.assertEqual(json.loads(receipt.read_text())["generation"], generation)
        self.assertEqual(self.m.ingest(self.root, "test-run", preview["style"], image, generation), record)
        bad = dict(generation, prompt_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "generation prompt mismatch"):
            self.m.ingest(self.root, "test-run", run["previews"][1]["style"], self.image(2), bad)

    def test_rejects_mixed_style_pose_missing_or_duplicate_pose_ids_and_rule_drift(self):
        run = self.prepare()
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        mutations = (
            lambda value: value["previews"][0]["poses"][0].update(style="old-money"),
            lambda value: value["previews"][0]["poses"].pop(),
            lambda value: value["previews"][0]["poses"][1].update(ordinal=1),
            lambda value: value["previews"][0].update(style=value["previews"][1]["style"]),
        )
        for mutate in mutations:
            changed = copy.deepcopy(run)
            mutate(changed)
            path.write_text(json.dumps(changed))
            self.assertTrue(self.m.audit(self.root, "test-run"))
        path.write_text(json.dumps(run))
        prompt_rules = self.root / run["rules"]["prompt_build"]["path"]
        prompt_rules.write_text(prompt_rules.read_text() + "\nchanged\n")
        self.assertTrue(self.m.audit(self.root, "test-run"))

    def test_rejects_reused_native_call_original_or_optimized_hash(self):
        run = self.prepare()
        first, second = run["previews"][:2]
        image = self.image(1)
        self.m.ingest(self.root, "test-run", first["style"], image, self.generation(first, 1))
        with self.assertRaisesRegex(ValueError, "duplicate native call"):
            self.m.ingest(self.root, "test-run", second["style"], self.image(2), self.generation(second, 2, call_id="test-call-1"))
        with self.assertRaisesRegex(ValueError, "duplicate native output"):
            self.m.ingest(self.root, "test-run", second["style"], image, self.generation(second, 2))

    def test_source_authorization_and_incomplete_whole_sheet_review_fail_closed(self):
        run = self.ingest_all()
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        changed = copy.deepcopy(run)
        changed["source"]["authorization"]["public_use_authorized"] = False
        path.write_text(json.dumps(changed))
        self.assertTrue(self.m.audit(self.root, "test-run"))
        path.write_text(json.dumps(run))
        style = run["previews"][0]["style"]
        review = self.m.review_template(run, style)
        review.update(
            reviewer="github:test-human", reviewed_at="2026-09-13T02:00:00Z",
            confirmation=self.m.confirmation(style), public_use_approved=True,
        )
        for pose in review["poses"]:
            pose.update(product="pass", pose_layout="pass", identity_style="pass", ai_disclosure="pass")
        review["poses"][5]["pose_layout"] = "pending"
        with self.assertRaisesRegex(ValueError, "human review incomplete"):
            self.m.approve(self.root, "test-run", style, review)

    def test_approved_24_sheet_promotion_is_publicly_verifiable_and_idempotent(self):
        self.approve_all()
        public = self.m.promote(self.root, "test-run")
        self.assertEqual(self.m.validate_public_previews(self.root), [])
        self.assertEqual(self.m.promote(self.root, "test-run"), public)
        self.assertEqual(len(list(public.glob("*.jpg"))), 24)
        evidence = json.loads((public / "evidence.json").read_text())
        self.assertEqual(evidence["schema_version"], "2.0")
        self.assertNotIn(str(self.root), (public / "evidence.json").read_text())
        index = json.loads((self.root / "docs/demo/style-index.json").read_text())
        self.assertEqual(sum(bool(style.get("preview")) for style in index["styles"]), 24)
        self.assertEqual(sum(style["status"] == "ready" for style in index["styles"]), 1)
        self.assertIn("whole six-pose sheet", (self.root / "docs/demo/styles/old-money.md").read_text())
        import demo_media
        self.assertEqual(demo_media.validate_public_cases(self.root), [])
        shutil.rmtree(self.root / ".threadtruth")
        self.assertEqual(self.m.validate_public_previews(self.root), [])
        next(public.glob("*.jpg")).write_bytes(b"tampered")
        self.assertTrue(self.m.validate_public_previews(self.root))

    def test_promotion_requires_all_24_unique_approved_sheets(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        review = self.m.review_template(run, style)
        review.update(
            reviewer="github:test-human", reviewed_at="2026-09-13T02:00:00Z",
            confirmation=self.m.confirmation(style), public_use_approved=True,
        )
        for pose in review["poses"]:
            pose.update(product="pass", pose_layout="pass", identity_style="pass", ai_disclosure="pass")
        self.m.approve(self.root, "test-run", style, review)
        with self.assertRaisesRegex(ValueError, "unapproved styles"):
            self.m.promote(self.root, "test-run")

    def test_v1_is_read_only_and_cannot_be_promoted_or_migrated(self):
        self.m = module()
        directory = self.m.run_dir(self.root, "legacy")
        directory.mkdir(parents=True)
        legacy = {"schema_version": "1.0", "run_id": "legacy", "status": "approved", "boards": []}
        (directory / "evidence.json").write_text(json.dumps(legacy))
        before = (directory / "evidence.json").read_bytes()
        self.assertIn("superseded", " ".join(self.m.audit(self.root, "legacy")))
        self.assertIn("Historical v1", self.m.gallery(self.root, "legacy").read_text())
        with self.assertRaisesRegex(ValueError, "superseded"):
            self.m.promote(self.root, "legacy")
        with self.assertRaisesRegex(ValueError, "superseded"):
            self.m.prepare(self.root, "legacy")
        self.assertEqual((directory / "evidence.json").read_bytes(), before)

    def test_cli_rejects_legacy_board_selector_with_style_guidance(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/style-preview.py"), "--root", str(self.root), "ingest",
             "--run-id", "test-run", "--board", "A", "--image", "x", "--generation-record", "x"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--board is superseded; use --style", result.stderr)

    def test_refuses_unsafe_ids_paths_and_unregistered_styles(self):
        run = self.prepare()
        with self.assertRaises(ValueError):
            self.m.prepare(self.root, "../escape")
        with self.assertRaisesRegex(ValueError, "registered style"):
            self.m.ingest(self.root, "test-run", "unknown", self.image(1), {})
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        changed = copy.deepcopy(run)
        changed["previews"][0]["path"] = "../../outside.jpg"
        path.write_text(json.dumps(changed))
        self.assertTrue(self.m.audit(self.root, "test-run"))


if __name__ == "__main__":
    unittest.main()
