"""Behavior gates for development-only preview evidence (synthetic test pixels)."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

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
        shutil.rmtree(self.root / "docs/demo/style-previews", ignore_errors=True)

    def prepare(self):
        self.m = module()
        run = self.m.prepare(self.root, "test-run", "beige-blazer-denim-outfit")
        self.batch_for_style = {}
        for batch_number, offset in enumerate(range(0, 24, 6), start=1):
            styles = [preview["style"] for preview in run["previews"][offset:offset + 6]]
            manifest = {
                "schema_version": "1.0",
                "batch_id": f"outfit-batch-{batch_number:02d}",
                "run_id": "test-run",
                "styles": styles,
                "maximum_calls": 6,
                "authorization_sha256": str(batch_number) * 64,
                "authorized_at": f"2026-09-14T0{batch_number}:00:00Z",
                "scope": "serial-native-generation;no-auto-retry",
            }
            run = self.m.register_batch(self.root, "test-run", manifest)
            for style in styles:
                self.batch_for_style[style] = manifest
        return run

    def test_v5_outfit_plan_binds_one_source_and_every_outfit_fact(self):
        self.m = module()
        run = self.m.prepare(self.root, "outfit-run", "beige-blazer-denim-outfit")
        self.assertEqual(run["schema_version"], "5.0")
        self.assertEqual(run["source"]["case_id"], "beige-blazer-denim-outfit")
        self.assertEqual(len(run["source"]["assets"]), 1)
        self.assertEqual(run["identity_anchor"]["role"], "identity-only")
        for preview in run["previews"]:
            prompt = (
                self.m.run_dir(self.root, "outfit-run") / "prompts" / f"{preview['style']}.txt"
            ).read_text()
            for fact in run["source"]["outfit"]["core_items"]:
                self.assertIn(fact, prompt)
            self.assertIn("complete coordinated outfit", prompt)
            self.assertIn("Attached image 1 is the only authoritative outfit truth", prompt)
            self.assertIn("Attached image 2 is identity-only", prompt)
            self.assertNotIn("same one white hooded puffer vest", prompt)

    def test_v5_prepare_requires_a_valid_hash_bound_source_case(self):
        self.m = module()
        with self.assertRaisesRegex(ValueError, "source case is required"):
            self.m.prepare(self.root, "missing-source", None)
        with self.assertRaisesRegex(ValueError, "unknown preview source"):
            self.m.prepare(self.root, "unknown-source", "unknown")
        source = self.root / "docs/demo/preview-sources/beige-blazer-denim-outfit/source.jpg"
        source.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "preview source"):
            self.m.prepare(self.root, "drifted-source", "beige-blazer-denim-outfit")

    def test_released_v4_collection_matches_golden_manifest(self):
        manifest = json.loads((ROOT / "tests/fixtures/white-vest-24-v1-beta3.sha256.json").read_text())
        public = ROOT / "docs/demo/style-previews/white-vest-24-v1"
        self.assertEqual(
            sorted(path.relative_to(public).as_posix() for path in public.rglob("*") if path.is_file()),
            sorted(manifest),
        )
        for relative, expected in manifest.items():
            data = (public / relative).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected["sha256"])
            self.assertEqual(len(data), expected["bytes"])

    def test_schema_v4_is_public_read_only_and_all_mutations_refuse_it(self):
        self.m = module()
        public = ROOT / "docs/demo/style-previews/white-vest-24-v1"
        local = self.m.run_dir(self.root, "white-vest-24-v1")
        local.mkdir(parents=True)
        shutil.copyfile(public / "evidence.json", local / "evidence.json")
        record = json.loads((local / "evidence.json").read_text())
        self.assertEqual(record["schema_version"], "4.0")
        style = record["previews"][0]["style"]
        for mutate in (
            lambda: self.m.prepare(self.root, "white-vest-24-v1"),
            lambda: self.m.ingest(self.root, "white-vest-24-v1", style, self.image(1), {}),
            lambda: self.m.compose(self.root, "white-vest-24-v1", style, {}, Path("missing-font")),
            lambda: self.m.approve(self.root, "white-vest-24-v1", style, {}),
            lambda: self.m.promote(self.root, "white-vest-24-v1"),
        ):
            with self.assertRaisesRegex(ValueError, "schema 4.0 is frozen"):
                mutate()

    def generation(self, preview, number, *, call_id=None):
        manifest = self.batch_for_style[preview["style"]]
        return {
            "tool": "native-imagegen",
            "call_id": f"test-call-{number}" if call_id is None else call_id,
            "generated_at": "2026-09-14T08:10:00Z",
            "prompt_sha256": preview["prompt_sha256"],
            "batch_id": manifest["batch_id"],
            "authorization_sha256": manifest["authorization_sha256"],
            "model_docs_url": "https://learn.chatgpt.com/docs/image-generation",
            "model_docs_verified_at": "2026-09-14",
            "per_call_model": "unavailable",
        }

    def test_four_batches_are_immutable_ordered_and_non_overlapping(self):
        self.m = module()
        run = self.m.prepare(self.root, "batch-run", "beige-blazer-denim-outfit")
        styles = [preview["style"] for preview in run["previews"]]

        def manifest(number, selected):
            return {
                "schema_version": "1.0",
                "batch_id": f"outfit-batch-{number:02d}",
                "run_id": "batch-run",
                "styles": selected,
                "maximum_calls": 6,
                "authorization_sha256": str(number) * 64,
                "authorized_at": f"2026-09-14T0{number}:00:00Z",
                "scope": "serial-native-generation;no-auto-retry",
            }

        first = manifest(1, styles[:6])
        registered = self.m.register_batch(self.root, "batch-run", first)
        self.assertEqual(self.m.register_batch(self.root, "batch-run", first), registered)
        changed = copy.deepcopy(first)
        changed["styles"] = list(reversed(changed["styles"]))
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.m.register_batch(self.root, "batch-run", changed)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.m.register_batch(self.root, "batch-run", manifest(2, styles[5:11]))
        with self.assertRaisesRegex(ValueError, "one through six"):
            self.m.register_batch(self.root, "batch-run", manifest(2, styles[6:13]))
        for number, offset in ((2, 6), (3, 12), (4, 18)):
            self.m.register_batch(self.root, "batch-run", manifest(number, styles[offset:offset + 6]))
        with self.assertRaisesRegex(ValueError, "four batches"):
            self.m.register_batch(self.root, "batch-run", manifest(5, [styles[0]]))

    def test_generation_is_bound_to_registered_batch_authorization(self):
        run = self.prepare()
        preview = run["previews"][0]
        generation = self.generation(preview, 1, call_id=None)
        generation["call_id"] = None
        record = self.m.ingest(self.root, "test-run", preview["style"], self.image(1), generation)
        self.assertIsNone(record["previews"][0]["generation"]["call_id"])
        second = run["previews"][1]
        wrong_batch = self.generation(second, 2)
        wrong_batch["batch_id"] = self.batch_for_style[run["previews"][6]["style"]]["batch_id"]
        with self.assertRaisesRegex(ValueError, "outside registered batch"):
            self.m.ingest(self.root, "test-run", second["style"], self.image(2), wrong_batch)
        wrong_hash = self.generation(second, 2)
        wrong_hash["authorization_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "authorization hash"):
            self.m.ingest(self.root, "test-run", second["style"], self.image(2), wrong_hash)

    def image(self, number, size=(900, 900)):
        path = self.root / f"input-{number}.png"
        image = Image.new("RGB", size, ((number * 31) % 256, 100, 150))
        if size == (900, 900):
            draw = ImageDraw.Draw(image)
            for index, bounds in enumerate(
                (
                    (90, 120, 299, 399), (345, 120, 554, 399), (600, 120, 809, 399),
                    (90, 420, 299, 699), (345, 420, 554, 699), (600, 420, 809, 699),
                )
            ):
                draw.rectangle(bounds, fill=(30 + index * 20, 80 + index * 10, 160 - index * 10))
            draw.rectangle((60, 20, 839, 54), fill=(245, 245, 245))
            draw.rectangle((60, 70, 839, 99), fill=(220, 220, 220))
            draw.rectangle((90, 750, 809, 799), fill=(200, 200, 200))
        image.save(path)
        return path

    def completed_review(self, record, style):
        review = self.m.review_template(record, style)
        review.update(
            reviewer="github:test-human",
            reviewed_at="2026-09-14T09:00:00Z",
            confirmation=self.m.confirmation(style),
            public_use_approved=True,
        )
        review["geometry"] = {
            "cells": [
                [44, 140, 360, 480], [420, 140, 360, 480], [796, 140, 360, 480],
                [44, 636, 360, 480], [420, 636, 360, 480], [796, 636, 360, 480],
            ],
            "title": [44, 16, 1112, 72],
            "subtitle": [44, 92, 1112, 36],
            "footer": [44, 1128, 1112, 60],
        }
        review["checks"] = {
            "observed_boundaries": "pass",
            "full_bilingual_title": "pass",
            "correct_subtitle": "pass",
            "readable_ai_footer": "pass",
            "text_subject_non_overlap": "pass",
            "complete_panel_extraction": "pass",
            "padding_no_subject_loss": "pass",
            "derivative_disclosure": "pass",
        }
        for cell in review["cells"]:
            cell["core_items"] = {key: "pass" for key in cell["core_items"]}
            cell["optional_items"] = {
                key: "not-visible-no-contradiction" for key in cell["optional_items"]
            }
            for key in (
                "complete_outfit_visible", "adult_identity", "anatomy", "pose_layout",
                "registered_style_distinct", "ai_disclosure", "framing",
            ):
                cell[key] = "pass"
        return review

    def ingest_all(self):
        run = self.prepare()
        for number, preview in enumerate(run["previews"], start=1):
            ingested = self.m.ingest(
                self.root,
                "test-run",
                preview["style"],
                self.image(number),
                self.generation(preview, number),
            )
            self.compose(ingested, preview['style'])
        return self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")

    def compose(self, record, style):
        font_candidates = [Path('/System/Library/Fonts/STHeiti Light.ttc'),
                           Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
        font = next((path for path in font_candidates if path.is_file()), None)
        if font is None:
            self.skipTest('A CJK font is required for label rendering')
        preview = next(item for item in record['previews'] if item['style'] == style)
        return self.m.compose(self.root, 'test-run', style, {
            'original_sha256': preview['original_sha256'],
            'cells': [[90, 120, 210, 280], [345, 120, 210, 280], [600, 120, 210, 280],
                      [90, 420, 210, 280], [345, 420, 210, 280], [600, 420, 210, 280]],
        }, font)

    def approve_all(self):
        run = self.ingest_all()
        for preview in run["previews"]:
            current = self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")
            review = self.completed_review(current, preview["style"])
            self.m.approve(self.root, "test-run", preview["style"], review)
        return self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")

    def test_prepare_builds_24_single_style_six_pose_previews(self):
        run = self.prepare()
        self.assertEqual(run["schema_version"], "5.0")
        self.assertEqual(len(run["previews"]), 24)
        self.assertEqual(len({p["style"] for p in run["previews"]}), 24)
        for preview in run["previews"]:
            self.assertEqual([pose["ordinal"] for pose in preview["poses"]], list(range(1, 7)))
            self.assertTrue(all("style" not in pose for pose in preview["poses"]))

    def test_prepare_binds_square_board_cell_framing_and_exact_native_labels(self):
        run = self.prepare()
        preview = run["previews"][0]
        self.assertEqual(
            preview["layout_contract"],
            {
                "board_aspect_ratio": "1:1",
                "rows": 2,
                "columns": 3,
                "cell_aspect_ratio": "3:4",
                "label_bands": ["title", "subtitle", "footer"],
                "framing": ["full-body", "full-body", "half-body-permitted", "full-body", "half-body-permitted", "full-body"],
            },
        )
        self.assertEqual(
            preview["label_contract"],
            {
                "title": preview["display_name"],
                "subtitle": f"同款完整套装 · {preview['mode']} {self.m.MODE_NAMES[preview['mode']]} · 六姿势预览",
                "footer": "AI生成 · 方向预览 · 非成片 / PREVIEW ONLY — NOT FINAL",
            },
        )
        prompt = (self.m.run_dir(self.root, "test-run") / "prompts" / f"{preview['style']}.txt").read_text()
        for exact_text in preview["label_contract"].values():
            self.assertIn(exact_text, prompt)
        self.assertIn("square 1:1 board", prompt)
        self.assertIn("3:4", prompt)
        self.assertIn("independent title, subtitle and footer bands", prompt)

    def test_non_square_native_output_is_retained_but_requires_composition(self):
        run = self.prepare()
        preview = run["previews"][0]
        record = self.m.ingest(
            self.root, "test-run", preview["style"], self.image(1, (601, 607)), self.generation(preview, 1)
        )
        stored = record["previews"][0]
        retained = self.m.run_dir(self.root, "test-run") / "native-outputs" / preview["style"]
        self.assertEqual((stored["width"], stored["height"]), (601, 607))
        self.assertTrue(any(retained.parent.glob(retained.name + ".*")))
        self.assertEqual(
            self.m.audit(self.root, "test-run", style=preview["style"]),
            [f"{preview['style']}: missing or malformed composition"],
        )
        with self.assertRaisesRegex(ValueError, "composition"):
            self.m.approve(self.root, "test-run", preview["style"], {})

    def test_schema_two_record_is_historical_and_rejected_by_every_mutation(self):
        run = self.prepare()
        preview = run["previews"][0]
        self.m.ingest(self.root, "test-run", preview["style"], self.image(1), self.generation(preview, 1))
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        record = json.loads(path.read_text())
        record["schema_version"] = "2.0"
        path.write_text(json.dumps(record))
        before = path.read_bytes()
        self.assertIn("historical", " ".join(self.m.audit(self.root, "test-run")))
        self.assertIn("not approved for current standard", self.m.gallery(self.root, "test-run").read_text())
        for mutate in (
            lambda: self.m.prepare(self.root, "test-run"),
            lambda: self.m.ingest(self.root, "test-run", preview["style"], self.image(2), self.generation(preview, 2)),
            lambda: self.m.approve(self.root, "test-run", preview["style"], {}),
            lambda: self.m.promote(self.root, "test-run"),
        ):
            with self.assertRaisesRegex(ValueError, "historical"):
                mutate()
        self.assertEqual(path.read_bytes(), before)
        public = self.root / "docs/demo/style-previews/historical-v2"
        public.mkdir(parents=True)
        public_record = copy.deepcopy(record)
        public_record["run_id"] = "historical-v2"
        (public / "evidence.json").write_text(json.dumps(public_record))
        self.assertIn("historical preview evidence", " ".join(self.m.validate_public_previews(self.root)))

    def test_prepare_binds_registry_packs_runtime_rules_and_canonical_action_zero_prompt(self):
        run = self.prepare()
        self.assertEqual(set(run["rules"]), {"prompt_build", "modes_scenes", "safety_core", "style_router"})
        self.assertEqual(len(run["source"]["assets"]), 1)
        self.assertEqual(run["source"]["review_contract"], "coordinated-outfit-v1")
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
        self.assertIn("img{display:block;width:auto;max-width:100%;height:auto}", content)

    def test_gallery_approval_label_requires_a_complete_hash_bound_review(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        run["previews"][0]["human_review"] = self.m.review_template(run, style)
        path.write_text(json.dumps(run))
        content = self.m.gallery(self.root, "test-run", style=style).read_text()
        self.assertIn("<p>review invalid / pending</p>", content)
        self.assertNotIn("<p>approved</p>", content)

        review = self.completed_review(run, style)
        run["previews"][0]["human_review"] = review
        path.write_text(json.dumps(run))
        self.assertIn("<p>approved</p>", self.m.gallery(self.root, "test-run", style=style).read_text())
        (self.m.run_dir(self.root, "test-run") / run["previews"][0]["path"]).write_bytes(b"tampered")
        content = self.m.gallery(self.root, "test-run", style=style).read_text()
        self.assertIn("<p>review invalid / pending</p>", content)
        self.assertNotIn("<p>approved</p>", content)
        self.assertIn('width="900" height="900"', content)

        review = run["previews"][0]["human_review"]
        review.update(
            reviewer="github:test-human", reviewed_at="2026-09-13T02:00:00Z",
            confirmation=self.m.confirmation(style), public_use_approved=True,
            preview_sha256="0" * 64,
        )
        path.write_text(json.dumps(run))
        content = self.m.gallery(self.root, "test-run", style=style).read_text()
        self.assertIn("<p>review invalid / pending</p>", content)
        self.assertNotIn("<p>approved</p>", content)

    def test_full_audit_reports_unapproved_styles_but_scoped_machine_audit_is_useful(self):
        run = self.ingest_all()
        findings = self.m.audit(self.root, "test-run")
        self.assertEqual(len(findings), 24)
        self.assertTrue(all("human review incomplete" in finding for finding in findings))
        style = run["previews"][0]["style"]
        self.assertEqual(self.m.audit(self.root, "test-run", style=style), [])
        self.assertEqual(
            self.m.audit(self.root, "test-run", style=style, require_approval=True),
            [f"{style}: human review incomplete"],
        )

    def test_review_template_requires_observed_geometry_and_explicit_label_checks(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        review = self.m.review_template(run, style)
        self.assertEqual(
            review["geometry"],
            {"cells": [None, None, None, None, None, None], "title": None, "subtitle": None, "footer": None},
        )
        self.assertTrue(all(value == "pending" for value in review["checks"].values()))
        self.assertTrue(all(cell["framing"] == "pending" for cell in review["cells"]))
        with self.assertRaisesRegex(ValueError, "human review incomplete"):
            self.m.approve(self.root, "test-run", style, review)

    def test_outfit_review_requires_every_core_item_in_all_six_cells(self):
        run = self.prepare()
        preview = run["previews"][0]
        ingested = self.m.ingest(
            self.root, "test-run", preview["style"], self.image(1), self.generation(preview, 1)
        )
        self.compose(ingested, preview["style"])
        current = self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")
        template = self.m.outfit_review_template(current, preview["style"])
        self.assertEqual(len(template["cells"]), 6)
        self.assertEqual(
            set(template["cells"][0]["core_items"]),
            {"blazer", "top", "jeans", "tote", "loafers"},
        )
        self.assertEqual(set(template["cells"][0]["optional_items"]), {"watch", "jewelry"})
        for replacement in (None, "pending", "fail", "not-visible-no-contradiction"):
            review = self.completed_review(current, preview["style"])
            if replacement is None:
                review["cells"][0]["core_items"].pop("blazer")
            else:
                review["cells"][0]["core_items"]["blazer"] = replacement
            with self.subTest(replacement=replacement):
                with self.assertRaisesRegex(ValueError, "human review incomplete"):
                    self.m.approve(self.root, "test-run", preview["style"], review)
        review = self.completed_review(current, preview["style"])
        review["cells"][0]["optional_items"]["watch"] = "pass"
        self.m.approve(self.root, "test-run", preview["style"], review)

    def test_review_rejects_bad_cell_shape_bounds_overlap_order_and_size(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        mutations = (
            lambda review: review["geometry"]["cells"][0].__setitem__(2, 200),
            lambda review: review["geometry"]["cells"][5].__setitem__(0, 800),
            lambda review: review["geometry"]["cells"][1].__setitem__(0, 200),
            lambda review: review["geometry"]["cells"][1].__setitem__(0, 50),
            lambda review: review["geometry"]["cells"][1].__setitem__(2, 207),
            lambda review: review["geometry"]["cells"][4].__setitem__(1, 424),
        )
        for mutate in mutations:
            review = self.completed_review(run, style)
            mutate(review)
            with self.subTest(geometry=review["geometry"]["cells"]):
                with self.assertRaisesRegex(ValueError, "observed geometry invalid"):
                    self.m.approve(self.root, "test-run", style, review)

    def test_review_rejects_malformed_coordinates_and_text_band_placement(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        mutations = (
            lambda review: review["geometry"]["cells"][0].__setitem__(0, True),
            lambda review: review["geometry"]["cells"][0].__setitem__(0, 90.0),
            lambda review: review["geometry"]["cells"][0].__setitem__(0, "90"),
            lambda review: review["geometry"]["cells"][0].__setitem__(2, 0),
            lambda review: review["geometry"].__setitem__("title", [60, 125, 780, 35]),
            lambda review: review["geometry"].__setitem__("subtitle", [60, 40, 780, 30]),
            lambda review: review["geometry"].__setitem__("footer", [90, 680, 720, 50]),
        )
        for mutate in mutations:
            review = self.completed_review(run, style)
            mutate(review)
            with self.subTest(geometry=review["geometry"]):
                with self.assertRaisesRegex(ValueError, "observed geometry invalid"):
                    self.m.approve(self.root, "test-run", style, review)

    def test_review_rejects_missing_pending_or_failed_text_and_framing_checks(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        mutations = (
            lambda review: review["checks"].pop("full_bilingual_title"),
            lambda review: review["checks"].update(correct_subtitle="pending"),
            lambda review: review["checks"].update(readable_ai_footer="fail"),
            lambda review: review["checks"].update(text_subject_non_overlap="pending"),
            lambda review: review["cells"][0].update(framing="pending"),
            lambda review: review["cells"][5].pop("framing"),
        )
        for mutate in mutations:
            review = self.completed_review(run, style)
            mutate(review)
            with self.subTest(review=review):
                with self.assertRaisesRegex(ValueError, "human review incomplete"):
                    self.m.approve(self.root, "test-run", style, review)

    def test_receipt_contract_binding_and_review_hash_tampering_fail_closed(self):
        run = self.ingest_all()
        preview = run["previews"][0]
        style = preview["style"]
        receipt_path = self.m.run_dir(self.root, "test-run") / "native-receipts" / f"{style}.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["bindings"]["layout_contract_sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt))
        self.assertIn("native receipt binding mismatch", " ".join(self.m.audit(self.root, "test-run", style=style)))
        receipt["bindings"]["layout_contract_sha256"] = self.m.object_hash(preview["layout_contract"])
        receipt_path.write_text(json.dumps(receipt))
        review = self.completed_review(run, style)
        review["evidence_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "human review incomplete"):
            self.m.approve(self.root, "test-run", style, review)

    def test_style_ingest_preserves_native_dimensions_and_requires_exact_receipt(self):
        run = self.prepare()
        preview = run["previews"][0]
        image = self.image(1)
        generation = self.generation(preview, 1)
        record = self.m.ingest(self.root, "test-run", preview["style"], image, generation)
        stored = record["previews"][0]
        self.assertEqual((stored["width"], stored["height"]), (900, 900))
        receipt = self.m.run_dir(self.root, "test-run") / "native-receipts" / f"{preview['style']}.json"
        receipt_record = json.loads(receipt.read_text())
        self.assertEqual(receipt_record["generation"], generation)
        self.assertEqual(receipt_record["native_dimensions"], [900, 900])
        self.assertEqual(
            set(receipt_record["bindings"]),
            {"style", "source_sha256", "rules_sha256", "pack_sha256", "prompt_sha256", "layout_contract_sha256", "label_contract_sha256"},
        )
        self.assertEqual(self.m.ingest(self.root, "test-run", preview["style"], image, generation), record)
        bad = dict(generation, prompt_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "generation prompt mismatch"):
            self.m.ingest(self.root, "test-run", run["previews"][1]["style"], self.image(2), bad)

    def test_correction_ingest_binds_replaced_asset_and_actual_prompt(self):
        run = self.prepare()
        preview = run["previews"][0]
        correction_prompt = "1" * 64
        generation = self.generation(preview, 1)
        generation["prompt_sha256"] = correction_prompt
        generation["authorization_sha256"] = "2" * 64
        correction = {
            "kind": "targeted-correction",
            "reason_code": "maintainer-requested-visual-fix",
            "generation_prompt_sha256": correction_prompt,
            "generation_authorization_sha256": "2" * 64,
            "visual_acceptance_sha256": "3" * 64,
            "replaces": {
                "call_id": "replaced-call-1",
                "original_sha256": "4" * 64,
                "native_sha256": "5" * 64,
                "display_sha256": "6" * 64,
            },
        }
        record = self.m.ingest(
            self.root,
            "test-run",
            preview["style"],
            self.image(1),
            generation,
            correction=correction,
        )
        stored = record["previews"][0]
        self.assertEqual(stored["correction"], correction)
        self.assertEqual(stored["generation"], generation)
        receipt = self.m.read_json(
            self.m.run_dir(self.root, "test-run") / "native-receipts" / f"{preview['style']}.json"
        )
        self.assertEqual(receipt["bindings"]["correction_sha256"], self.m.object_hash(correction))
        self.assertEqual(receipt["bindings"]["generation_prompt_sha256"], correction_prompt)
        record = self.compose(record, preview["style"])
        current = self.m.read_json(self.m.run_dir(self.root, "test-run") / "evidence.json")
        review = self.completed_review(current, preview["style"])
        self.m.approve(self.root, "test-run", preview["style"], review)
        self.assertEqual(self.m.audit(self.root, "test-run", style=preview["style"], require_approval=True), [])

        second = run["previews"][1]
        bad = copy.deepcopy(correction)
        bad["generation_prompt_sha256"] = "7" * 64
        with self.assertRaisesRegex(ValueError, "generation prompt mismatch"):
            self.m.ingest(
                self.root,
                "test-run",
                second["style"],
                self.image(2),
                dict(generation, call_id="test-call-2"),
                correction=bad,
            )

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

    def test_source_binding_and_incomplete_whole_sheet_review_fail_closed(self):
        run = self.ingest_all()
        path = self.m.run_dir(self.root, "test-run") / "evidence.json"
        changed = copy.deepcopy(run)
        changed["source"]["rights_sha256"] = "0" * 64
        path.write_text(json.dumps(changed))
        self.assertTrue(self.m.audit(self.root, "test-run"))
        path.write_text(json.dumps(run))
        style = run["previews"][0]["style"]
        review = self.completed_review(run, style)
        review["cells"][5]["pose_layout"] = "pending"
        with self.assertRaisesRegex(ValueError, "human review incomplete"):
            self.m.approve(self.root, "test-run", style, review)

    def test_approved_24_sheet_promotion_is_publicly_verifiable_and_idempotent(self):
        self.approve_all()
        readme = self.root / 'README.md'
        chinese_readme = self.root / 'README.zh-CN.md'
        initial_readme = '# Fixture\n<!-- STYLE_PREVIEWS:START -->\nPending\n<!-- STYLE_PREVIEWS:END -->\n'
        readme.write_text(initial_readme)
        chinese_readme.write_text('Missing markers')
        index_path = self.root / "docs/demo/style-index.json"
        original_index = index_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'README preview markers'):
            self.m.promote(self.root, 'test-run')
        self.assertEqual(readme.read_text(), initial_readme)
        self.assertEqual(index_path.read_bytes(), original_index)
        self.assertFalse((self.root / 'docs/demo/style-previews/test-run').exists())
        chinese_readme.write_text(initial_readme)
        broken_index = json.loads(original_index)
        broken_index["styles"].pop()
        index_path.write_text(json.dumps(broken_index))
        with self.assertRaisesRegex(ValueError, "style index and approved previews differ"):
            self.m.promote(self.root, "test-run")
        self.assertFalse((self.root / "docs/demo/style-previews/test-run").exists())
        index_path.write_bytes(original_index)
        public = self.m.promote(self.root, "test-run")
        self.assertEqual(self.m.validate_public_previews(self.root), [])
        self.assertEqual(self.m.promote(self.root, "test-run"), public)
        self.assertEqual(len(list(public.glob("*.jpg"))), 72)
        self.assertEqual(readme.read_text().count('-thumb.jpg'), 24)
        self.assertEqual(chinese_readme.read_text().count('-display.jpg'), 24)
        evidence = json.loads((public / "evidence.json").read_text())
        self.assertEqual(evidence["schema_version"], "5.0")
        rights = (self.root / 'docs/demo/RIGHTS.md').read_text()
        for asset in self.m.public_assets(evidence):
            self.assertIn(asset['role'], rights)
            self.assertIn(asset['path'], rights)
            self.assertIn(asset['sha256'][:12], rights)
        self.assertNotIn(str(self.root), (public / "evidence.json").read_text())
        index = json.loads((self.root / "docs/demo/style-index.json").read_text())
        self.assertEqual(sum(bool(style.get("preview")) for style in index["styles"]), 24)
        index["styles"][0]["preview"] = None
        (self.root / "docs/demo/style-index.json").write_text(json.dumps(index))
        self.assertTrue(self.m._primary().validate_style_index(self.root))
        self.assertEqual(self.m.promote(self.root, "test-run"), public)
        self.assertEqual(self.m._primary().validate_style_index(self.root), [])
        self.assertEqual(sum(style["status"] == "ready" for style in index["styles"]), 1)
        style_page = (self.root / "docs/demo/styles/old-money.md").read_text()
        for suffix in ('', '-display', '-thumb'):
            self.assertIn(f'(../style-previews/test-run/old-money{suffix}.jpg)', style_page)
        import demo_media
        self.assertEqual(demo_media.validate_public_cases(self.root), [])
        shutil.rmtree(self.root / ".threadtruth")
        self.assertEqual(self.m.validate_public_previews(self.root), [])
        (public / 'unregistered.jpg').write_bytes(b'orphan')
        self.assertTrue(self.m.validate_public_previews(self.root))
        (public / 'unregistered.jpg').unlink()
        next(public.glob("*.jpg")).write_bytes(b"tampered")
        self.assertTrue(self.m.validate_public_previews(self.root))

    def test_promotion_requires_all_24_unique_approved_sheets(self):
        run = self.ingest_all()
        style = run["previews"][0]["style"]
        review = self.completed_review(run, style)
        self.m.approve(self.root, "test-run", style, review)
        with self.assertRaisesRegex(ValueError, "unapproved styles"):
            self.m.promote(self.root, "test-run")

    def test_v1_is_read_only_and_cannot_be_promoted_or_migrated(self):
        self.m = module()
        directory = self.m.run_dir(self.root, "legacy")
        directory.mkdir(parents=True)
        Image.new("RGB", (600, 600), "gray").save(directory / "legacy.jpg")
        legacy = {
            "schema_version": "1.0", "run_id": "legacy", "status": "approved",
            "boards": [{"path": "legacy.jpg", "width": 600, "height": 600, "status": "machine-pass"}],
        }
        (directory / "evidence.json").write_text(json.dumps(legacy))
        before = (directory / "evidence.json").read_bytes()
        self.assertIn("superseded", " ".join(self.m.audit(self.root, "legacy")))
        content = self.m.gallery(self.root, "legacy").read_text()
        self.assertIn("Historical v1", content)
        self.assertIn("not approved for current standard", content)
        self.assertIn('<a href="legacy.jpg"><img src="legacy.jpg"', content)
        self.assertIn('name="viewport"', content)
        self.assertIn("white-space:pre-wrap;overflow-wrap:anywhere", content)
        self.assertIn("img{display:block;width:auto;max-width:100%;height:auto}", content)
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
