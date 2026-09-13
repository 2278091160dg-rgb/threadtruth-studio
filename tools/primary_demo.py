#!/usr/bin/env python3
"""Promote a rights-cleared, image-ready primary demo into public artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import struct
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


SCHEMA_VERSION = "1.0"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GITHUB_REVIEWER = re.compile(r"^github:[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
JPEG_MAX_BYTES = 8 * 1024 * 1024
PRIMARY_ROOT_FILES = {"README.md", "rights.json", "hero.jpg"}
SUPPORTED_STYLES = {
    "american-street",
    "athleisure",
    "balletcore",
    "british-heritage",
    "cityboy",
    "clean-fit",
    "coquette-ladylike",
    "ecommerce-studio",
    "french-effortless",
    "gorpcore",
    "guochao-street",
    "italian-luxe",
    "japanese-lifestyle",
    "korean-cold-editorial",
    "korean-menswear",
    "neo-chinese",
    "nordic-minimal",
    "office-commute-women",
    "old-money",
    "preppy",
    "quiet-luxury",
    "resort-vacation",
    "workwear-vintage",
    "y2k-millennium",
}
FEATURED_STYLES = {
    "american-street",
    "coquette-ladylike",
    "ecommerce-studio",
    "gorpcore",
    "korean-cold-editorial",
    "korean-menswear",
    "neo-chinese",
    "old-money",
}
FULL_CASE_STYLES = {
    "american-street",
    "ecommerce-studio",
    "korean-cold-editorial",
}
GROUP_QA_ACCEPTED = {
    "file_count": {"pass"},
    "unique_hashes": {"pass"},
    "canvas_ratio": {"pass"},
    "pixel_consistency": {"pass"},
    "identity_consistency": {"pass", "no blocking visual drift observed"},
    "garment_hard_facts": {"pass", "no blocking visual drift observed"},
}
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?:/Users/|/home/|/private/|file://|[A-Za-z]:\\Users\\)"),
    re.compile(r"(?:^|\s)~/(?:\S+)"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|AKIA[A-Z0-9]{12,})\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*\S+"),
)


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_iso_z(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC ISO-8601")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC ISO-8601")
    return parsed


def iter_text_values(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from iter_text_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_text_values(nested)


def has_sensitive_public_text(value: object) -> bool:
    return any(
        pattern.search(text)
        for text in iter_text_values(value)
        for pattern in SENSITIVE_TEXT_PATTERNS
    )


def safe_child(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ValueError("unsafe asset path")
    root = root.resolve()
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        raise ValueError("unsafe asset path")
    return candidate


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise ValueError("invalid JPEG")
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if marker == 0xDA:
            break
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset : offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if length < 7:
                break
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            if width > 0 and height > 0:
                return width, height
            break
        offset += length
    raise ValueError("invalid JPEG")


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 33 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG")
    if data[12:16] != b"IHDR" or data[-12:-8] != b"\x00\x00\x00\x00" or data[-8:-4] != b"IEND":
        raise ValueError("invalid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if width < 1 or height < 1:
        raise ValueError("invalid PNG")
    return width, height


def _add(findings: list[str], code: str) -> None:
    if code not in findings:
        findings.append(code)


def validate_staged_primary_case(staging: Path) -> list[str]:
    findings: list[str] = []
    staging = staging.resolve()
    try:
        rights = read_json(staging / "rights-declaration.json")
        run = read_json(staging / "final-run.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return ["EVIDENCE_INCOMPLETE"]

    rights_required = {
        "schema_version",
        "work_id",
        "status",
        "reviewer",
        "declared_at",
        "declaration",
        "public_use_authorized",
        "project_media_policy_accepted",
        "source_model_display_authorized",
        "sources",
        "public_status",
    }
    promotion_fields = {"promoted_case_id", "promoted_at"}
    run_required = {
        "schema_version",
        "work_id",
        "generated_at",
        "action",
        "style",
        "mode",
        "route",
        "output_form",
        "state",
        "identity_anchor",
        "canvas_contract",
        "generation_calls",
        "expected_images",
        "actual_images",
        "preview_images_included",
        "outputs",
        "group_qa",
        "ai_content_label_notice",
        "public_status",
    }
    if (
        not rights_required.issubset(rights)
        or not set(rights).issubset(rights_required | promotion_fields)
        or not run_required.issubset(run)
        or not set(run).issubset(run_required | promotion_fields)
        or not isinstance(run.get("canvas_contract"), dict)
        or set(run.get("canvas_contract", {}))
        != {"target_ratio", "target_orientation", "batch_canvas_baseline", "all_files_match"}
    ):
        _add(findings, "EVIDENCE_FIELDS_INVALID")
    rights_is_promoted = rights.get("public_status") == "promoted"
    run_is_promoted = run.get("public_status") == "promoted"
    if (
        rights.get("public_status") not in {"not-promoted", "promoted"}
        or run.get("public_status") not in {"not-promoted", "promoted"}
        or rights_is_promoted != run_is_promoted
        or (set(rights) & promotion_fields)
        != (promotion_fields if rights_is_promoted else set())
        or (set(run) & promotion_fields)
        != (promotion_fields if run_is_promoted else set())
    ):
        _add(findings, "EVIDENCE_FIELDS_INVALID")
    if has_sensitive_public_text(rights) or has_sensitive_public_text(run):
        _add(findings, "PUBLIC_TEXT_SENSITIVE")
    if rights.get("schema_version") != SCHEMA_VERSION or run.get("schema_version") != SCHEMA_VERSION:
        _add(findings, "SCHEMA_INVALID")
    if rights.get("work_id") != run.get("work_id"):
        _add(findings, "WORK_ID_MISMATCH")
    if rights.get("status") != "user-approved-source-rights" or not all(
        rights.get(key) is True
        for key in ("public_use_authorized", "project_media_policy_accepted", "source_model_display_authorized")
    ):
        _add(findings, "SOURCE_RIGHTS_INCOMPLETE")
    if (
        not isinstance(rights.get("reviewer"), str)
        or not GITHUB_REVIEWER.fullmatch(str(rights["reviewer"]))
        or not isinstance(rights.get("declaration"), str)
        or not rights["declaration"].strip()
    ):
        _add(findings, "SOURCE_RIGHTS_INCOMPLETE")

    sources = rights.get("sources")
    if not isinstance(sources, list) or len(sources) != 4:
        _add(findings, "SOURCE_SET_INCOMPLETE")
    else:
        source_roles: list[str] = []
        source_paths: list[Path] = []
        source_hashes: list[str] = []
        for index, source in enumerate(sources, start=1):
            try:
                if not isinstance(source, dict) or set(source) != {"role", "path", "sha256"}:
                    _add(findings, "EVIDENCE_FIELDS_INVALID")
                    raise ValueError("invalid source record")
                role = str(source["role"])
                relative = Path(str(source["path"]))
                path = safe_child(staging, str(relative))
                data = path.read_bytes()
                jpeg_dimensions(data)
                digest = sha256_bytes(data)
                if (
                    not CASE_ID.fullmatch(role)
                    or relative.parent != Path("sources")
                    or not re.fullmatch(rf"source-{index}-[a-z0-9-]+\.jpg", relative.name)
                ):
                    _add(findings, "SOURCE_SET_INCOMPLETE")
                if source.get("sha256") != digest:
                    _add(findings, "ASSET_HASH_MISMATCH")
                source_roles.append(role)
                source_paths.append(path)
                source_hashes.append(digest)
            except (KeyError, OSError, ValueError, TypeError):
                _add(findings, "SOURCE_SET_INCOMPLETE")
        if (
            len(set(source_roles)) != 4
            or len(set(source_paths)) != 4
            or len(set(source_hashes)) != 4
        ):
            _add(findings, "SOURCE_SET_DUPLICATED")

    if run.get("state") != "image-ready":
        _add(findings, "PRIMARY_NOT_IMAGE_READY")
    if run.get("action") != "six-independent-final-images" or run.get("route") != "B1":
        _add(findings, "ROUTE_INVALID")
    if run.get("mode") != "B" or run.get("style") not in SUPPORTED_STYLES:
        _add(findings, "STYLE_UNREGISTERED")
    if run.get("identity_anchor") != "finals/look-1.png":
        _add(findings, "IDENTITY_ANCHOR_INVALID")
    if any(run.get(key) != 6 for key in ("generation_calls", "expected_images", "actual_images")):
        _add(findings, "FINAL_SET_INCOMPLETE")
    if run.get("preview_images_included") != 0:
        _add(findings, "PREVIEW_INCLUDED")
    canvas = run.get("canvas_contract")
    if (
        not isinstance(canvas, dict)
        or canvas.get("target_ratio") != "2:3"
        or canvas.get("target_orientation") != "portrait"
        or canvas.get("all_files_match") is not True
    ):
        _add(findings, "CANVAS_CONTRACT_INVALID")
    baseline = canvas.get("batch_canvas_baseline") if isinstance(canvas, dict) else None

    outputs = run.get("outputs")
    output_hashes: list[str] = []
    if not isinstance(outputs, list) or len(outputs) != 6:
        _add(findings, "FINAL_SET_INCOMPLETE")
    else:
        for expected, output in enumerate(outputs, start=1):
            try:
                if not isinstance(output, dict) or set(output) != {
                    "look",
                    "path",
                    "sha256",
                    "pixels",
                    "qa",
                    "user_review",
                }:
                    _add(findings, "EVIDENCE_FIELDS_INVALID")
                    raise ValueError("invalid output record")
                if output.get("look") != expected or output.get("path") != f"finals/look-{expected}.png":
                    _add(findings, "FINAL_SET_INCOMPLETE")
                if output.get("qa") != "qa-pass" or output.get("user_review") != "closed":
                    _add(findings, "USER_REVIEW_INCOMPLETE")
                path = safe_child(staging, str(output["path"]))
                data = path.read_bytes()
                width, height = png_dimensions(data)
                digest = sha256_bytes(data)
                output_hashes.append(digest)
                if output.get("sha256") != digest:
                    _add(findings, "ASSET_HASH_MISMATCH")
                if output.get("pixels") != f"{width}x{height}" or baseline != f"{width}x{height}":
                    _add(findings, "CANVAS_CONTRACT_INVALID")
            except (KeyError, OSError, ValueError, TypeError):
                _add(findings, "FINAL_SET_INCOMPLETE")
        if len(set(output_hashes)) != 6:
            _add(findings, "DUPLICATE_OUTPUT_HASH")

    group_qa = run.get("group_qa")
    review = group_qa.get("user_review_closure") if isinstance(group_qa, dict) else None
    expected_group_keys = set(GROUP_QA_ACCEPTED) | {
        "requires_user_review",
        "user_review_closure",
    }
    if (
        not isinstance(group_qa, dict)
        or set(group_qa) != expected_group_keys
        or not isinstance(review, dict)
        or set(review)
        != {"status", "reviewer", "reviewed_at", "confirmation", "closed_items"}
        or not isinstance(review.get("closed_items"), list)
        or not review.get("closed_items")
        or not all(
            isinstance(item, str) and item.strip()
            for item in review.get("closed_items", [])
        )
    ):
        _add(findings, "EVIDENCE_FIELDS_INVALID")
    if not isinstance(group_qa, dict) or any(
        group_qa.get(key) not in accepted for key, accepted in GROUP_QA_ACCEPTED.items()
    ):
        _add(findings, "GROUP_QA_INCOMPLETE")
    if (
        not isinstance(group_qa, dict)
        or group_qa.get("requires_user_review") != []
        or not isinstance(review, dict)
        or review.get("status") != "closed"
        or review.get("reviewer") != rights.get("reviewer")
        or not isinstance(review.get("reviewer"), str)
        or not GITHUB_REVIEWER.fullmatch(str(review.get("reviewer")))
        or not isinstance(review.get("confirmation"), str)
        or not review["confirmation"].strip()
    ):
        _add(findings, "USER_REVIEW_INCOMPLETE")
    label = run.get("ai_content_label_notice")
    if (
        not isinstance(label, dict)
        or set(label) != {"status", "informed_at", "requirement"}
        or label.get("status") != "informed"
        or not isinstance(label.get("requirement"), str)
        or not str(label.get("requirement")).strip()
    ):
        _add(findings, "AI_LABEL_NOTICE_INCOMPLETE")
    try:
        declared_at = parse_iso_z(rights.get("declared_at"))
        generated_at = parse_iso_z(run.get("generated_at"))
        reviewed_at = parse_iso_z(review.get("reviewed_at") if isinstance(review, dict) else None)
        informed_at = parse_iso_z(label.get("informed_at") if isinstance(label, dict) else None)
        if not declared_at <= generated_at <= informed_at <= reviewed_at:
            raise ValueError("invalid chronology")
        if rights.get("public_status") == "promoted" or run.get("public_status") == "promoted":
            if (
                rights.get("public_status") != "promoted"
                or run.get("public_status") != "promoted"
                or rights.get("promoted_case_id") != run.get("promoted_case_id")
                or rights.get("promoted_at") != run.get("promoted_at")
                or reviewed_at > parse_iso_z(run.get("promoted_at"))
            ):
                raise ValueError("invalid promotion chronology")
    except (AttributeError, TypeError, ValueError):
        _add(findings, "EVIDENCE_TIMESTAMP_INVALID")
    return findings


def pillow_converter(source: Path, destination: Path) -> None:
    from PIL import Image, ImageOps

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.save(destination, "JPEG", quality=86, optimize=True, progressive=True)


def pillow_compositor(sources: list[Path], destination: Path) -> None:
    from PIL import Image, ImageOps

    if len(sources) != 7:
        raise ValueError("hero requires one source plus six final images")

    def fit(path: Path, size: tuple[int, int]):
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.thumbnail(size, Image.Resampling.LANCZOS)
            tile = Image.new("RGB", size, "white")
            tile.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
            return tile

    canvas = Image.new("RGB", (1280, 640), "#f2f4f5")
    canvas.paste(fit(sources[0], (300, 600)), (20, 20))
    positions = ((340, 20), (640, 20), (940, 20), (340, 340), (640, 340), (940, 340))
    for source, position in zip(sources[1:], positions):
        canvas.paste(fit(source, (280, 280)), position)
    canvas.save(destination, "JPEG", quality=88, optimize=True, progressive=True)


def _public_asset(original: Path, public: Path, role: str, name: str) -> dict[str, object]:
    public_data = public.read_bytes()
    width, height = jpeg_dimensions(public_data)
    return {
        "role": role,
        "name": name,
        "path": public.name,
        "original_sha256": sha256_file(original),
        "public_sha256": sha256_bytes(public_data),
        "mime": "image/jpeg",
        "bytes": len(public_data),
        "width": width,
        "height": height,
    }


def _preview_module():
    spec = importlib.util.spec_from_file_location("primary_style_preview", Path(__file__).with_name("style_preview.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def primary_rights_index_content(root: Path) -> str:
    rows: list[str] = []
    primary_root = root.resolve() / "docs" / "demo" / "primary-cases"
    if primary_root.is_dir():
        for path in sorted(primary_root.glob("*/rights.json")):
            rights = read_json(path)
            generated = [asset for asset in rights.get("assets", []) if asset.get("role") == "generated-final"]
            digest = generated[0].get("public_sha256", "") if generated else ""
            rows.append(
                f"| `{rights.get('case_id', '')}` | primary | maintainer-authorized real garment | "
                f"CC0-1.0 | `{str(digest)[:12]}` | {rights.get('status', '')} |"
            )
    auxiliary_root = root.resolve() / "docs" / "demo" / "cases"
    if auxiliary_root.is_dir():
        for path in sorted(auxiliary_root.glob("*/rights.json")):
            rights = read_json(path)
            source = rights.get("source", {})
            asset = rights.get("asset", {})
            rows.append(
                f"| `{rights.get('case_id', '')}` | auxiliary | The Met `{source.get('object_id', '')}` | "
                f"CC0-1.0 | `{str(asset.get('sha256', ''))[:12]}` | {rights.get('status', '')} |"
            )
    preview_root = root.resolve() / "docs/demo/style-previews"
    for path in sorted(preview_root.glob("*/evidence.json")):
        evidence = read_json(path)
        previews = evidence.get("previews", [])
        digest = previews[0].get("sha256", "") if previews else ""
        rows.append(f"| `{evidence.get('run_id', '')}` | style-preview | authorized primary garment | CC0-1.0 | `{str(digest)[:12]}` | 24 human-approved single-style sheets; not finals |")
    table = (
        "| Case | Role | Source | License | SHA-256 prefix | Status |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(rows)
        if rows
        else "No media is currently approved for publication."
    )
    primary_ready = any("| primary |" in row for row in rows)
    primary_line = (
        "A maintainer-owned primary demo is rights-cleared and image-ready."
        if primary_ready
        else "Primary maintainer-owned demo remains `sample-blocked`."
    )
    return f"""# Public media rights manifest

Approved primary and auxiliary media is listed below.

{primary_line} Auxiliary CC0 cases do not count as non-maintainer adoption.

{table}

Apache-2.0 does not cover case media. Public source derivatives and project-generated demo media are offered under CC0 only to the extent the project can grant rights. CC0 does not imply endorsement or remove possible trademark, privacy, personality, moral, or cultural rights.
"""


def render_rights_index(root: Path) -> Path:
    output = root.resolve() / "docs" / "demo" / "RIGHTS.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(primary_rights_index_content(root), encoding="utf-8")
    return output


def promote_primary_case(
    root: Path,
    staging: Path,
    case_id: str,
    *,
    promoted_at: str,
    converter: Callable[[Path, Path], None] = pillow_converter,
    compositor: Callable[[list[Path], Path], None] = pillow_compositor,
) -> dict[str, object]:
    if not CASE_ID.fullmatch(case_id):
        raise ValueError("invalid case id")
    findings = validate_staged_primary_case(staging)
    if findings:
        raise ValueError("primary demo validation failed: " + ", ".join(findings))
    root = root.resolve()
    staging = staging.resolve()
    rights_declaration = read_json(staging / "rights-declaration.json")
    run = read_json(staging / "final-run.json")
    reviewed_at = parse_iso_z(run["group_qa"]["user_review_closure"]["reviewed_at"])
    if reviewed_at > parse_iso_z(promoted_at):
        raise ValueError("promotion timestamp predates human review")
    destination = root / "docs" / "demo" / "primary-cases" / case_id
    if destination.exists():
        raise FileExistsError(f"primary case already exists: {case_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{case_id}-", dir=destination.parent))
    try:
        public_assets: list[dict[str, object]] = []
        public_sources: list[Path] = []
        for source in rights_declaration["sources"]:
            original = safe_child(staging, source["path"])
            public = temporary / Path(source["path"]).name
            converter(original, public)
            public_sources.append(public)
            public_assets.append(_public_asset(original, public, "source", source["role"]))
        public_outputs: list[Path] = []
        for output in run["outputs"]:
            original = safe_child(staging, output["path"])
            public = temporary / f"look-{output['look']}.jpg"
            converter(original, public)
            public_outputs.append(public)
            public_assets.append(_public_asset(original, public, "generated-final", f"look-{output['look']}"))
        hero = temporary / "hero.jpg"
        compositor([public_sources[0], *public_outputs], hero)
        hero_data = hero.read_bytes()
        if jpeg_dimensions(hero_data) != (1280, 640) or len(hero_data) >= 1024 * 1024:
            raise ValueError("social preview must be 1280x640 and smaller than 1 MiB")
        review = run["group_qa"]["user_review_closure"]
        rights = {
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "work_id": run["work_id"],
            "status": "promoted",
            "role": "primary",
            "primary_demo_status": "ready",
            "style": run["style"],
            "route": run["route"],
            "source_rights": {
                "reviewer": rights_declaration["reviewer"],
                "declared_at": rights_declaration["declared_at"],
                "declaration": rights_declaration["declaration"],
                "public_use_authorized": True,
                "project_media_policy_accepted": True,
                "source_model_display_authorized": True,
            },
            "media_license": {
                "id": "CC0-1.0",
                "url": CC0_URL,
                "scope": "Public source derivatives and generated demo media to the extent the project can grant rights.",
            },
            "assets": public_assets,
            "hero": {
                "path": "hero.jpg",
                "sha256": sha256_bytes(hero_data),
                "mime": "image/jpeg",
                "bytes": len(hero_data),
                "width": 1280,
                "height": 640,
            },
            "quality": {
                "state": "image-ready",
                "generated_at": run["generated_at"],
                "expected_images": 6,
                "actual_images": 6,
                "preview_images_included": 0,
                "generation_calls": 6,
                "canvas_contract": run["canvas_contract"],
                "unique_original_output_hashes": 6,
                "checks": {
                    key: run["group_qa"][key]
                    for key in GROUP_QA_ACCEPTED
                },
            },
            "human_review": {
                "status": "closed",
                "reviewer": review["reviewer"],
                "reviewed_at": review["reviewed_at"],
                "confirmation": review["confirmation"],
                "closed_items": review.get("closed_items", []),
            },
            "ai_content_label": {
                "status": "required-and-disclosed",
                "informed_at": run["ai_content_label_notice"]["informed_at"],
                "requirement": run["ai_content_label_notice"]["requirement"],
            },
            "promoted_at": promoted_at,
            "notices": [
                "Apache-2.0 does not apply to media in this case.",
                "AI-generated outputs require applicable synthetic-content labeling when published.",
                "CC0 applies only to the extent the project can grant rights and does not remove third-party rights.",
            ],
        }
        write_json(temporary / "rights.json", rights)
        (temporary / "README.md").write_text(primary_case_readme(rights), encoding="utf-8")
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    render_rights_index(root)
    for record_name in ("rights-declaration.json", "final-run.json"):
        record = read_json(staging / record_name)
        record["public_status"] = "promoted"
        record["promoted_case_id"] = case_id
        record["promoted_at"] = promoted_at
        write_json(staging / record_name, record)
    return rights


def primary_case_readme(rights: dict[str, object]) -> str:
    return f"""# Primary demo — {rights['case_id']}

Status: `image-ready` and `promoted`.

This maintainer-authorized real-garment case uses the `{rights['style']}` route `{rights['route']}`. Four source views remain authoritative for garment facts; six independent generated images passed the 2:3 canvas contract, unique-hash check, commercial QA, and maintainer source review.

The source derivatives and generated demo media are offered under CC0 only to the extent the project can grant rights. Apache-2.0 covers project code and documentation, not this media. Public use of the generated images requires applicable AI-generated or synthetic-content labeling.

See `rights.json` for hashes, rights evidence, QA closure, and limitations.
"""


def validate_public_primary_cases(root: Path) -> list[str]:
    findings: list[str] = []
    case_styles: list[str] = []
    cases_root = root.resolve() / "docs" / "demo" / "primary-cases"
    if not cases_root.is_dir() or cases_root.is_symlink():
        return ["primary public cases directory is missing"]
    for case_dir in sorted(cases_root.iterdir()):
        if case_dir.is_symlink() or not case_dir.is_dir():
            findings.append(f"{case_dir.name}: unregistered primary case entry")
            continue
        try:
            rights = read_json(case_dir / "rights.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append(f"{case_dir.name}: unreadable primary rights: {exc}")
            continue
        required_top = {
            "schema_version",
            "case_id",
            "work_id",
            "status",
            "role",
            "primary_demo_status",
            "style",
            "route",
            "source_rights",
            "media_license",
            "assets",
            "hero",
            "quality",
            "human_review",
            "ai_content_label",
            "promoted_at",
            "notices",
        }
        if set(rights) != required_top:
            findings.append(f"{case_dir.name}: primary rights contract is incomplete")
        if rights.get("schema_version") != SCHEMA_VERSION:
            findings.append(f"{case_dir.name}: unsupported primary rights schema")
        if (
            rights.get("status") != "promoted"
            or rights.get("role") != "primary"
            or rights.get("primary_demo_status") != "ready"
        ):
            findings.append(f"{case_dir.name}: primary promotion status is invalid")
        if (
            rights.get("case_id") != case_dir.name
            or not isinstance(rights.get("work_id"), str)
            or not CASE_ID.fullmatch(str(rights.get("work_id")))
        ):
            findings.append(f"{case_dir.name}: case identifier mismatch")
        if rights.get("style") not in FULL_CASE_STYLES or rights.get("route") != "B1":
            findings.append(f"{case_dir.name}: style or route is invalid")
        elif isinstance(rights.get("style"), str):
            case_styles.append(str(rights["style"]))

        source_rights = rights.get("source_rights")
        if (
            not isinstance(source_rights, dict)
            or set(source_rights)
            != {
                "reviewer",
                "declared_at",
                "declaration",
                "public_use_authorized",
                "project_media_policy_accepted",
                "source_model_display_authorized",
            }
            or not isinstance(source_rights.get("reviewer"), str)
            or not GITHUB_REVIEWER.fullmatch(str(source_rights.get("reviewer")))
            or not isinstance(source_rights.get("declaration"), str)
            or not str(source_rights.get("declaration")).strip()
            or any(
                source_rights.get(key) is not True
                for key in (
                    "public_use_authorized",
                    "project_media_policy_accepted",
                    "source_model_display_authorized",
                )
            )
        ):
            findings.append(f"{case_dir.name}: source rights evidence is incomplete")

        ai_label = rights.get("ai_content_label")
        if (
            not isinstance(ai_label, dict)
            or set(ai_label) != {"status", "informed_at", "requirement"}
            or ai_label.get("status") != "required-and-disclosed"
            or not isinstance(ai_label.get("informed_at"), str)
            or not isinstance(ai_label.get("requirement"), str)
            or not str(ai_label.get("requirement")).strip()
        ):
            findings.append(f"{case_dir.name}: AI label evidence is incomplete")
        human_review = rights.get("human_review")
        if (
            not isinstance(human_review, dict)
            or set(human_review)
            != {"status", "reviewer", "reviewed_at", "confirmation", "closed_items"}
            or human_review.get("status") != "closed"
            or human_review.get("reviewer") != (
                source_rights.get("reviewer") if isinstance(source_rights, dict) else None
            )
            or not isinstance(human_review.get("confirmation"), str)
            or not str(human_review.get("confirmation")).strip()
            or not isinstance(human_review.get("reviewed_at"), str)
            or not isinstance(human_review.get("closed_items"), list)
            or not human_review.get("closed_items")
            or not all(
                isinstance(item, str) and item.strip()
                for item in human_review.get("closed_items", [])
            )
        ):
            findings.append(f"{case_dir.name}: human review is incomplete")
        license_record = rights.get("media_license")
        if (
            not isinstance(license_record, dict)
            or set(license_record) != {"id", "url", "scope"}
            or license_record.get("id") != "CC0-1.0"
            or license_record.get("url") != CC0_URL
            or not isinstance(license_record.get("scope"), str)
            or not str(license_record.get("scope")).strip()
        ):
            findings.append(f"{case_dir.name}: media license is invalid")

        quality = rights.get("quality")
        canvas = quality.get("canvas_contract") if isinstance(quality, dict) else None
        checks = quality.get("checks") if isinstance(quality, dict) else None
        if (
            not isinstance(quality, dict)
            or set(quality)
            != {
                "state",
                "generated_at",
                "expected_images",
                "actual_images",
                "preview_images_included",
                "generation_calls",
                "canvas_contract",
                "unique_original_output_hashes",
                "checks",
            }
            or quality.get("state") != "image-ready"
            or quality.get("expected_images") != 6
            or quality.get("actual_images") != 6
            or quality.get("preview_images_included") != 0
            or quality.get("generation_calls") != 6
            or quality.get("unique_original_output_hashes") != 6
            or not isinstance(canvas, dict)
            or set(canvas)
            != {
                "target_ratio",
                "target_orientation",
                "batch_canvas_baseline",
                "all_files_match",
            }
            or canvas.get("target_ratio") != "2:3"
            or canvas.get("target_orientation") != "portrait"
            or canvas.get("all_files_match") is not True
            or not isinstance(canvas.get("batch_canvas_baseline"), str)
            or not isinstance(checks, dict)
            or set(checks) != set(GROUP_QA_ACCEPTED)
            or any(checks.get(key) not in accepted for key, accepted in GROUP_QA_ACCEPTED.items())
        ):
            findings.append(f"{case_dir.name}: quality evidence is incomplete")

        try:
            declared_at = parse_iso_z(
                source_rights.get("declared_at") if isinstance(source_rights, dict) else None
            )
            generated_at = parse_iso_z(
                quality.get("generated_at") if isinstance(quality, dict) else None
            )
            informed_at = parse_iso_z(
                ai_label.get("informed_at") if isinstance(ai_label, dict) else None
            )
            reviewed_at = parse_iso_z(
                human_review.get("reviewed_at") if isinstance(human_review, dict) else None
            )
            promoted_at = parse_iso_z(rights.get("promoted_at"))
            if not declared_at <= generated_at <= informed_at <= reviewed_at <= promoted_at:
                raise ValueError("invalid chronology")
        except (TypeError, ValueError):
            findings.append(f"{case_dir.name}: evidence chronology is invalid")

        notices = rights.get("notices")
        if (
            not isinstance(notices, list)
            or len(notices) < 3
            or not all(isinstance(item, str) and item.strip() for item in notices)
            or not any("Apache-2.0" in item for item in notices)
            or not any("AI-generated" in item for item in notices)
            or not any("CC0" in item for item in notices)
        ):
            findings.append(f"{case_dir.name}: public notices are incomplete")

        assets = rights.get("assets")
        if not isinstance(assets, list) or len(assets) != 10:
            findings.append(f"{case_dir.name}: primary asset set is incomplete")
            assets = []
        expected_files = {"README.md", "rights.json", "hero.jpg"}
        output_original_hashes: list[str] = []
        source_original_hashes: list[str] = []
        generated_names: list[str] = []
        asset_paths: list[str] = []
        output_dimensions: list[tuple[int, int]] = []
        for asset in assets:
            if not isinstance(asset, dict):
                findings.append(f"{case_dir.name}: malformed primary asset")
                continue
            if set(asset) != {
                "role",
                "name",
                "path",
                "original_sha256",
                "public_sha256",
                "mime",
                "bytes",
                "width",
                "height",
            }:
                findings.append(f"{case_dir.name}: malformed primary asset")
            path_name = asset.get("path")
            if not isinstance(path_name, str) or Path(path_name).name != path_name:
                findings.append(f"{case_dir.name}: unsafe primary asset path")
                continue
            asset_paths.append(path_name)
            expected_files.add(path_name)
            path = case_dir / path_name
            try:
                data = path.read_bytes()
                width, height = jpeg_dimensions(data)
            except (OSError, ValueError):
                findings.append(f"{case_dir.name}/{path_name}: invalid JPEG")
                continue
            if asset.get("public_sha256") != sha256_bytes(data):
                findings.append(f"{case_dir.name}/{path_name}: hash mismatch")
            if (
                asset.get("mime") != "image/jpeg"
                or asset.get("bytes") != len(data)
                or asset.get("width") != width
                or asset.get("height") != height
                or not isinstance(asset.get("original_sha256"), str)
                or not SHA256.fullmatch(str(asset.get("original_sha256")))
            ):
                findings.append(f"{case_dir.name}/{path_name}: media evidence is incomplete")
            if asset.get("role") == "generated-final":
                output_original_hashes.append(str(asset.get("original_sha256", "")))
                generated_names.append(str(asset.get("name", "")))
                output_dimensions.append((width, height))
                if path_name != f"{asset.get('name')}.jpg":
                    findings.append(f"{case_dir.name}/{path_name}: generated asset name is invalid")
            elif asset.get("role") == "source":
                source_original_hashes.append(str(asset.get("original_sha256", "")))
                if not isinstance(asset.get("name"), str) or not CASE_ID.fullmatch(str(asset.get("name"))):
                    findings.append(f"{case_dir.name}/{path_name}: source asset name is invalid")
            else:
                findings.append(f"{case_dir.name}/{path_name}: asset role is invalid")
        if len(output_original_hashes) != 6 or len(set(output_original_hashes)) != 6 or not all(SHA256.fullmatch(value) for value in output_original_hashes):
            findings.append(f"{case_dir.name}: generated output hashes are incomplete or duplicated")
        if sorted(generated_names) != [f"look-{index}" for index in range(1, 7)]:
            findings.append(f"{case_dir.name}: generated output names are incomplete")
        if (
            len(source_original_hashes) != 4
            or len(set(source_original_hashes)) != 4
            or len(asset_paths) != len(set(asset_paths))
        ):
            findings.append(f"{case_dir.name}: source assets are incomplete or duplicated")
        if output_dimensions:
            baseline = f"{output_dimensions[0][0]}x{output_dimensions[0][1]}"
            if (
                len(set(output_dimensions)) != 1
                or output_dimensions[0][0] * 3 != output_dimensions[0][1] * 2
                or not isinstance(canvas, dict)
                or canvas.get("batch_canvas_baseline") != baseline
            ):
                findings.append(f"{case_dir.name}: output canvas evidence does not match assets")
        hero = rights.get("hero")
        try:
            if not isinstance(hero, dict) or set(hero) != {
                "path",
                "sha256",
                "mime",
                "bytes",
                "width",
                "height",
            }:
                raise ValueError("invalid hero record")
            hero_path = case_dir / str(hero["path"])
            hero_data = hero_path.read_bytes()
            hero_dimensions = jpeg_dimensions(hero_data)
        except (KeyError, TypeError, OSError, ValueError):
            findings.append(f"{case_dir.name}: social preview is invalid")
        else:
            if (
                hero.get("path") != "hero.jpg"
                or hero.get("mime") != "image/jpeg"
                or hero.get("bytes") != len(hero_data)
                or hero.get("width") != 1280
                or hero.get("height") != 640
                or hero_dimensions != (1280, 640)
                or len(hero_data) >= 1024 * 1024
                or hero.get("sha256") != sha256_bytes(hero_data)
            ):
                findings.append(f"{case_dir.name}: social preview evidence is invalid")
        actual_files = {entry.name for entry in case_dir.iterdir() if entry.is_file() and not entry.is_symlink()}
        if actual_files != expected_files or any(entry.is_symlink() or not entry.is_file() for entry in case_dir.iterdir()):
            findings.append(f"{case_dir.name}: unregistered or missing primary case artifact")
        try:
            if (case_dir / "README.md").read_text(encoding="utf-8") != primary_case_readme(rights):
                findings.append(f"{case_dir.name}: primary case README is stale")
        except OSError:
            findings.append(f"{case_dir.name}: primary case README is missing")
        if has_sensitive_public_text(rights):
            findings.append(f"{case_dir.name}: primary rights contain sensitive text")
    if len(case_styles) != len(set(case_styles)):
        findings.append("primary cases must use unique approved full-case styles")
    return findings


def _zip_files(files: Iterable[tuple[Path, str]], archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path, relative in sorted(files, key=lambda item: item[1]):
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, path.read_bytes())


def sanitize_release_image(source: Path, destination: Path) -> None:
    """Decode and re-encode an image without source metadata or ancillary text."""
    from PIL import Image, ImageOps

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        if destination.suffix.lower() == ".jpg":
            image.convert("RGB").save(
                destination,
                "JPEG",
                quality=95,
                optimize=True,
                progressive=True,
            )
        elif destination.suffix.lower() == ".png":
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in opened.info else "RGB")
            image.save(destination, "PNG", optimize=True)
        else:
            raise ValueError("unsupported release image type")


def build_primary_media_bundle(
    staging: Path,
    case_id: str,
    version: str,
    output_dir: Path,
    *,
    sanitizer: Callable[[Path, Path], None] = sanitize_release_image,
) -> tuple[Path, Path]:
    findings = validate_staged_primary_case(staging)
    if findings:
        raise ValueError("primary demo validation failed: " + ", ".join(findings))
    output_dir.mkdir(parents=True, exist_ok=True)
    root_name = f"threadtruth-studio-{case_id}-{version}"
    archive = output_dir / f"{root_name}.zip"
    checksum = output_dir / f"{root_name}.zip.sha256"
    rights = read_json(staging / "rights-declaration.json")
    run = read_json(staging / "final-run.json")
    with tempfile.TemporaryDirectory() as temp_dir:
        temporary = Path(temp_dir)
        selected: list[tuple[Path, str]] = []
        manifest_lines: list[str] = []
        source_evidence: list[dict[str, object]] = []
        output_evidence: list[dict[str, object]] = []

        for source in rights["sources"]:
            original = safe_child(staging, source["path"])
            relative = f"sources/{original.name}"
            clean = temporary / relative
            clean.parent.mkdir(parents=True, exist_ok=True)
            sanitizer(original, clean)
            width, height = jpeg_dimensions(clean.read_bytes())
            release_hash = sha256_file(clean)
            selected.append((clean, f"{root_name}/{relative}"))
            manifest_lines.append(f"{release_hash}  {relative}")
            source_evidence.append(
                {
                    "role": source["role"],
                    "path": relative,
                    "original_sha256": source["sha256"],
                    "release_sha256": release_hash,
                    "pixels": f"{width}x{height}",
                }
            )

        for output in run["outputs"]:
            original = safe_child(staging, output["path"])
            relative = f"finals/{original.name}"
            clean = temporary / relative
            clean.parent.mkdir(parents=True, exist_ok=True)
            sanitizer(original, clean)
            width, height = png_dimensions(clean.read_bytes())
            release_hash = sha256_file(clean)
            selected.append((clean, f"{root_name}/{relative}"))
            manifest_lines.append(f"{release_hash}  {relative}")
            output_evidence.append(
                {
                    "look": output["look"],
                    "path": relative,
                    "original_sha256": output["sha256"],
                    "release_sha256": release_hash,
                    "pixels": f"{width}x{height}",
                    "qa": output["qa"],
                    "user_review": output["user_review"],
                }
            )

        public_rights = {
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "work_id": rights["work_id"],
            "status": rights["status"],
            "reviewer": rights["reviewer"],
            "declared_at": rights["declared_at"],
            "declaration": rights["declaration"],
            "public_use_authorized": rights["public_use_authorized"],
            "project_media_policy_accepted": rights["project_media_policy_accepted"],
            "source_model_display_authorized": rights["source_model_display_authorized"],
            "media_license": {
                "id": "CC0-1.0",
                "url": CC0_URL,
                "scope": "Included media to the extent the project can grant rights.",
            },
            "sources": source_evidence,
        }
        public_run = {
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "work_id": run["work_id"],
            "generated_at": run["generated_at"],
            "action": run["action"],
            "style": run["style"],
            "mode": run["mode"],
            "route": run["route"],
            "output_form": run["output_form"],
            "state": run["state"],
            "identity_anchor": "finals/look-1.png",
            "canvas_contract": run["canvas_contract"],
            "generation_calls": run["generation_calls"],
            "expected_images": run["expected_images"],
            "actual_images": run["actual_images"],
            "preview_images_included": run["preview_images_included"],
            "outputs": output_evidence,
            "group_qa": {
                key: run["group_qa"][key]
                for key in GROUP_QA_ACCEPTED
            },
            "human_review": {
                key: run["group_qa"]["user_review_closure"][key]
                for key in (
                    "status",
                    "reviewer",
                    "reviewed_at",
                    "confirmation",
                    "closed_items",
                )
            },
            "ai_content_label": {
                "status": "required-and-disclosed",
                "informed_at": run["ai_content_label_notice"]["informed_at"],
                "requirement": run["ai_content_label_notice"]["requirement"],
            },
        }
        if has_sensitive_public_text(public_rights) or has_sensitive_public_text(public_run):
            raise ValueError("PUBLIC_TEXT_SENSITIVE: release evidence contains private data")
        rights_path = temporary / "rights.json"
        run_path = temporary / "run-evidence.json"
        readme_path = temporary / "README.md"
        write_json(rights_path, public_rights)
        write_json(run_path, public_run)
        readme_path.write_text(
            f"""# ThreadTruth Studio primary media — {case_id}

This bundle contains four authorized real-garment sources and six independently generated, human-accepted final PNGs for the `{run['style']}` route `{run['route']}`.

All images were decoded and re-encoded before packaging to remove embedded metadata while preserving the recorded canvas. The results are AI-generated media and require applicable synthetic-content labeling. Apache-2.0 does not cover media; the included media is offered under CC0 only to the extent the project can grant rights.
""",
            encoding="utf-8",
        )
        for path, name in (
            (readme_path, "README.md"),
            (rights_path, "rights.json"),
            (run_path, "run-evidence.json"),
        ):
            selected.append((path, f"{root_name}/{name}"))
            manifest_lines.append(f"{sha256_file(path)}  {name}")

        manifest = temporary / "SHA256SUMS"
        manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        selected.append((manifest, f"{root_name}/SHA256SUMS"))
        _zip_files(selected, archive)
    digest = sha256_file(archive)
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def validate_style_index(root: Path) -> list[str]:
    findings: list[str] = []
    demo_root = root.resolve() / "docs" / "demo"
    path = demo_root / "style-index.json"
    try:
        index = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["style index is missing or invalid"]
    pack_root = root.resolve() / "skills" / "threadtruth-studio" / "references" / "styles"
    pack_slugs = {path.name.removesuffix(".pack.yaml") for path in pack_root.glob("*.pack.yaml") if path.name != "_TEMPLATE.pack.yaml"}
    styles = index.get("styles")
    if index.get("schema_version") != SCHEMA_VERSION or not isinstance(styles, list):
        return ["style index schema is invalid"]
    slugs = [item.get("slug") for item in styles if isinstance(item, dict)]
    if len(styles) != 24 or set(slugs) != pack_slugs or len(slugs) != len(set(slugs)):
        findings.append("style index does not cover 24 unique packs")
    featured = {
        item.get("slug")
        for item in styles
        if isinstance(item, dict) and item.get("featured") is True
    }
    if featured != FEATURED_STYLES:
        findings.append("style index must define the approved eight featured styles")
    full_cases = {
        item.get("slug")
        for item in styles
        if isinstance(item, dict) and item.get("full_case") in {"ready", "planned"}
    }
    if full_cases != FULL_CASE_STYLES:
        findings.append("style index must define the approved three full primary cases")

    approved_images: dict[str, tuple[str, dict[str, object]]] = {}
    primary_root = demo_root / "primary-cases"
    if primary_root.is_dir():
        for rights_path in primary_root.glob("*/rights.json"):
            try:
                rights = read_json(rights_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if (
                rights.get("status") != "promoted"
                or rights.get("role") != "primary"
                or rights.get("style") not in SUPPORTED_STYLES
            ):
                continue
            for asset in rights.get("assets", []):
                if isinstance(asset, dict) and asset.get("role") == "generated-final":
                    relative = f"primary-cases/{rights_path.parent.name}/{asset.get('path', '')}"
                    approved_images[relative] = (str(rights["style"]), asset)

    try:
        approved_previews = _preview_module().preview_links(root)
    except (OSError, ValueError, TypeError):
        approved_previews = {}
        findings.append("style preview evidence is invalid")
    ready_images: list[str] = []
    for item in styles:
        if not isinstance(item, dict) or item.get("status") not in {"ready", "planned"}:
            findings.append("style index contains an invalid status")
            continue
        if (
            item.get("slug") not in SUPPORTED_STYLES
            or not isinstance(item.get("display_name"), str)
            or not str(item.get("display_name")).strip()
            or not isinstance(item.get("source_family"), str)
            or not str(item.get("source_family")).strip()
            or not isinstance(item.get("beta_week"), int)
            or not 0 <= item.get("beta_week") <= 4
        ):
            findings.append(f"{item.get('slug')}: style index metadata is incomplete")
        image = item.get("representative_image")
        if item.get("preview") != approved_previews.get(item.get("slug")):
            findings.append(f"{item.get('slug')}: preview is not bound to approved evidence")
        if item["status"] == "ready":
            try:
                image_path = safe_child(demo_root, image)
                data = image_path.read_bytes()
                jpeg_dimensions(data)
            except (OSError, TypeError, ValueError):
                findings.append(f"{item.get('slug')}: ready style lacks a representative image")
                continue
            ready_images.append(str(image))
            approval = approved_images.get(str(image))
            if (
                image_path.suffix.lower() != ".jpg"
                or approval is None
                or approval[0] != item.get("slug")
                or approval[1].get("mime") != "image/jpeg"
                or approval[1].get("public_sha256") != sha256_bytes(data)
            ):
                findings.append(f"{item.get('slug')}: representative is not bound to approved rights")
            if item.get("full_case") == "ready" and approval is None:
                findings.append(f"{item.get('slug')}: ready full case lacks approved evidence")
        elif image is not None:
            findings.append(f"{item.get('slug')}: planned style must not claim an image")
        elif item.get("full_case") == "ready":
            findings.append(f"{item.get('slug')}: ready full case cannot be planned")
    if len(ready_images) != len(set(ready_images)):
        findings.append("style index reuses a representative image")
    return findings


def style_page_content(item: dict[str, object]) -> str:
    image = item.get("representative_image")
    if item.get("status") == "ready" and isinstance(image, str):
        visual = f"![{item['display_name']} representative](../{image})\n"
        status_note = "A rights-cleared representative is available."
    else:
        visual = ""
        status_note = "No public representative image has been generated or approved yet."
    full_case = item.get("full_case", "none")
    preview_note = ""
    if "preview" in item:
        preview = item["preview"]
        if preview:
            preview_note = f"\nStyle preview: [whole six-pose sheet](../{preview['path']}) for `{preview['style']}`. The linked image is the complete action-0 sheet, with no crop or upscale. AI-generated style preview; not an independent final.\n"
        else:
            preview_note = "\nStyle preview: `planned`. No approved single-style six-pose sheet yet.\n"
    return f"""# {item['display_name']}

Status: `{item['status']}` · Featured: `{str(bool(item['featured'])).lower()}` · Full six-image case: `{full_case}`

Recommended source family: **{item['source_family']}**.

{status_note}

{visual}{preview_note}A style page records visual evidence only after source rights, generation approval, six-image or single-image QA as applicable, and AI-content labeling are complete. A planned page is not generation evidence.
"""


def style_overview_content(index: dict[str, object]) -> str:
    rows = []
    for item in index["styles"]:
        rows.append(
            f"| [{item['display_name']}](styles/{item['slug']}.md) | "
            f"{'featured' if item['featured'] else 'index'} | {item['status']} | "
            f"{item['full_case']} | {item['source_family']} |"
        )
    ready = sum(item["status"] == "ready" for item in index["styles"])
    preview_coverage = ""
    if any("preview" in item for item in index["styles"]):
        count = sum(bool(item.get("preview")) for item in index["styles"])
        preview_coverage = f"\nSingle-style preview-sheet coverage: **{count}/24**. Final representative coverage: **{ready}/24**. Each preview is one whole action-0 sheet with six canonical poses; preview sheets never satisfy final-image or six-image case requirements.\n"
    return f"""# 24-style public evidence index

Visual evidence progress: **{ready}/24 ready**. The runtime contains 24 routed packs; this page separately tracks rights-cleared public image evidence and never treats a planned card as a completed generation.
{preview_coverage}

| Style | Tier | Representative | Six-image case | Source family |
|---|---|---|---|---|
{"\n".join(rows)}

Three styles are designated for complete six-image primary cases: Korean Cold Editorial, E-commerce Studio, and American Street. The remaining styles need one approved representative image each. New generation remains subject to explicit per-style authorization.
"""


def expected_style_pages(root: Path) -> dict[Path, str]:
    demo_root = root.resolve() / "docs" / "demo"
    index = read_json(demo_root / "style-index.json")
    outputs = {demo_root / "STYLES.md": style_overview_content(index)}
    for item in index["styles"]:
        outputs[demo_root / "styles" / f"{item['slug']}.md"] = style_page_content(item)
    return outputs


def render_style_pages(root: Path) -> list[Path]:
    outputs = expected_style_pages(root)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return sorted(outputs)


def validate_style_pages(root: Path) -> list[str]:
    findings: list[str] = []
    try:
        outputs = expected_style_pages(root)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["style pages cannot be derived"]
    for path, expected in outputs.items():
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            findings.append(f"missing generated style page: {path.name}")
        else:
            if actual != expected:
                findings.append(f"stale generated style page: {path.name}")
    styles_root = root.resolve() / "docs" / "demo" / "styles"
    expected_names = {path.name for path in outputs if path.parent == styles_root}
    if styles_root.is_dir():
        actual_names = {path.name for path in styles_root.iterdir() if path.is_file()}
        if actual_names != expected_names:
            findings.append("style page set does not match the style index")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--staging", type=Path, required=True)
    promote = subparsers.add_parser("promote")
    promote.add_argument("--staging", type=Path, required=True)
    promote.add_argument("--case-id", required=True)
    promote.add_argument("--promoted-at", required=True)
    bundle = subparsers.add_parser("build-media")
    bundle.add_argument("--staging", type=Path, required=True)
    bundle.add_argument("--case-id", required=True)
    bundle.add_argument("--version", required=True)
    bundle.add_argument("--output", type=Path, required=True)
    subparsers.add_parser("render-styles")
    args = parser.parse_args()
    if args.command == "validate":
        findings = validate_staged_primary_case(args.staging)
        print(json.dumps({"findings": findings}, ensure_ascii=False, indent=2))
        return 1 if findings else 0
    if args.command == "promote":
        rights = promote_primary_case(args.root, args.staging, args.case_id, promoted_at=args.promoted_at)
        print(json.dumps(rights, ensure_ascii=False, indent=2))
        return 0
    if args.command == "render-styles":
        for path in render_style_pages(args.root):
            print(path)
        return 0
    archive, checksum = build_primary_media_bundle(args.staging, args.case_id, args.version, args.output)
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
