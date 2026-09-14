import importlib.util
import copy
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "demo_media.py"


def load_module():
    spec = importlib.util.spec_from_file_location("demo_media", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_jpeg(width=640, height=960):
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
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
    encoded_bits = ((width + 7) // 8) * ((height + 7) // 8) * 3 * 2
    whole_bytes, remaining_bits = divmod(encoded_bits, 8)
    entropy = bytearray(whole_bytes)
    if remaining_bits:
        entropy.append((1 << (8 - remaining_bits)) - 1)
    return b"\xff\xd8" + app0 + dqt + sof + dht + sos + bytes(entropy) + b"\xff\xd9"


def met_item(object_id=159228):
    return {
        "objectID": object_id,
        "isPublicDomain": True,
        "primaryImage": "https://images.metmuseum.org/CRDImages/ci/original/coat.jpg",
        "primaryImageSmall": "https://images.metmuseum.org/CRDImages/ci/web-large/coat.jpg",
        "objectURL": f"https://www.metmuseum.org/art/collection/search/{object_id}",
        "department": "Costume Institute",
        "objectName": "Coat",
        "title": "Coat",
        "culture": "American",
        "objectDate": "1880-89",
        "medium": "silk, metal",
        "creditLine": "Gift",
    }


class FakeMetClient:
    def __init__(self, object_ids, items, downloads):
        self.object_ids = object_ids
        self.items = items
        self.downloads = downloads
        self.search_calls = []
        self.object_calls = []
        self.download_calls = []

    def search(self, query, limit):
        self.search_calls.append((query, limit))
        return list(self.object_ids)[:limit], {"total": len(self.object_ids), "objectIDs": self.object_ids}

    def get_object(self, object_id):
        self.object_calls.append(object_id)
        return copy.deepcopy(self.items[object_id])

    def download_image(self, url):
        self.download_calls.append(url)
        result = self.downloads[url]
        if isinstance(result, Exception):
            raise result
        return result


class DemoMediaModuleTests(unittest.TestCase):
    def test_outfit_preview_source_is_demo_only_and_hash_bound(self):
        module = load_module()
        rights = json.loads(
            (ROOT / "docs/demo/preview-sources/beige-blazer-denim-outfit/rights.json").read_text()
        )
        self.assertEqual(rights["schema_version"], "1.0")
        self.assertEqual(rights["case_id"], "beige-blazer-denim-outfit")
        self.assertEqual(rights["license"]["id"], "ThreadTruth-Demo-Only-1.0")
        self.assertEqual(
            rights["original"]["sha256"],
            "40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a",
        )
        self.assertNotEqual(rights["license"]["id"], "CC0-1.0")
        self.assertIn("no standalone reuse, resale, relicensing or CC0 dedication", rights["license"]["scope"])
        self.assertEqual(module.validate_preview_sources(ROOT), [])

    def test_preview_source_validator_rejects_tampering_and_unregistered_files(self):
        module = load_module()
        mutations = (
            lambda root, rights: (root / rights["public_asset"]["path"]).write_bytes(b"changed"),
            lambda root, rights: rights["license"].update(id="CC0-1.0"),
            lambda root, rights: rights["public_asset"].update(path="/tmp/source.jpg"),
            lambda root, rights: rights["outfit"]["core_items"].pop(),
            lambda root, rights: (root / "unregistered.txt").write_text("orphan"),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    shutil.copytree(ROOT / "docs/demo", root / "docs/demo")
                    case = root / "docs/demo/preview-sources/beige-blazer-denim-outfit"
                    rights_path = case / "rights.json"
                    rights = json.loads(rights_path.read_text())
                    mutate(case, rights)
                    rights_path.write_text(json.dumps(rights))
                    self.assertTrue(module.validate_preview_sources(root))
    def test_combined_public_case_validation_accepts_primary_and_auxiliary_cases(self):
        module = load_module()
        self.assertEqual(module.validate_public_cases(ROOT), [])

    def create_audited_run(self, module, root, run_id="review-test"):
        item = met_item()
        client = FakeMetClient(
            [159228],
            {159228: item},
            {
                item["primaryImage"]: {
                    "data": minimal_jpeg(1200, 1600),
                    "content_type": "image/jpeg",
                    "final_url": item["primaryImage"],
                }
            },
        )
        module.search_run(
            root,
            "coat",
            1,
            client,
            now=datetime(2026, 9, 12, tzinfo=timezone.utc),
            run_id=run_id,
        )
        module.fetch_run(root, run_id, client, fetched_at="2026-09-12T00:01:00Z")
        module.audit_run(root, run_id, audited_at="2026-09-12T00:02:00Z")
        return client

    def test_development_module_exists_outside_runtime_skill(self):
        self.assertTrue((ROOT / "tools" / "demo_media.py").is_file())
        self.assertFalse((ROOT / "skills" / "threadtruth-studio" / "demo_media.py").exists())

    def test_state_machine_allows_only_forward_gated_transitions(self):
        module = load_module()
        for current, target in (
            ("discovered", "fetched"),
            ("fetched", "machine-passed"),
            ("machine-passed", "human-approved"),
            ("human-approved", "promoted"),
        ):
            module.validate_transition(current, target)
        for current, target in (
            ("discovered", "machine-passed"),
            ("human-approved", "fetched"),
            ("rights-rejected", "human-approved"),
            ("expired", "promoted"),
        ):
            with self.assertRaisesRegex(ValueError, "STATE_TRANSITION_INVALID"):
                module.validate_transition(current, target)

    def test_state_machine_allows_rejection_and_expiry_without_revival(self):
        module = load_module()
        for current in ("discovered", "fetched", "machine-passed", "human-approved"):
            module.validate_transition(current, "rights-rejected")
        for current in ("discovered", "fetched", "machine-passed", "rights-rejected"):
            module.validate_transition(current, "expired")
        for current in ("human-approved", "promoted", "expired"):
            with self.assertRaisesRegex(ValueError, "STATE_TRANSITION_INVALID"):
                module.validate_transition(current, "expired")

    def test_query_and_limit_contract(self):
        module = load_module()
        self.assertEqual(module.validate_query("  coat "), "coat")
        self.assertEqual(module.validate_limit(8), 8)
        for query in ("", "x" * 81):
            with self.assertRaises(ValueError):
                module.validate_query(query)
        for limit in (0, 13):
            with self.assertRaises(ValueError):
                module.validate_limit(limit)

    def test_jpeg_dimensions_and_hash_are_deterministic(self):
        module = load_module()
        data = minimal_jpeg(640, 960)
        self.assertEqual(module.jpeg_dimensions(data), (640, 960))
        self.assertEqual(module.sha256_bytes(data), module.sha256_bytes(data))
        self.assertEqual(len(module.sha256_bytes(data)), 64)

    def test_jpeg_parser_rejects_corrupt_or_png_data(self):
        module = load_module()
        complete = minimal_jpeg(1200, 1600)
        header_only = complete.split(b"\xff\xda", 1)[0] + b"\xff\xd9"
        sos_offset = complete.index(b"\xff\xda")
        sos_length = int.from_bytes(complete[sos_offset + 2 : sos_offset + 4], "big")
        scan_start = sos_offset + 2 + sos_length
        truncated_scan = complete[:scan_start] + b"\x00\xff\xd9"
        sof_start = complete.index(b"\xff\xc0")
        sof_end = sof_start + 2 + int.from_bytes(
            complete[sof_start + 2 : sof_start + 4], "big"
        )
        empty_tables_and_scan = (
            b"\xff\xd8"
            + complete[2 : complete.index(b"\xff\xdb")]
            + b"\xff\xdb\x00\x02"
            + complete[sof_start:sof_end]
            + b"\xff\xc4\x00\x02"
            + b"\xff\xda\x00\x02"
            + bytes(23000)
            + b"\xff\xd9"
        )
        for data in (
            b"",
            b"not-an-image",
            b"\x89PNG\r\n\x1a\n",
            header_only,
            truncated_scan,
            empty_tables_and_scan,
        ):
            with self.assertRaisesRegex(ValueError, "IMAGE_CORRUPT"):
                module.jpeg_dimensions(data)

    def test_metadata_audit_accepts_only_costume_institute_public_domain_images(self):
        module = load_module()
        self.assertEqual(module.metadata_rejection_codes(159228, met_item()), [])

        mutations = {
            "METADATA_NOT_PUBLIC_DOMAIN": {"isPublicDomain": False},
            "MISSING_PRIMARY_IMAGE": {"primaryImage": ""},
            "WRONG_DEPARTMENT": {"department": "Islamic Art"},
            "UNTRUSTED_HOST": {"primaryImage": "https://example.com/coat.jpg"},
            "OBJECT_ID_MISMATCH": {"objectID": 999},
            "EVIDENCE_INCOMPLETE": {"objectURL": ""},
        }
        for expected, changes in mutations.items():
            item = met_item()
            item.update(changes)
            self.assertIn(expected, module.metadata_rejection_codes(159228, item))

    def test_candidate_record_captures_cc0_and_raw_metadata_digest(self):
        module = load_module()
        item = met_item()
        record = module.candidate_from_metadata(159228, item, "2026-09-12T00:00:00Z")
        self.assertEqual(record["schema_version"], "1.0")
        self.assertEqual(record["candidate_id"], "met-159228")
        self.assertEqual(record["state"], "discovered")
        self.assertEqual(record["license"]["id"], "CC0-1.0")
        self.assertEqual(len(record["source"]["raw_metadata_sha256"]), 64)
        self.assertEqual(record["human_review"]["decision"], "pending")

        rejected_item = met_item()
        rejected_item["isPublicDomain"] = False
        rejected = module.candidate_from_metadata(
            159228, rejected_item, "2026-09-12T00:00:00Z"
        )
        self.assertIsNone(rejected["license"]["id"])
        self.assertIn(
            "METADATA_NOT_PUBLIC_DOMAIN", rejected["machine_audit"]["reason_codes"]
        )

    def test_image_audit_records_evidence_and_rejects_bad_inputs(self):
        module = load_module()
        record = module.candidate_from_metadata(159228, met_item(), "2026-09-12T00:00:00Z")
        passed = module.audit_download(
            copy.deepcopy(record),
            minimal_jpeg(1200, 1600),
            "image/jpeg",
            seen_hashes=set(),
        )
        self.assertEqual(passed["state"], "machine-passed")
        self.assertEqual(passed["machine_audit"]["decision"], "pass")
        self.assertEqual(passed["asset"]["width"], 1200)
        self.assertEqual(passed["asset"]["height"], 1600)

        cases = (
            ("DOWNLOAD_TYPE_INVALID", minimal_jpeg(1200, 1600), "image/png", set()),
            ("IMAGE_CORRUPT", b"bad", "image/jpeg", set()),
            ("IMAGE_TOO_SMALL", minimal_jpeg(300, 400), "image/jpeg", set()),
        )
        for expected, data, content_type, seen in cases:
            rejected = module.audit_download(
                copy.deepcopy(record), data, content_type, seen_hashes=seen
            )
            self.assertEqual(rejected["state"], "rights-rejected")
            self.assertIn(expected, rejected["machine_audit"]["reason_codes"])

        duplicate_data = minimal_jpeg(1200, 1600)
        rejected = module.audit_download(
            copy.deepcopy(record),
            duplicate_data,
            "image/jpeg",
            seen_hashes={module.sha256_bytes(duplicate_data)},
        )
        self.assertIn("DUPLICATE_HASH", rejected["machine_audit"]["reason_codes"])

    def test_search_fetch_and_audit_are_separate_persisted_stages(self):
        module = load_module()
        good = met_item(159228)
        bad = met_item(999)
        bad["isPublicDomain"] = False
        downloads = {
            good["primaryImage"]: {
                "data": minimal_jpeg(1200, 1600),
                "content_type": "image/jpeg",
                "final_url": good["primaryImage"],
            }
        }
        client = FakeMetClient([159228, 999], {159228: good, 999: bad}, downloads)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            now = datetime(2026, 9, 12, tzinfo=timezone.utc)
            run_id = module.search_run(
                root, "coat", 8, client, now=now, run_id="20260912T000000Z-coat"
            )
            run_dir = root / ".threadtruth" / "demo-candidates" / run_id
            run = json.loads((run_dir / "run.json").read_text())
            self.assertEqual(run["state"], "discovered")
            self.assertEqual(run["expires_at"], "2026-09-19T00:00:00Z")
            self.assertEqual(client.download_calls, [])
            self.assertEqual(
                run["search_response_sha256"],
                module.sha256_bytes((run_dir / "raw" / "search.json").read_bytes()),
            )

            module.fetch_run(root, run_id, client, fetched_at="2026-09-12T00:01:00Z")
            good_record = json.loads(
                (run_dir / "candidates" / "met-159228.json").read_text()
            )
            bad_record = json.loads(
                (run_dir / "candidates" / "met-999.json").read_text()
            )
            self.assertEqual(good_record["state"], "fetched")
            self.assertEqual(
                good_record["source"]["raw_metadata_sha256"],
                module.sha256_bytes((run_dir / "raw" / "met-159228.json").read_bytes()),
            )
            self.assertEqual(bad_record["state"], "rights-rejected")
            self.assertIn(
                "METADATA_NOT_PUBLIC_DOMAIN",
                bad_record["machine_audit"]["reason_codes"],
            )
            self.assertEqual(len(client.download_calls), 1)

            module.audit_run(root, run_id, audited_at="2026-09-12T00:02:00Z")
            good_record = json.loads(
                (run_dir / "candidates" / "met-159228.json").read_text()
            )
            self.assertEqual(good_record["state"], "machine-passed")
            self.assertEqual(good_record["machine_audit"]["decision"], "pass")
            self.assertEqual(json.loads((run_dir / "run.json").read_text())["state"], "machine-passed")

    def test_fetch_rejects_untrusted_redirect_without_writing_image(self):
        module = load_module()
        item = met_item()
        client = FakeMetClient(
            [159228],
            {159228: item},
            {
                item["primaryImage"]: {
                    "data": minimal_jpeg(1200, 1600),
                    "content_type": "image/jpeg",
                    "final_url": "https://example.com/redirected.jpg",
                }
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_id = module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 12, tzinfo=timezone.utc),
                run_id="redirect-test",
            )
            module.fetch_run(root, run_id, client, fetched_at="2026-09-12T00:01:00Z")
            run_dir = root / ".threadtruth" / "demo-candidates" / run_id
            record = json.loads(
                (run_dir / "candidates" / "met-159228.json").read_text()
            )
            self.assertEqual(record["state"], "rights-rejected")
            self.assertIn("UNTRUSTED_HOST", record["machine_audit"]["reason_codes"])
            self.assertFalse((run_dir / "images" / "met-159228.jpg").exists())

    def test_fetch_rejects_cross_host_redirect_even_when_both_hosts_are_allowed(self):
        module = load_module()
        item = met_item()
        client = FakeMetClient(
            [159228],
            {159228: item},
            {
                item["primaryImage"]: {
                    "data": minimal_jpeg(1200, 1600),
                    "content_type": "image/jpeg",
                    "final_url": "https://collectionapi.metmuseum.org/redirected.jpg",
                }
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_id = module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 12, tzinfo=timezone.utc),
                run_id="cross-host-test",
            )
            module.fetch_run(root, run_id, client, fetched_at="2026-09-12T00:01:00Z")
            record = json.loads(
                (
                    root
                    / ".threadtruth"
                    / "demo-candidates"
                    / run_id
                    / "candidates"
                    / "met-159228.json"
                ).read_text()
            )
            self.assertEqual(record["state"], "rights-rejected")
            self.assertIn("UNTRUSTED_HOST", record["machine_audit"]["reason_codes"])

    def test_run_and_candidate_identifiers_cannot_escape_workspace(self):
        module = load_module()
        for value in ("../escape", "/absolute", "with space", ""):
            with self.assertRaises(ValueError):
                module.validate_identifier(value)

    def test_gallery_is_offline_and_uses_only_relative_image_sources(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_audited_run(module, root)
            gallery = module.generate_gallery(root, "review-test")
            text = gallery.read_text()
            self.assertIn("met-159228", text)
            self.assertIn("Costume Institute", text)
            self.assertIn("--no-person --no-logo --no-watermark", text)
            self.assertIn("reject --run review-test", text)
            self.assertIn(module.CC0_URL, text)
            self.assertNotRegex(text, r'<img[^>]+src=["\']https?://')
            self.assertNotRegex(text, r'<(?:script|link)[^>]+https?://')
            self.assertNotIn(str(root), text)

    def test_approval_requires_complete_visual_review_and_exact_confirmation(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_audited_run(module, root)
            checks = {
                "no_person": True,
                "no_logo": True,
                "no_watermark": True,
                "physical_garment": True,
                "not_sensitive": True,
            }
            record = module.approve_candidate(
                root,
                "review-test",
                "met-159228",
                reviewer="github:2278091160dg-rgb",
                checks=checks,
                confirmation=module.APPROVAL_CONFIRMATION,
                reviewed_at="2026-09-12T01:00:00Z",
            )
            self.assertEqual(record["state"], "human-approved")
            self.assertEqual(record["human_review"]["decision"], "approved")
            run = json.loads(
                (
                    root
                    / ".threadtruth"
                    / "demo-candidates"
                    / "review-test"
                    / "run.json"
                ).read_text()
            )
            self.assertEqual(run["approved_candidates"], ["met-159228"])

            for index, (broken_checks, confirmation) in enumerate(
                (
                    ({**checks, "no_logo": False}, module.APPROVAL_CONFIRMATION),
                    (checks, "yes"),
                )
            ):
                broken_run = f"broken-review-{index}"
                self.create_audited_run(module, root, run_id=broken_run)
                with self.assertRaisesRegex(ValueError, "HUMAN_REVIEW_INCOMPLETE"):
                    module.approve_candidate(
                        root,
                        broken_run,
                        "met-159228",
                        reviewer="github:2278091160dg-rgb",
                        checks=broken_checks,
                        confirmation=confirmation,
                        reviewed_at="2026-09-12T01:00:00Z",
                    )

            broken_time = copy.deepcopy(record)
            broken_time["human_review"]["reviewed_at"] = None
            self.assertIn(
                "HUMAN_REVIEW_INCOMPLETE",
                module.validate_human_approval(broken_time),
            )

            placeholder = copy.deepcopy(record)
            placeholder["human_review"]["reviewer"] = "github:YOUR-HANDLE"
            self.assertIn(
                "HUMAN_REVIEW_INCOMPLETE",
                module.validate_human_approval(placeholder),
            )

            early_run = "early-review"
            self.create_audited_run(module, root, run_id=early_run)
            with self.assertRaisesRegex(ValueError, "predates"):
                module.approve_candidate(
                    root,
                    early_run,
                    "met-159228",
                    reviewer="github:2278091160dg-rgb",
                    checks=checks,
                    confirmation=module.APPROVAL_CONFIRMATION,
                    reviewed_at="2026-09-11T23:59:59Z",
                )

    def test_human_rejection_uses_known_reason_and_is_terminal(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_audited_run(module, root)
            record = module.reject_candidate(
                root,
                "review-test",
                "met-159228",
                reason="LOGO_OR_TRADEMARK",
                reviewer="github:2278091160dg-rgb",
                reviewed_at="2026-09-12T01:00:00Z",
            )
            self.assertEqual(record["state"], "rights-rejected")
            self.assertEqual(record["human_review"]["decision"], "rejected")
            with self.assertRaises(ValueError):
                module.reject_candidate(
                    root,
                    "review-test",
                    "met-159228",
                    reason="NOT_A_REAL_CODE",
                    reviewer="github:2278091160dg-rgb",
                    reviewed_at="2026-09-12T01:01:00Z",
                )

    def test_expired_approved_candidate_can_be_rejected_then_pruned(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.approve_test_candidate(module, root, run_id="approved-expired")
            record = module.reject_candidate(
                root,
                "approved-expired",
                "met-159228",
                reason="CULTURAL_OR_SENSITIVE_CONTEXT",
                reviewer="github:2278091160dg-rgb",
                reviewed_at="2026-09-20T00:00:00Z",
            )
            self.assertEqual(record["state"], "rights-rejected")
            removed = module.prune_expired_runs(
                root, now=datetime(2026, 9, 20, tzinfo=timezone.utc)
            )
            self.assertEqual(removed, ["approved-expired"])

            rejected_run = "invalid-reviewer"
            self.create_audited_run(module, root, run_id=rejected_run)
            with self.assertRaisesRegex(ValueError, "HUMAN_REVIEW_INCOMPLETE"):
                module.reject_candidate(
                    root,
                    rejected_run,
                    "met-159228",
                    reason="LOGO_OR_TRADEMARK",
                    reviewer="private email",
                    reviewed_at="2026-09-12T01:01:00Z",
                )

    def approve_test_candidate(self, module, root, run_id="promote-test"):
        client = self.create_audited_run(module, root, run_id=run_id)
        module.approve_candidate(
            root,
            run_id,
            "met-159228",
            reviewer="github:2278091160dg-rgb",
            checks={name: True for name in module.REVIEW_CHECKS},
            confirmation=module.APPROVAL_CONFIRMATION,
            reviewed_at="2026-09-12T01:00:00Z",
        )
        return client

    def test_promote_revalidates_metadata_and_writes_public_cc0_case(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root)
            result = module.promote_candidate(
                root,
                "promote-test",
                "met-159228",
                "met-coat-159228",
                client,
                promoted_at="2026-09-12T02:00:00Z",
            )
            case_dir = root / "docs" / "demo" / "cases" / "met-coat-159228"
            self.assertEqual(result["status"], "promoted")
            self.assertEqual(result["role"], "auxiliary")
            self.assertEqual(result["media_license"]["id"], "CC0-1.0")
            self.assertNotIn("note", result["human_review"])
            self.assertTrue((case_dir / "source.jpg").is_file())
            self.assertTrue((case_dir / "source-metadata.json").is_file())
            self.assertTrue((case_dir / "rights.json").is_file())
            self.assertEqual(
                result["source"]["metadata_sha256_at_promotion"],
                module.sha256_bytes((case_dir / "source-metadata.json").read_bytes()),
            )
            case_readme = (case_dir / "README.md").read_text()
            self.assertIn("not endorsed by The Metropolitan Museum of Art", case_readme)
            self.assertNotIn("Primary maintainer-owned demo remains", case_readme)
            rights_index = (root / "docs" / "demo" / "RIGHTS.md").read_text()
            self.assertIn("met-coat-159228", rights_index)
            self.assertIn("Primary maintainer-owned demo remains `sample-blocked`", rights_index)
            self.assertEqual(module.validate_public_cases(root), [])

            repeated = module.promote_candidate(
                root,
                "promote-test",
                "met-159228",
                "met-coat-159228",
                client,
                promoted_at="2026-09-12T02:01:00Z",
            )
            self.assertEqual(repeated["asset"]["sha256"], result["asset"]["sha256"])

            record_path = (
                root
                / ".threadtruth"
                / "demo-candidates"
                / "promote-test"
                / "candidates"
                / "met-159228.json"
            )
            run_path = record_path.parents[1] / "run.json"
            recovered_record = json.loads(record_path.read_text())
            recovered_record["state"] = "human-approved"
            record_path.write_text(json.dumps(recovered_record))
            recovered_run = json.loads(run_path.read_text())
            recovered_run["state"] = "human-approved"
            run_path.write_text(json.dumps(recovered_run))
            (root / "docs" / "demo" / "RIGHTS.md").write_text("stale")
            module.promote_candidate(
                root,
                "promote-test",
                "met-159228",
                "met-coat-159228",
                client,
                promoted_at="2026-09-12T02:02:00Z",
            )
            self.assertEqual(json.loads(record_path.read_text())["state"], "promoted")
            self.assertEqual(json.loads(run_path.read_text())["promoted_cases"], ["met-coat-159228"])
            self.assertIn(
                "met-coat-159228", (root / "docs" / "demo" / "RIGHTS.md").read_text()
            )

    def test_promote_fails_closed_on_metadata_drift_or_missing_approval(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root, run_id="drift-test")
            client.items[159228]["isPublicDomain"] = False
            with self.assertRaisesRegex(ValueError, "SOURCE_METADATA_CHANGED"):
                module.promote_candidate(
                    root,
                    "drift-test",
                    "met-159228",
                    "drift-case",
                    client,
                    promoted_at="2026-09-12T02:00:00Z",
                )

    def test_promote_rejects_candidate_object_id_mismatch(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root, run_id="id-mismatch")
            record_path = (
                root
                / ".threadtruth"
                / "demo-candidates"
                / "id-mismatch"
                / "candidates"
                / "met-159228.json"
            )
            record = json.loads(record_path.read_text())
            record["candidate_id"] = "met-999"
            record_path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "OBJECT_ID_MISMATCH"):
                module.promote_candidate(
                    root,
                    "id-mismatch",
                    "met-159228",
                    "mismatched-case",
                    client,
                    promoted_at="2026-09-12T02:00:00Z",
                )

    def test_promote_rejects_tampered_discovery_metadata_file(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root, run_id="raw-tamper")
            raw_path = (
                root
                / ".threadtruth"
                / "demo-candidates"
                / "raw-tamper"
                / "raw"
                / "met-159228.json"
            )
            raw_path.write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "EVIDENCE_INCOMPLETE"):
                module.promote_candidate(
                    root,
                    "raw-tamper",
                    "met-159228",
                    "tampered-raw-case",
                    client,
                    promoted_at="2026-09-12T02:00:00Z",
                )

    def test_public_case_validator_checks_size_limit_and_jpeg_structure(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root)
            module.promote_candidate(
                root,
                "promote-test",
                "met-159228",
                "met-coat-159228",
                client,
                promoted_at="2026-09-12T02:00:00Z",
            )
            case_dir = root / "docs" / "demo" / "cases" / "met-coat-159228"
            tiny = minimal_jpeg(100, 100)
            (case_dir / "source.jpg").write_bytes(tiny)
            rights_path = case_dir / "rights.json"
            rights = json.loads(rights_path.read_text())
            rights["asset"].update(
                {
                    "sha256": module.sha256_bytes(tiny),
                    "bytes": len(tiny),
                    "width": 100,
                    "height": 100,
                }
            )
            rights_path.write_text(json.dumps(rights))
            module.render_rights_index(root)
            findings = module.validate_public_cases(root)
            self.assertTrue(any("too small" in finding.lower() for finding in findings))
            self.assertFalse((root / "docs" / "demo" / "cases" / "drift-case").exists())

            self.create_audited_run(module, root, run_id="unapproved-test")
            with self.assertRaisesRegex(ValueError, "HUMAN_REVIEW_INCOMPLETE"):
                module.promote_candidate(
                    root,
                    "unapproved-test",
                    "met-159228",
                    "unapproved-case",
                    client,
                    promoted_at="2026-09-12T02:00:00Z",
                )

    def test_public_case_validator_detects_hash_and_license_tampering(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root)
            module.promote_candidate(
                root,
                "promote-test",
                "met-159228",
                "met-coat-159228",
                client,
                promoted_at="2026-09-12T02:00:00Z",
            )
            case_dir = root / "docs" / "demo" / "cases" / "met-coat-159228"
            (case_dir / "source.jpg").write_bytes(b"tampered")
            findings = module.validate_public_cases(root)
            self.assertTrue(any("hash" in finding.lower() for finding in findings))

            rights = json.loads((case_dir / "rights.json").read_text())
            rights["media_license"]["id"] = "CC-BY-4.0"
            (case_dir / "rights.json").write_text(json.dumps(rights))
            findings = module.validate_public_cases(root)
            self.assertTrue(any("CC0" in finding for finding in findings))

    def test_public_case_validator_detects_review_metadata_and_index_drift(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            client = self.approve_test_candidate(module, root)
            module.promote_candidate(
                root,
                "promote-test",
                "met-159228",
                "met-coat-159228",
                client,
                promoted_at="2026-09-12T02:00:00Z",
            )
            case_dir = root / "docs" / "demo" / "cases" / "met-coat-159228"
            rights_path = case_dir / "rights.json"
            rights = json.loads(rights_path.read_text())
            rights["human_review"]["checks"]["no_logo"] = False
            rights["human_review"]["reviewed_at"] = "2026-09-13T00:00:00Z"
            rights["source"]["metadata_sha256_at_promotion"] = "0" * 64
            rights_path.write_text(json.dumps(rights))
            (root / "docs" / "demo" / "RIGHTS.md").write_text("stale index")
            findings = module.validate_public_cases(root)
            self.assertTrue(any("human review" in finding.lower() for finding in findings))
            self.assertTrue(any("metadata hash" in finding.lower() for finding in findings))
            self.assertTrue(any("postdates promotion" in finding.lower() for finding in findings))
            self.assertTrue(any("rights index" in finding.lower() for finding in findings))

    def test_audit_rejects_candidate_image_path_escape(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_audited_run(module, root, run_id="path-source")
            client = FakeMetClient([], {}, {})
            module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 12, tzinfo=timezone.utc),
                run_id="path-test",
            )
            run_dir = root / ".threadtruth" / "demo-candidates" / "path-test"
            run = json.loads((run_dir / "run.json").read_text())
            run["state"] = "fetched"
            (run_dir / "run.json").write_text(json.dumps(run))
            record = module.candidate_from_metadata(
                159228, met_item(), "2026-09-12T00:01:00Z"
            )
            record["state"] = "fetched"
            escaped_data = minimal_jpeg(1200, 1600)
            record["asset"] = {
                "relative_path": "../path-source/images/met-159228.jpg",
                "sha256": module.sha256_bytes(escaped_data),
                "mime": "image/jpeg",
                "bytes": len(escaped_data),
                "width": None,
                "height": None,
                "final_url": met_item()["primaryImage"],
            }
            candidate_dir = run_dir / "candidates"
            candidate_dir.mkdir(parents=True)
            (candidate_dir / "met-159228.json").write_text(json.dumps(record))
            module.audit_run(root, "path-test", audited_at="2026-09-12T00:02:00Z")
            audited = json.loads((candidate_dir / "met-159228.json").read_text())
            self.assertEqual(audited["state"], "rights-rejected")
            self.assertIn("EVIDENCE_INCOMPLETE", audited["machine_audit"]["reason_codes"])

    def test_cli_parser_exposes_every_governed_stage(self):
        module = load_module()
        parser = module.build_parser()
        commands = (
            ["search", "--query", "coat"],
            ["fetch", "--run", "run-1"],
            ["audit", "--run", "run-1"],
            ["gallery", "--run", "run-1"],
            [
                "approve",
                "--run",
                "run-1",
                "--candidate",
                "met-1",
                "--reviewer",
                "github:2278091160dg-rgb",
                "--no-person",
                "--no-logo",
                "--no-watermark",
                "--physical-garment",
                "--not-sensitive",
                "--confirm",
                module.APPROVAL_CONFIRMATION,
            ],
            [
                "reject",
                "--run",
                "run-1",
                "--candidate",
                "met-1",
                "--reason",
                "LOGO_OR_TRADEMARK",
                "--reviewer",
                "github:2278091160dg-rgb",
            ],
            [
                "promote",
                "--run",
                "run-1",
                "--candidate",
                "met-1",
                "--case-id",
                "case-1",
            ],
            ["prune", "--expired"],
        )
        self.assertEqual(
            [parser.parse_args(command).command for command in commands],
            [command[0] for command in commands],
        )
        self.assertTrue((ROOT / "tools" / "demo-media.py").is_file())

    def test_redirect_validation_requires_same_trusted_https_host(self):
        module = load_module()
        module.validate_redirect(
            "https://images.metmuseum.org/original/a.jpg",
            "https://images.metmuseum.org/original/b.jpg",
        )
        for target in (
            "http://images.metmuseum.org/original/a.jpg",
            "https://collectionapi.metmuseum.org/original/a.jpg",
            "https://example.com/a.jpg",
            "https://images.metmuseum.org:444/original/a.jpg",
        ):
            with self.assertRaisesRegex(ValueError, "UNTRUSTED_HOST"):
                module.validate_redirect(
                    "https://images.metmuseum.org/original/a.jpg", target
                )

    def test_expiry_is_enforced_at_the_exact_boundary(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_audited_run(module, root, run_id="expiry-test")
            with self.assertRaisesRegex(ValueError, "RUN_EXPIRED"):
                module.approve_candidate(
                    root,
                    "expiry-test",
                    "met-159228",
                    reviewer="github:2278091160dg-rgb",
                    checks={name: True for name in module.REVIEW_CHECKS},
                    confirmation=module.APPROVAL_CONFIRMATION,
                    reviewed_at="2026-09-19T00:00:00Z",
                )

    def test_fetch_and_audit_refuse_expired_runs(self):
        module = load_module()
        item = met_item()
        client = FakeMetClient(
            [159228],
            {159228: item},
            {
                item["primaryImage"]: {
                    "data": minimal_jpeg(1200, 1600),
                    "content_type": "image/jpeg",
                    "final_url": item["primaryImage"],
                }
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 12, tzinfo=timezone.utc),
                run_id="expired-fetch",
            )
            with self.assertRaisesRegex(ValueError, "RUN_EXPIRED"):
                module.fetch_run(
                    root,
                    "expired-fetch",
                    client,
                    fetched_at="2026-09-19T00:00:00Z",
                )

            module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 12, tzinfo=timezone.utc),
                run_id="expired-audit",
            )
            module.fetch_run(
                root,
                "expired-audit",
                client,
                fetched_at="2026-09-12T00:01:00Z",
            )
            with self.assertRaisesRegex(ValueError, "RUN_EXPIRED"):
                module.audit_run(
                    root,
                    "expired-audit",
                    audited_at="2026-09-19T00:00:00Z",
                )

    def test_fetch_turns_download_policy_errors_into_candidate_rejections(self):
        module = load_module()
        item = met_item()
        client = FakeMetClient(
            [159228],
            {159228: item},
            {item["primaryImage"]: ValueError("DOWNLOAD_TOO_LARGE: response exceeded limit")},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_id = module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 12, tzinfo=timezone.utc),
                run_id="oversize-test",
            )
            module.fetch_run(root, run_id, client, fetched_at="2026-09-12T00:01:00Z")
            record = json.loads(
                (
                    root
                    / ".threadtruth"
                    / "demo-candidates"
                    / run_id
                    / "candidates"
                    / "met-159228.json"
                ).read_text()
            )
            self.assertEqual(record["state"], "rights-rejected")
            self.assertIn("DOWNLOAD_TOO_LARGE", record["machine_audit"]["reason_codes"])

    def test_prune_removes_only_expired_unapproved_runs(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.create_audited_run(module, root, run_id="expired-run")
            self.approve_test_candidate(module, root, run_id="approved-run")
            client = FakeMetClient([], {}, {})
            module.search_run(
                root,
                "coat",
                1,
                client,
                now=datetime(2026, 9, 20, tzinfo=timezone.utc),
                run_id="fresh-run",
            )
            removed = module.prune_expired_runs(
                root, now=datetime(2026, 9, 20, tzinfo=timezone.utc)
            )
            self.assertEqual(removed, ["expired-run"])
            base = root / ".threadtruth" / "demo-candidates"
            self.assertFalse((base / "expired-run").exists())
            self.assertTrue((base / "approved-run").exists())
            self.assertTrue((base / "fresh-run").exists())


if __name__ == "__main__":
    unittest.main()
