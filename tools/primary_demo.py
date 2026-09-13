#!/usr/bin/env python3
"""Promote a rights-cleared, image-ready primary demo into public artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Iterable


SCHEMA_VERSION = "1.0"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
JPEG_MAX_BYTES = 8 * 1024 * 1024
PRIMARY_ROOT_FILES = {"README.md", "rights.json", "hero.jpg"}


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

    if rights.get("schema_version") != SCHEMA_VERSION or run.get("schema_version") != SCHEMA_VERSION:
        _add(findings, "SCHEMA_INVALID")
    if rights.get("work_id") != run.get("work_id"):
        _add(findings, "WORK_ID_MISMATCH")
    if rights.get("status") != "user-approved-source-rights" or not all(
        rights.get(key) is True
        for key in ("public_use_authorized", "project_media_policy_accepted", "source_model_display_authorized")
    ):
        _add(findings, "SOURCE_RIGHTS_INCOMPLETE")
    if not isinstance(rights.get("declaration"), str) or not rights["declaration"].strip():
        _add(findings, "SOURCE_RIGHTS_INCOMPLETE")

    sources = rights.get("sources")
    if not isinstance(sources, list) or len(sources) != 4:
        _add(findings, "SOURCE_SET_INCOMPLETE")
    else:
        for source in sources:
            try:
                path = safe_child(staging, str(source["path"]))
                data = path.read_bytes()
                jpeg_dimensions(data)
                if source.get("sha256") != sha256_bytes(data):
                    _add(findings, "ASSET_HASH_MISMATCH")
            except (KeyError, OSError, ValueError, TypeError):
                _add(findings, "SOURCE_SET_INCOMPLETE")

    if run.get("state") != "image-ready":
        _add(findings, "PRIMARY_NOT_IMAGE_READY")
    if run.get("action") != "six-independent-final-images" or run.get("route") != "B1":
        _add(findings, "ROUTE_INVALID")
    if any(run.get(key) != 6 for key in ("generation_calls", "expected_images", "actual_images")):
        _add(findings, "FINAL_SET_INCOMPLETE")
    if run.get("preview_images_included") != 0:
        _add(findings, "PREVIEW_INCLUDED")
    canvas = run.get("canvas_contract")
    if not isinstance(canvas, dict) or canvas.get("target_ratio") != "2:3" or canvas.get("all_files_match") is not True:
        _add(findings, "CANVAS_CONTRACT_INVALID")
    baseline = canvas.get("batch_canvas_baseline") if isinstance(canvas, dict) else None

    outputs = run.get("outputs")
    output_hashes: list[str] = []
    if not isinstance(outputs, list) or len(outputs) != 6:
        _add(findings, "FINAL_SET_INCOMPLETE")
    else:
        for expected, output in enumerate(outputs, start=1):
            try:
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
    if (
        not isinstance(group_qa, dict)
        or group_qa.get("requires_user_review") != []
        or not isinstance(review, dict)
        or review.get("status") != "closed"
        or review.get("reviewer") != rights.get("reviewer")
        or not isinstance(review.get("confirmation"), str)
        or not review["confirmation"].strip()
    ):
        _add(findings, "USER_REVIEW_INCOMPLETE")
    label = run.get("ai_content_label_notice")
    if not isinstance(label, dict) or label.get("status") != "informed":
        _add(findings, "AI_LABEL_NOTICE_INCOMPLETE")
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
                "expected_images": 6,
                "actual_images": 6,
                "preview_images_included": 0,
                "generation_calls": 6,
                "canvas_contract": run["canvas_contract"],
                "unique_original_output_hashes": 6,
            },
            "human_review": {
                "status": "closed",
                "reviewer": review["reviewer"],
                "reviewed_at": review["reviewed_at"],
                "confirmation": review["confirmation"],
            },
            "ai_content_label": {
                "status": "required-and-disclosed",
                "informed_at": run["ai_content_label_notice"]["informed_at"],
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
        if rights.get("status") != "promoted" or rights.get("role") != "primary" or rights.get("primary_demo_status") != "ready":
            findings.append(f"{case_dir.name}: primary promotion status is invalid")
        if rights.get("case_id") != case_dir.name:
            findings.append(f"{case_dir.name}: case identifier mismatch")
        if rights.get("ai_content_label", {}).get("status") != "required-and-disclosed":
            findings.append(f"{case_dir.name}: AI label evidence is incomplete")
        if rights.get("human_review", {}).get("status") != "closed":
            findings.append(f"{case_dir.name}: human review is incomplete")
        license_record = rights.get("media_license")
        if not isinstance(license_record, dict) or license_record.get("id") != "CC0-1.0" or license_record.get("url") != CC0_URL:
            findings.append(f"{case_dir.name}: media license is invalid")
        assets = rights.get("assets")
        if not isinstance(assets, list) or len(assets) != 10:
            findings.append(f"{case_dir.name}: primary asset set is incomplete")
            assets = []
        expected_files = {"README.md", "rights.json", "hero.jpg"}
        output_original_hashes: list[str] = []
        for asset in assets:
            path_name = asset.get("path")
            if not isinstance(path_name, str) or Path(path_name).name != path_name:
                findings.append(f"{case_dir.name}: unsafe primary asset path")
                continue
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
            if asset.get("mime") != "image/jpeg" or asset.get("bytes") != len(data) or asset.get("width") != width or asset.get("height") != height:
                findings.append(f"{case_dir.name}/{path_name}: media evidence is incomplete")
            if asset.get("role") == "generated-final":
                output_original_hashes.append(str(asset.get("original_sha256", "")))
        if len(output_original_hashes) != 6 or len(set(output_original_hashes)) != 6 or not all(SHA256.fullmatch(value) for value in output_original_hashes):
            findings.append(f"{case_dir.name}: generated output hashes are incomplete or duplicated")
        hero = rights.get("hero")
        try:
            hero_path = case_dir / str(hero["path"])
            hero_data = hero_path.read_bytes()
            hero_dimensions = jpeg_dimensions(hero_data)
        except (KeyError, TypeError, OSError, ValueError):
            findings.append(f"{case_dir.name}: social preview is invalid")
        else:
            if hero_dimensions != (1280, 640) or len(hero_data) >= 1024 * 1024 or hero.get("sha256") != sha256_bytes(hero_data):
                findings.append(f"{case_dir.name}: social preview evidence is invalid")
        actual_files = {entry.name for entry in case_dir.iterdir() if entry.is_file() and not entry.is_symlink()}
        if actual_files != expected_files or any(entry.is_symlink() or not entry.is_file() for entry in case_dir.iterdir()):
            findings.append(f"{case_dir.name}: unregistered or missing primary case artifact")
    return findings


def _zip_files(files: Iterable[tuple[Path, str]], archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path, relative in sorted(files, key=lambda item: item[1]):
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, path.read_bytes())


def build_primary_media_bundle(staging: Path, case_id: str, version: str, output_dir: Path) -> tuple[Path, Path]:
    findings = validate_staged_primary_case(staging)
    if findings:
        raise ValueError("primary demo validation failed: " + ", ".join(findings))
    output_dir.mkdir(parents=True, exist_ok=True)
    root_name = f"threadtruth-studio-{case_id}-{version}"
    archive = output_dir / f"{root_name}.zip"
    checksum = output_dir / f"{root_name}.zip.sha256"
    rights = read_json(staging / "rights-declaration.json")
    run = read_json(staging / "final-run.json")
    selected: list[tuple[Path, str]] = []
    manifest_lines: list[str] = []
    for record_name in ("rights-declaration.json", "final-run.json", "final-prompts.md"):
        path = staging / record_name
        selected.append((path, f"{root_name}/{record_name}"))
        manifest_lines.append(f"{sha256_file(path)}  {record_name}")
    for source in rights["sources"]:
        path = safe_child(staging, source["path"])
        relative = f"sources/{path.name}"
        selected.append((path, f"{root_name}/{relative}"))
        manifest_lines.append(f"{sha256_file(path)}  {relative}")
    for output in run["outputs"]:
        path = safe_child(staging, output["path"])
        relative = f"finals/{path.name}"
        selected.append((path, f"{root_name}/{relative}"))
        manifest_lines.append(f"{sha256_file(path)}  {relative}")
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest = Path(temp_dir) / "SHA256SUMS"
        manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        selected.append((manifest, f"{root_name}/SHA256SUMS"))
        _zip_files(selected, archive)
    digest = sha256_file(archive)
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def validate_style_index(root: Path) -> list[str]:
    findings: list[str] = []
    path = root.resolve() / "docs" / "demo" / "style-index.json"
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
    if sum(item.get("featured") is True for item in styles if isinstance(item, dict)) != 8:
        findings.append("style index must define exactly eight featured styles")
    if sum(item.get("full_case") in {"ready", "planned"} for item in styles if isinstance(item, dict)) != 3:
        findings.append("style index must define exactly three full primary cases")
    for item in styles:
        if not isinstance(item, dict) or item.get("status") not in {"ready", "planned"}:
            findings.append("style index contains an invalid status")
            continue
        image = item.get("representative_image")
        if item["status"] == "ready":
            if not isinstance(image, str) or not safe_child(path.parent, image).is_file():
                findings.append(f"{item.get('slug')}: ready style lacks a representative image")
        elif image is not None:
            findings.append(f"{item.get('slug')}: planned style must not claim an image")
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
    return f"""# {item['display_name']}

Status: `{item['status']}` · Featured: `{str(bool(item['featured'])).lower()}` · Full six-image case: `{full_case}`

Recommended source family: **{item['source_family']}**.

{status_note}

{visual}A style page records visual evidence only after source rights, generation approval, six-image or single-image QA as applicable, and AI-content labeling are complete. A planned page is not generation evidence.
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
    return f"""# 24-style public evidence index

Visual evidence progress: **{ready}/24 ready**. The runtime contains 24 routed packs; this page separately tracks rights-cleared public image evidence and never treats a planned card as a completed generation.

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
