"""Behavior gates for development-only preview evidence (synthetic test pixels)."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
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
        for name in ("docs/demo", "skills/threadtruth-studio/references/styles"):
            shutil.copytree(ROOT / name, self.root / name)

    def prepare(self):
        self.m = module()
        return self.m.prepare(self.root, "test-run")

    def ingest(self):
        run = self.prepare()
        for number, board in enumerate("ABCD"):
            image = self.root / f"input-{board}.png"
            Image.new("RGB", (900, 900), (number * 50, 100, 150)).save(image)
            record = {"tool": "native-imagegen", "call_id": f"test-call-{board}",
                      "generated_at": "2026-09-13T01:00:00Z", "prompt_sha256": run["boards"][number]["prompt_sha256"]}
            self.m.ingest(self.root, "test-run", board, image, record)
        return self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")

    def reviewed(self):
        run = self.ingest()
        review = self.m.review_template(run)
        review.update(reviewer="github:test-human", reviewed_at="2026-09-13T02:00:00Z",
                      confirmation="I reviewed all 24 preview tiles against the authorized sources.",
                      ai_label_acknowledged=True, public_use_approved=True)
        for tile in review["tiles"]:
            tile.update(product="pass", style_check="pass", identity_layout="pass")
        self.m.approve(self.root, "test-run", review)
        return review

    def test_prepare_reads_actual_packs_and_builds_four_distinct_source_bound_prompts(self):
        run = self.prepare()
        self.assertEqual(len(run["source"]["assets"]), 4)
        self.assertEqual(run["identity_anchor"]["role"], "identity-only")
        self.assertEqual([b["id"] for b in run["boards"]], list("ABCD"))
        tiles = [t for b in run["boards"] for t in b["tiles"]]
        self.assertEqual(len({t["style"] for t in tiles}), 24)
        self.assertEqual(tiles[6]["style"], "old-money")
        prompt = (self.m.run_dir(self.root, "test-run") / "prompts/board-B.txt").read_text()
        self.assertIn("understated heritage elegance", prompt)
        self.assertIn("adult female", prompt)
        self.assertIn("3 columns", prompt)
        self.assertEqual(self.m.prepare(self.root, "test-run"), run)
        self.assertTrue(self.m.audit(self.root, "test-run"))  # missing native outputs

    def test_tension_pack_clothing_suggestions_are_filtered_out_of_mood_sections(self):
        run = self.prepare()
        tiles = {t["style"]: t for b in run["boards"] for t in b["tiles"]}
        for slug, forbidden in [("gorpcore", "nylon"), ("preppy", "knitwear"),
                                ("american-street", "oversized proportions"), ("balletcore", "tulle"),
                                ("coquette-ladylike", "bows"), ("neo-chinese", "oriental structure")]:
            self.assertNotIn(forbidden, tiles[slug]["visual"]["mood"])
        self.assertIn("graceful elongated posture", tiles["balletcore"]["visual"]["mood"])

    def test_prepared_native_prompts_require_visible_unobtrusive_preview_mark(self):
        self.prepare()
        for board in "ABCD":
            prompt = (self.m.run_dir(self.root, "test-run") / f"prompts/board-{board}.txt").read_text()
            self.assertIn("Draw a visible, unobtrusive English label 'AI PREVIEW / NOT FINAL' at the bottom right", prompt)
            self.assertIn("Do not cover any face or vest; no large centered watermark", prompt)

    def test_ingest_audit_gallery_and_approval_are_distinct(self):
        run = self.ingest()
        self.assertEqual(self.m.audit(self.root, "test-run"), [])
        self.assertTrue(self.m.audit(self.root, "test-run", require_approval=True))
        with self.assertRaises(ValueError):
            self.m.promote(self.root, "test-run")
        gallery = self.m.gallery(self.root, "test-run")
        self.assertIn("AI-generated style preview", gallery.read_text())
        self.assertIn("board-D.jpg", gallery.read_text())
        self.assertEqual(run["status"], "awaiting-human-review")

    def test_approved_promotion_is_independently_verifiable_and_idempotent(self):
        self.reviewed()
        public = self.m.promote(self.root, "test-run")
        self.assertEqual(self.m.validate_public_previews(self.root), [])
        self.assertEqual(self.m.promote(self.root, "test-run"), public)
        self.assertEqual(len(list(public.glob("*.jpg"))), 4)
        evidence = json.loads((public / "evidence.json").read_text())
        self.assertEqual(evidence["role"], "style-preview")
        self.assertNotIn(str(self.root), (public / "evidence.json").read_text())
        index = json.loads((self.root / "docs/demo/style-index.json").read_text())
        self.assertEqual(sum(bool(s.get("preview")) for s in index["styles"]), 24)
        self.assertEqual(sum(s["status"] == "ready" for s in index["styles"]), 1)
        import demo_media
        self.assertEqual(demo_media.validate_public_cases(self.root), [])
        shutil.rmtree(self.root / ".threadtruth")
        self.assertEqual(self.m.validate_public_previews(self.root), [])
        (public / "board-A.jpg").write_bytes(b"tampered")
        self.assertTrue(self.m.validate_public_previews(self.root))

    def test_rejects_incomplete_or_forged_review_and_missing_ai_notice(self):
        run = self.ingest()
        review = self.m.review_template(run)
        with self.assertRaises(ValueError):
            self.m.approve(self.root, "test-run", review)
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        for field, value in (("status", "approved"), ("ai_label", "")):
            changed = copy.deepcopy(run)
            changed[field] = value
            path.write_text(json.dumps(changed))
            self.assertTrue(self.m.audit(self.root, "test-run", require_approval=True))

    def test_rejects_changed_packs_sources_maps_prompts_and_generation(self):
        run = self.ingest()
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        changes = [lambda x: x["boards"][0]["tiles"][0].update(style="unknown"),
                   lambda x: x["boards"][0]["tiles"][0].update(style="old-money"),
                   lambda x: x["boards"].pop(),
                   lambda x: x["source"]["assets"].pop(),
                   lambda x: x["boards"][0]["generation"].update(prompt_sha256="0" * 64),
                   lambda x: x.update(role="generated-final"),
                   lambda x: x["boards"][0].update(path="../../outside.jpg")]
        for change in changes:
            changed = copy.deepcopy(run)
            change(changed)
            path.write_text(json.dumps(changed))
            self.assertTrue(self.m.audit(self.root, "test-run"))
        path.write_text(json.dumps(run))
        pack = self.root / run["boards"][0]["tiles"][0]["pack"]["path"]
        pack.write_text(pack.read_text() + "\n# changed\n")
        self.assertTrue(self.m.audit(self.root, "test-run"))

    def test_refuses_overwrite_unsafe_ids_and_changed_approved_assets(self):
        self.reviewed()
        with self.assertRaises(ValueError):
            self.m.prepare(self.root, "../escape")
        with self.assertRaises(ValueError):
            self.m.ingest(self.root, "test-run", "A", self.root / "input-B.png", {})
        run_path = self.m.run_dir(self.root, "test-run")
        (run_path / "board-A.jpg").write_bytes((run_path / "board-B.jpg").read_bytes())
        with self.assertRaises(ValueError):
            self.m.promote(self.root, "test-run")

    def test_release_rejects_orphan_and_unapproved_preview_media(self):
        import demo_media
        spec = importlib.util.spec_from_file_location("preview_release_test", ROOT / "tools/build-release.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        orphan = self.root / "docs/demo/style-previews/orphan"
        orphan.mkdir(parents=True)
        (orphan / "board-A.jpg").write_bytes(b"orphan")
        self.assertTrue(demo_media.validate_public_cases(self.root))
        with self.assertRaises(ValueError):
            build._validate_public_demo(self.root)

    def test_public_review_cannot_be_replaced_by_status_or_partial_tile_qa(self):
        self.reviewed()
        public = self.m.promote(self.root, "test-run")
        path = public / "evidence.json"
        original = json.loads(path.read_text())
        changes = [lambda x: x.pop("human_review"),
                   lambda x: x["human_review"].update(ai_label_acknowledged=False),
                   lambda x: x["human_review"]["tiles"][0].update(product="pending"),
                   lambda x: x["human_review"].update(reviewed_at="2020-01-01T00:00:00Z"),
                   lambda x: x["boards"][0].update(original_sha256="0" * 64),
                   lambda x: x.update(ai_label=""),
                   lambda x: x["human_review"].update(confirmation="/".join(("", "Users", "private", "review.txt")))]
        for change in changes:
            record = copy.deepcopy(original)
            change(record)
            path.write_text(json.dumps(record))
            self.assertTrue(self.m.validate_public_previews(self.root))
        path.write_text(json.dumps(original))
        (public / "orphan.webp").write_bytes(b"orphan")
        self.assertTrue(self.m.validate_public_previews(self.root))

    def test_source_rights_prompt_and_symlink_tampering_fail_closed(self):
        run = self.ingest()
        source = self.root / run["source"]["rights_ref"]
        original = source.read_text()
        rights = json.loads(original)
        rights["source_rights"]["source_model_display_authorized"] = False
        source.write_text(json.dumps(rights))
        self.assertTrue(self.m.audit(self.root, "test-run"))
        source.write_text(original)
        directory = self.m.run_dir(self.root, "test-run")
        prompt = directory / "prompts/board-A.txt"
        original = prompt.read_text()
        prompt.write_text(original + "change vest to black")
        self.assertTrue(self.m.audit(self.root, "test-run"))
        prompt.write_text(original)
        board = directory / "board-A.jpg"
        board.unlink()
        board.symlink_to(directory / "board-B.jpg")
        self.assertTrue(self.m.audit(self.root, "test-run"))

    def test_ingest_retains_local_native_output_receipt_but_never_publishes_paths(self):
        self.ingest()
        local = self.m.run_dir(self.root, "test-run")
        receipt = local / "native-receipts/board-A.json"
        self.assertTrue(receipt.is_file(), "native output provenance receipt missing")
        self.assertEqual(json.loads(receipt.read_text())["native_output_path"], str((self.root / "input-A.png").resolve()))
        (local / "native-outputs/board-A.png").write_bytes(b"tampered")
        self.assertTrue(self.m.audit(self.root, "test-run"))

    def test_ingest_refuses_existing_native_receipt_without_writing_any_board(self):
        run = self.prepare()
        local = self.m.run_dir(self.root, "test-run")
        receipts = local / "native-receipts"
        receipts.mkdir()
        receipt = receipts / "board-A.json"
        receipt.write_text('{"existing":"keep"}')
        image = self.root / "input.png"
        Image.new("RGB", (900, 900), "white").save(image)
        generation = {"tool": "native-imagegen", "call_id": "first", "generated_at": "2026-09-13T01:00:00Z",
                      "prompt_sha256": run["boards"][0]["prompt_sha256"]}
        with self.assertRaises(ValueError):
            self.m.ingest(self.root, "test-run", "A", image, generation)
        self.assertEqual(receipt.read_text(), '{"existing":"keep"}')
        self.assertFalse((local / "board-A.jpg").exists())

    def test_prepare_refuses_unknown_state_and_run_id_mismatch(self):
        run = self.prepare()
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        for field, value in (("status", "image-ready"), ("run_id", "another-run")):
            changed = copy.deepcopy(run)
            changed[field] = value
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                self.m.prepare(self.root, "test-run")


if __name__ == "__main__":
    unittest.main()
