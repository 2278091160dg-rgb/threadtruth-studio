import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "primary_demo.py"


def load_module():
    if not MODULE_PATH.is_file():
        raise AssertionError("tools/primary_demo.py is missing")
    spec = importlib.util.spec_from_file_location("primary_demo", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def minimal_jpeg(width=750, height=900, marker=0):
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    comment = b"\xff\xfe\x00\x03" + bytes([marker % 256])
    dqt = b"\xff\xdb\x00\x43\x00" + bytes([1]) * 64
    sof = (
        b"\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )
    counts = bytes([1] + [0] * 15)
    dht = b"\xff\xc4\x00\x26" + b"\x00" + counts + b"\x00" + b"\x10" + counts + b"\x00"
    sos = b"\xff\xda\x00\x0c\x03\x01\x00\x02\x00\x03\x00\x00\x3f\x00"
    entropy = bytes(24000 + marker)
    return b"\xff\xd8" + app0 + comment + dqt + sof + dht + sos + entropy + b"\xff\xd9"


def minimal_png(width=1024, height=1536, color=0):
    def chunk(kind, payload):
        return (
            len(payload).to_bytes(4, "big")
            + kind
            + payload
            + zlib.crc32(kind + payload).to_bytes(4, "big")
        )

    raw_row = b"\x00" + bytes([color, color, color]) * width
    raw = raw_row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def write_staging(root, *, state="image-ready", ai_notice="informed"):
    staging = root / ".threadtruth" / "primary-demo" / "vest"
    (staging / "sources").mkdir(parents=True)
    (staging / "finals").mkdir()
    sources = []
    for index, name in enumerate(
        ("source-1-front.jpg", "source-2-detail.jpg", "source-3-zipper.jpg", "source-4-back.jpg"),
        start=1,
    ):
        data = minimal_jpeg(750, 870 + index, index)
        (staging / "sources" / name).write_bytes(data)
        sources.append({"role": f"source-{index}", "path": f"sources/{name}", "sha256": sha256(data)})
    outputs = []
    for index in range(1, 7):
        data = minimal_png(color=index)
        path = staging / "finals" / f"look-{index}.png"
        path.write_bytes(data)
        outputs.append(
            {
                "look": index,
                "path": f"finals/look-{index}.png",
                "sha256": sha256(data),
                "pixels": "1024x1536",
                "qa": "qa-pass",
                "user_review": "closed",
            }
        )
    (staging / "rights-declaration.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "work_id": "vest",
                "status": "user-approved-source-rights",
                "reviewer": "github:maintainer",
                "declared_at": "2026-09-12T17:01:47Z",
                "declaration": "I own or control the rights required for this public demo.",
                "public_use_authorized": True,
                "project_media_policy_accepted": True,
                "source_model_display_authorized": True,
                "sources": sources,
                "public_status": "not-promoted",
            }
        )
    )
    (staging / "final-run.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "work_id": "vest",
                "generated_at": "2026-09-12T17:34:53Z",
                "action": "six-independent-final-images",
                "style": "korean-cold-editorial",
                "mode": "B",
                "route": "B1",
                "output_form": "generic-adult-female-model",
                "state": state,
                "identity_anchor": "finals/look-1.png",
                "canvas_contract": {
                    "target_ratio": "2:3",
                    "target_orientation": "portrait",
                    "batch_canvas_baseline": "1024x1536",
                    "all_files_match": True,
                },
                "generation_calls": 6,
                "expected_images": 6,
                "actual_images": 6,
                "preview_images_included": 0,
                "outputs": outputs,
                "group_qa": {
                    "file_count": "pass",
                    "unique_hashes": "pass",
                    "canvas_ratio": "pass",
                    "pixel_consistency": "pass",
                    "identity_consistency": "pass",
                    "garment_hard_facts": "pass",
                    "requires_user_review": [],
                    "user_review_closure": {
                        "status": "closed",
                        "reviewer": "github:maintainer",
                        "reviewed_at": "2026-09-12T17:38:24Z",
                        "confirmation": "I reviewed looks 1 through 6 and approve image-ready.",
                    },
                },
                "ai_content_label_notice": {"status": ai_notice, "informed_at": "2026-09-12T17:38:24Z"},
                "public_status": "not-promoted",
            }
        )
    )
    (staging / "final-prompts.md").write_text("# Prompt set\n")
    return staging


class PrimaryDemoTests(unittest.TestCase):
    def test_default_image_backend_converts_and_composites_without_ffmpeg(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            inputs = []
            for index in range(7):
                path = root / f"input-{index}.png"
                path.write_bytes(minimal_png(120 + index, 180 + index, color=index))
                inputs.append(path)
            converted = root / "converted.jpg"
            hero = root / "hero.jpg"
            module.pillow_converter(inputs[0], converted)
            module.pillow_compositor(inputs, hero)
            self.assertEqual(module.jpeg_dimensions(converted.read_bytes()), (120, 180))
            self.assertEqual(module.jpeg_dimensions(hero.read_bytes()), (1280, 640))
            self.assertLess(hero.stat().st_size, 1024 * 1024)

    def test_staged_case_requires_image_ready_ai_notice_and_matching_hashes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staging = write_staging(root)
            self.assertEqual(module.validate_staged_primary_case(staging), [])

            run_path = staging / "final-run.json"
            run = json.loads(run_path.read_text())
            run["state"] = "image-draft"
            run_path.write_text(json.dumps(run))
            self.assertIn("PRIMARY_NOT_IMAGE_READY", module.validate_staged_primary_case(staging))

            run["state"] = "image-ready"
            run["ai_content_label_notice"]["status"] = "pending"
            run_path.write_text(json.dumps(run))
            self.assertIn("AI_LABEL_NOTICE_INCOMPLETE", module.validate_staged_primary_case(staging))

            run["ai_content_label_notice"]["status"] = "informed"
            run_path.write_text(json.dumps(run))
            (staging / "finals" / "look-2.png").write_bytes(minimal_png(color=99))
            self.assertIn("ASSET_HASH_MISMATCH", module.validate_staged_primary_case(staging))

    def test_promotion_writes_primary_rights_and_public_assets(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs" / "demo").mkdir(parents=True)
            staging = write_staging(root)
            counter = {"value": 0}

            def converter(_source, destination):
                counter["value"] += 1
                destination.write_bytes(minimal_jpeg(640, 960, counter["value"]))

            def compositor(_sources, destination):
                destination.write_bytes(minimal_jpeg(1280, 640, 77))

            rights = module.promote_primary_case(
                root,
                staging,
                "white-vest-korean-cold",
                promoted_at="2026-09-12T18:00:00Z",
                converter=converter,
                compositor=compositor,
            )
            case_dir = root / "docs" / "demo" / "primary-cases" / "white-vest-korean-cold"
            self.assertEqual(rights["role"], "primary")
            self.assertEqual(rights["primary_demo_status"], "ready")
            self.assertEqual(rights["style"], "korean-cold-editorial")
            self.assertEqual(len(rights["assets"]), 10)
            self.assertEqual(len(list(case_dir.glob("look-*.jpg"))), 6)
            self.assertEqual(len(list(case_dir.glob("source-*.jpg"))), 4)
            self.assertTrue((case_dir / "hero.jpg").is_file())
            self.assertEqual(module.validate_public_primary_cases(root), [])

            (case_dir / "look-3.jpg").write_bytes(b"tampered")
            self.assertTrue(
                any("hash" in finding for finding in module.validate_public_primary_cases(root))
            )

    def test_media_bundle_contains_exact_originals_and_no_preview(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staging = write_staging(root)
            output = root / "dist"
            archive, checksum = module.build_primary_media_bundle(
                staging, "white-vest-korean-cold", "1.0.0-beta.1", output
            )
            self.assertTrue(checksum.is_file())
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            self.assertEqual(sum(name.endswith(".png") for name in names), 6)
            self.assertEqual(sum("/sources/" in name for name in names), 4)
            self.assertFalse(any("generated-tests" in name or "preview" in name for name in names))
            self.assertTrue(any(name.endswith("SHA256SUMS") for name in names))

    def test_style_index_covers_every_pack_without_claiming_planned_images(self):
        module = load_module()
        self.assertEqual(module.validate_style_index(ROOT), [])
        self.assertEqual(module.validate_style_pages(ROOT), [])
        index = json.loads((ROOT / "docs" / "demo" / "style-index.json").read_text())
        self.assertEqual(len(index["styles"]), 24)
        self.assertEqual(sum(item["featured"] for item in index["styles"]), 8)
        ready = [item for item in index["styles"] if item["status"] == "ready"]
        self.assertEqual([item["slug"] for item in ready], ["korean-cold-editorial"])
        for item in index["styles"]:
            if item["status"] == "planned":
                self.assertIsNone(item["representative_image"])


if __name__ == "__main__":
    unittest.main()
