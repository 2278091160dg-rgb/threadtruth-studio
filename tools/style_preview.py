"""Development-only, offline single-style preview evidence workflow.

The tool never generates images. Approval records are human attestations, not
cryptographic identity proofs; agents must never fill real visual review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import importlib.util
import json
import re
import shutil
import tempfile
from pathlib import Path


def _primary():
    spec = importlib.util.spec_from_file_location("preview_primary", Path(__file__).with_name("primary_demo.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CASE = "white-hooded-puffer-vest-korean-cold"
SOURCE_REF = f"docs/demo/primary-cases/{CASE}/rights.json"
PACK_ROOT = "skills/threadtruth-studio/references/styles"
RULE_PATHS = {
    "prompt_build": "skills/threadtruth-studio/references/prompt-build.md",
    "modes_scenes": "skills/threadtruth-studio/references/modes-scenes.md",
    "safety_core": "skills/threadtruth-studio/references/safety-core.md",
    "style_router": "skills/threadtruth-studio/references/style-router.md",
}
AI_LABEL = "AI-generated style preview — not six independent final images."
PREVIEW_MARK = "AI生成 · 方向预览 · 非成片 / PREVIEW ONLY — NOT FINAL"
CURRENT_SCHEMA = "3.0"
LEGACY_SCHEMAS = {"1.0", "2.0"}
MODE_NAMES = {"B": "棚拍版", "C": "场景版", "D": "混合版"}
LAYOUT_CONTRACT = {
    "board_aspect_ratio": "1:1",
    "rows": 2,
    "columns": 3,
    "cell_aspect_ratio": "3:4",
    "label_bands": ["title", "subtitle", "footer"],
    "framing": ["full-body", "full-body", "half-body-permitted", "full-body", "half-body-permitted", "full-body"],
}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
HASH = re.compile(r"[a-f0-9]{64}")
MAX_BYTES = 8 * 1024 * 1024
GENERATED_FIELDS = {"path", "sha256", "width", "height", "bytes", "original_sha256", "generation", "human_review"}


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def object_hash(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def child(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("unsafe path")
    root = root.resolve()
    candidate = root / relative
    if any(path.is_symlink() for path in [candidate, *candidate.parents] if path != root and root in path.parents):
        raise ValueError("symlink forbidden")
    if root not in candidate.resolve().parents:
        raise ValueError("unsafe path")
    return candidate


def run_dir(root, run_id):
    if not isinstance(run_id, str) or not ID.fullmatch(run_id):
        raise ValueError("invalid run id")
    return child(root, f".threadtruth/style-previews/{run_id}")


def _field(text, field):
    match = re.search(rf"^{re.escape(field)}:\s*([^\n]*)(?:\n((?:[ \t]+[^\n]*\n?)*))?", text, re.M)
    if not match:
        raise ValueError(f"pack missing {field}")
    value, continuation = match.groups()
    if value.strip() in {">", "|", ""}:
        return " ".join((continuation or "").split())
    return value.split("#", 1)[0].strip().strip('"\'')


def _list_field(text, field):
    inline = _field(text, field)
    if inline.startswith("[") and inline.endswith("]"):
        return [item.strip().strip('"\'') for item in inline[1:-1].split(",") if item.strip()]
    match = re.search(rf"^{re.escape(field)}:\s*\n((?:\s+-[^\n]+\n?)+)", text, re.M)
    if match:
        return [line.split("-", 1)[1].strip() for line in match.group(1).splitlines()]
    return [inline]


def _visual(text):
    visual = _field(text, "visual_language")
    clauses = re.split(r"[;,]", visual)
    excluded = re.compile(
        r"garment|reference|silhouette|tailor|cashmere|wool|tweed|silk|linen|logo|denim|leather|dress|skirt|ribbon|lace|pleat|uniform|embroid|collar|button|construction|nylon|shirting|knitwear|proportions|layering|metallic accents|cotton|tulle|bows|feminine details|oriental structure",
        re.I,
    )
    mood = "; ".join(
        clause.strip() for clause in clauses
        if clause.strip() and not excluded.search(clause) and clause.strip() not in {"do not add", "remove"}
    )
    mood = re.sub(r"\bmenswear\b", "urban", mood, flags=re.I)
    return {"mood": mood, "persona": _field(text, "model_persona"), "lighting": _field(text, "lighting_palette")}


def _source(root):
    primary = _primary()
    if primary.validate_public_primary_cases(root):
        raise ValueError("source primary evidence invalid")
    path = child(root, SOURCE_REF)
    rights = read_json(path)
    authorization = rights["source_rights"]
    required = ("public_use_authorized", "project_media_policy_accepted", "source_model_display_authorized")
    if rights["case_id"] != CASE or not all(authorization.get(key) is True for key in required):
        raise ValueError("source rights incomplete")
    sources = [asset for asset in rights["assets"] if asset["role"] == "source"]
    if len(sources) != 4:
        raise ValueError("four authorized sources required")
    base = str(Path(SOURCE_REF).parent)
    source = {
        "rights_ref": SOURCE_REF,
        "rights_sha256": digest(path.read_bytes()),
        "authorization": authorization,
        "assets": [
            {"path": f"{base}/{asset['path']}", "sha256": asset["public_sha256"], "role": "garment-source"}
            for asset in sources
        ],
    }
    anchor = next(asset for asset in rights["assets"] if asset["name"] == "look-1")
    return source, {"path": f"{base}/{anchor['path']}", "sha256": anchor["public_sha256"], "role": "identity-only"}


def _rules(root):
    return {
        name: {"path": relative, "sha256": digest(child(root, relative).read_bytes())}
        for name, relative in RULE_PATHS.items()
    }


def _canonical_action_zero(root):
    text = child(root, RULE_PATHS["prompt_build"]).read_text(encoding="utf-8")
    pose_section = text.split("## 1. 六个原始姿势母版", 1)[1].split("## 1a.", 1)[0]
    poses = []
    for line in pose_section.splitlines():
        match = re.match(r"^\|\s*([1-6])\s*\|\s*([^|]+?)\s*\|\s*([A-Z_]+)\s*\|$", line)
        if match:
            poses.append({"ordinal": int(match.group(1)), "description": match.group(2).strip(), "master": match.group(3)})
    gaze_section = text.split("## 2. 头部方向 / 视线", 1)[1].split("## 3.", 1)[0]
    gazes = {}
    for line in gaze_section.splitlines():
        match = re.match(r"^\|\s*([1-6])\s*\|\s*([^|]+?)\s*\|$", line)
        if match:
            gazes[int(match.group(1))] = match.group(2).strip()
    negative_section = text.split("### 3b. 预览阶段负面词", 1)[1]
    negative_match = re.search(r"```\n(.*?)```", negative_section, re.S)
    if len(poses) != 6 or set(gazes) != set(range(1, 7)) or negative_match is None:
        raise ValueError("canonical action-0 rules are incomplete")
    for pose in poses:
        pose["head_gaze"] = gazes[pose["ordinal"]]
        pose["row"] = (pose["ordinal"] - 1) // 3 + 1
        pose["column"] = (pose["ordinal"] - 1) % 3 + 1
    return poses, " ".join(negative_match.group(1).split())


def _registered_packs(root):
    router = child(root, RULE_PATHS["style_router"]).read_text(encoding="utf-8")
    packs = []
    for path in sorted(child(root, PACK_ROOT).glob("*.pack.yaml")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        style = path.stem.removesuffix(".pack")
        if _field(text, "slug") != style:
            raise ValueError("pack slug mismatch")
        if not re.search(rf"\|\s*{re.escape(style)}\s*\|", router):
            raise ValueError(f"style {style} missing from runtime registry")
        packs.append((style, path, text))
    if len(packs) != 24 or len({style for style, _, _ in packs}) != 24:
        raise ValueError("runtime registry must contain 24 unique style packs")
    return packs


def _mode_scene(mode, scenes, ordinal):
    if mode == "B" or (mode == "D" and ordinal <= 2):
        return "low-distraction white or light-gray studio background"
    return scenes[ordinal - 1]


def _prompt(preview, source, anchor, preview_negative):
    visual = preview["visual"]
    lines = [
        f"Create one action-0 preview for style {preview['style']}.",
        "Use a single 2x3 grid contact-sheet preview on a square 1:1 board showing the SAME one white hooded puffer vest in six different directions.",
        "Top row poses 1-2-3; bottom row poses 4-5-6. Six equal 3:4 portrait cells, one pose per cell, one adult female model identity throughout this sheet.",
        "Reserve independent title, subtitle and footer bands outside all six pose cells; keep the three text bands distinct and clear of every subject.",
        f"Render this exact full bilingual title natively at the top: {preview['label_contract']['title']}",
        f"Render this exact subtitle natively below the title: {preview['label_contract']['subtitle']}",
        f"Render this exact disclosure natively in the footer: {preview['label_contract']['footer']}",
        "Attached images 1-4 are the only authoritative garment truth. Preserve the white color, hood, zipper, length, padding, seams and construction.",
        "Never replace or redesign the vest and never invent details. Keep it clearly visible in every cell.",
        "Attached image 5 is identity-only: preserve face, hair, apparent age and body proportions; never treat it as garment authority.",
        "Style changes mood, low-distraction background, pose treatment and lighting only; source truth overrides every style-pack suggestion.",
        f"Mode: {preview['mode']} derived from the registered pack default and runtime mode rules.",
        f"Mood only: {visual['mood']}",
        f"Attitude: {visual['persona']}",
        f"Lighting/background palette: {visual['lighting']}",
        "This is a LOW-RES DIRECTION PREVIEW, not a final deliverable. Keep the footer visible and unobtrusive, no larger than about 3-4% of image height.",
        "All requested text must be native-rendered in the generated board. Never cover the model, face, vest, shoes, bag or pose. Do not place a large centered watermark.",
        "Garment references: " + ", ".join(asset["path"] for asset in source["assets"]),
        "Identity-only reference: " + anchor["path"],
    ]
    for pose in preview["poses"]:
        lines.extend([
            "",
            f"POSE {pose['ordinal']} / row {pose['row']} column {pose['column']}: {pose['master']} — {pose['description']}",
            f"Head/gaze: {pose['head_gaze']}",
            f"Mode/scene: {pose['scene']}",
            f"Framing: {preview['layout_contract']['framing'][pose['ordinal'] - 1]}",
            "Retain white vest color and every visible source construction detail.",
        ])
    lines.extend([
        "",
        "Preview negative (grid is intentionally allowed): " + preview_negative,
        "Style negative append: " + ", ".join(preview["negative_delta_add"]),
    ])
    return "\n".join(lines) + "\n"


def _plan(root, run_id):
    run_dir(root, run_id)
    source, anchor = _source(root)
    rules = _rules(root)
    canonical_poses, preview_negative = _canonical_action_zero(root)
    previews = []
    for style, path, text in _registered_packs(root):
        relative = f"{PACK_ROOT}/{path.name}"
        mode = _field(text, "default_mode")
        if mode not in {"B", "C", "D"} or _field(text, "pose_masters") != "inherit":
            raise ValueError(f"unsupported runtime pose or mode contract for {style}")
        scenes = _list_field(text, "scenes")
        if len(scenes) != 6:
            raise ValueError(f"style {style} must provide six scenes")
        poses = copy.deepcopy(canonical_poses)
        for pose in poses:
            pose["scene"] = _mode_scene(mode, scenes, pose["ordinal"])
        raw = path.read_bytes()
        preview = {
            "style": style,
            "display_name": _field(text, "name"),
            "pack": {"path": relative, "sha256": digest(raw), "version": _field(text, "version")},
            "mode": mode,
            "visual": _visual(text),
            "negative_delta_add": _list_field(text, "negative_delta_add"),
            "poses": poses,
            "layout_contract": copy.deepcopy(LAYOUT_CONTRACT),
            "label_contract": {
                "title": _field(text, "name"),
                "subtitle": f"同款白马甲 · {mode} {MODE_NAMES[mode]} · 六姿势预览",
                "footer": PREVIEW_MARK,
            },
        }
        preview["prompt_sha256"] = digest(_prompt(preview, source, anchor, preview_negative).encode())
        previews.append(preview)
    return {
        "schema_version": CURRENT_SCHEMA, "run_id": run_id, "role": "style-preview", "status": "prepared",
        "source": source, "identity_anchor": anchor, "rules": rules, "ai_label": AI_LABEL, "previews": previews,
    }


def _legacy_error(schema):
    return f"preview schema {schema} is superseded historical evidence, not approved for current standard; it is read-only and cannot be prepared, ingested, approved or promoted"


def prepare(root, run_id):
    directory = run_dir(root, run_id)
    if directory.exists():
        existing = read_json(directory / "evidence.json")
        if existing.get("schema_version") in LEGACY_SCHEMAS:
            raise ValueError(_legacy_error(existing.get("schema_version")))
        _check_plan(root, existing, directory)
        return existing
    plan = _plan(root, run_id)
    directory.mkdir(parents=True)
    (directory / "prompts").mkdir()
    _, preview_negative = _canonical_action_zero(root)
    for preview in plan["previews"]:
        child(directory, f"prompts/{preview['style']}.txt").write_text(
            _prompt(preview, plan["source"], plan["identity_anchor"], preview_negative), encoding="utf-8"
        )
    write_json(directory / "evidence.json", plan)
    return plan


def _check_plan(root, record, directory=None):
    if record.get("schema_version") in LEGACY_SCHEMAS:
        raise ValueError(_legacy_error(record.get("schema_version")))
    if record.get("schema_version") != CURRENT_SCHEMA:
        raise ValueError("unsupported preview schema")
    if record.get("status") not in {"prepared", "awaiting-human-review", "approved"}:
        raise ValueError("invalid preview state")
    if directory is not None and record.get("run_id") != directory.name:
        raise ValueError("run id mismatch")
    expected = _plan(root, record["run_id"])
    if set(record) != set(expected):
        raise ValueError("unexpected evidence fields")
    for key in ("schema_version", "run_id", "role", "source", "identity_anchor", "rules", "ai_label"):
        if record.get(key) != expected[key]:
            raise ValueError(f"stale or invalid {key}")
    actual_previews = record.get("previews")
    if not isinstance(actual_previews, list) or len(actual_previews) != 24:
        raise ValueError("24 previews required")
    if len({preview.get("style") for preview in actual_previews if isinstance(preview, dict)}) != 24:
        raise ValueError("24 unique preview styles required")
    for preview, planned in zip(actual_previews, expected["previews"]):
        if not isinstance(preview, dict) or set(preview) - (set(planned) | GENERATED_FIELDS):
            raise ValueError("unexpected preview fields")
        if any(preview.get(key) != value for key, value in planned.items()):
            raise ValueError("stale pack, prompt, mode or pose mapping")
        poses = preview.get("poses")
        if not isinstance(poses, list) or [pose.get("ordinal") for pose in poses if isinstance(pose, dict)] != list(range(1, 7)):
            raise ValueError("six unique canonical pose IDs required")
        if any(set(pose) != set(planned["poses"][index]) for index, pose in enumerate(poses)):
            raise ValueError("mixed-style or malformed pose record")
        if directory is not None:
            prompt = child(directory, f"prompts/{preview['style']}.txt")
            if digest(prompt.read_bytes()) != preview["prompt_sha256"]:
                raise ValueError("prompt hash mismatch")
    generated = [preview for preview in actual_previews if "generation" in preview]
    calls = [preview.get("generation", {}).get("call_id") for preview in generated]
    originals = [preview.get("original_sha256") for preview in generated]
    optimized = [preview.get("sha256") for preview in generated]
    if len(calls) != len(set(calls)) or len(originals) != len(set(originals)) or len(optimized) != len(set(optimized)):
        raise ValueError("duplicate native call or preview hash")


def _image(path):
    from PIL import Image
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("preview exceeds optimized image limit")
    with Image.open(path) as image:
        image.load()
        if image.format != "JPEG" or min(image.width, image.height) < 600:
            raise ValueError("preview requires a readable JPEG whole sheet")
        if image.getexif() or image.info.get("comment") or image.info.get("icc_profile"):
            raise ValueError("preview contains embedded metadata")
        return {"sha256": digest(data), "bytes": len(data), "width": image.width, "height": image.height}


def _generation(generation, preview):
    if not isinstance(generation, dict) or set(generation) != {"tool", "call_id", "generated_at", "prompt_sha256"}:
        raise ValueError("generation record fields invalid")
    if generation["tool"] != "native-imagegen" or not isinstance(generation["call_id"], str) or not ID.fullmatch(generation["call_id"]):
        raise ValueError("native generation call required")
    if generation["prompt_sha256"] != preview["prompt_sha256"]:
        raise ValueError("generation prompt mismatch")
    _primary().parse_iso_z(generation["generated_at"])


def _find_preview(record, style):
    if not isinstance(style, str) or not ID.fullmatch(style):
        raise ValueError("registered style required")
    preview = next((item for item in record.get("previews", []) if item.get("style") == style), None)
    if preview is None:
        raise ValueError("registered style required")
    return preview


def _receipt_bindings(record, preview):
    return {
        "style": preview["style"], "source_sha256": object_hash(record["source"]),
        "rules_sha256": object_hash(record["rules"]), "pack_sha256": preview["pack"]["sha256"],
        "prompt_sha256": preview["prompt_sha256"],
        "layout_contract_sha256": object_hash(preview["layout_contract"]),
        "label_contract_sha256": object_hash(preview["label_contract"]),
    }


def _native_dimensions(path):
    from PIL import Image, ImageOps
    with Image.open(path) as opened:
        if opened.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("unsupported native image format")
        oriented = ImageOps.exif_transpose(opened)
        oriented.load()
        return [oriented.width, oriented.height]


def ingest(root, run_id, style, image, generation):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    _check_plan(root, record, directory)
    preview = _find_preview(record, style)
    if record["status"] not in {"prepared", "awaiting-human-review"}:
        raise ValueError("invalid ingest state")
    _generation(generation, preview)
    original = digest(image.read_bytes())
    if "path" in preview:
        expected = {key: preview[key] for key in ("sha256", "bytes", "width", "height")}
        if preview["original_sha256"] == original and preview["generation"] == generation and _image(child(directory, preview["path"])) == expected:
            return record
        raise ValueError("refuse to overwrite registered preview")
    for other in record["previews"]:
        if other.get("generation", {}).get("call_id") == generation["call_id"]:
            raise ValueError("duplicate native call")
        if other.get("original_sha256") == original:
            raise ValueError("duplicate native output")
    target = child(directory, f"{style}.jpg")
    receipt = child(directory, f"native-receipts/{style}.json")
    if target.exists() or receipt.exists():
        raise ValueError("refuse to overwrite unregistered asset")
    from PIL import Image, ImageOps
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        output = Path(temporary) / "preview.jpg"
        with Image.open(image) as opened:
            extension = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}.get(opened.format)
            if extension is None:
                raise ValueError("unsupported native image format")
            native_relative = f"native-outputs/{style}.{extension}"
            native = child(directory, native_relative)
            if native.exists():
                raise ValueError("refuse to overwrite native output")
            oriented = ImageOps.exif_transpose(opened)
            native_dimensions = [oriented.width, oriented.height]
            oriented.convert("RGB").save(output, "JPEG", quality=86, optimize=True, progressive=True)
        metadata = _image(output)
        if any(other.get("sha256") == metadata["sha256"] for other in record["previews"]):
            raise ValueError("duplicate optimized preview")
        shutil.copyfile(output, target)
    native.parent.mkdir(exist_ok=True)
    shutil.copyfile(image, native)
    receipt.parent.mkdir(exist_ok=True)
    write_json(receipt, {
        "native_output_path": str(image.resolve()), "retained_path": native_relative,
        "native_dimensions": native_dimensions, "original_sha256": original,
        "generation": generation, "bindings": _receipt_bindings(record, preview),
    })
    preview.update(metadata, path=target.name, original_sha256=original, generation=generation)
    record["status"] = "awaiting-human-review"
    write_json(directory / "evidence.json", record)
    write_json(directory / f"review-template-{style}.json", review_template(record, style))
    return record


def confirmation(style):
    return f"I reviewed the complete six-pose {style} preview against the authorized sources."


def _review_hash(record, preview):
    return object_hash({
        "source": record["source"], "identity_anchor": record["identity_anchor"], "rules": record["rules"],
        "preview": {key: value for key, value in preview.items() if key != "human_review"},
    })


def review_template(record, style):
    preview = _find_preview(record, style)
    return {
        "reviewer": "", "reviewed_at": "", "confirmation": "", "preview_sha256": preview.get("sha256", ""),
        "evidence_sha256": _review_hash(record, preview), "public_use_approved": False,
        "geometry": {
            "cells": [None, None, None, None, None, None],
            "title": None,
            "subtitle": None,
            "footer": None,
        },
        "checks": {
            "observed_boundaries": "pending",
            "full_bilingual_title": "pending",
            "correct_subtitle": "pending",
            "readable_ai_footer": "pending",
            "text_subject_non_overlap": "pending",
        },
        "poses": [
            {
                "ordinal": ordinal, "product": "pending", "pose_layout": "pending",
                "identity_style": "pending", "ai_disclosure": "pending", "framing": "pending",
            }
            for ordinal in range(1, 7)
        ],
    }


def _rect(value, width, height):
    if not isinstance(value, list) or len(value) != 4 or any(type(item) is not int for item in value):
        raise ValueError("observed geometry invalid")
    x, y, rect_width, rect_height = value
    if x < 0 or y < 0 or rect_width <= 0 or rect_height <= 0 or x + rect_width > width or y + rect_height > height:
        raise ValueError("observed geometry invalid")
    return value


def _overlap(first, second):
    return (
        first[0] < second[0] + second[2]
        and second[0] < first[0] + first[2]
        and first[1] < second[1] + second[3]
        and second[1] < first[1] + first[3]
    )


def _check_geometry(geometry, width, height):
    if not isinstance(geometry, dict) or set(geometry) != {"cells", "title", "subtitle", "footer"}:
        raise ValueError("observed geometry invalid")
    cells = geometry["cells"]
    if not isinstance(cells, list) or len(cells) != 6:
        raise ValueError("observed geometry invalid")
    cells = [_rect(value, width, height) for value in cells]
    title = _rect(geometry["title"], width, height)
    subtitle = _rect(geometry["subtitle"], width, height)
    footer = _rect(geometry["footer"], width, height)
    rectangles = [*cells, title, subtitle, footer]
    if any(_overlap(first, second) for index, first in enumerate(rectangles) for second in rectangles[index + 1:]):
        raise ValueError("observed geometry invalid")
    widths = [cell[2] for cell in cells]
    heights = [cell[3] for cell in cells]
    if max(widths) - min(widths) > 1 or max(heights) - min(heights) > 1:
        raise ValueError("observed geometry invalid")
    if any(abs(4 * cell[2] - 3 * cell[3]) > 4 for cell in cells):
        raise ValueError("observed geometry invalid")
    top, bottom = cells[:3], cells[3:]
    if max(cell[1] for cell in top) - min(cell[1] for cell in top) > 1:
        raise ValueError("observed geometry invalid")
    if max(cell[1] for cell in bottom) - min(cell[1] for cell in bottom) > 1:
        raise ValueError("observed geometry invalid")
    if any(abs(top[index][0] - bottom[index][0]) > 1 for index in range(3)):
        raise ValueError("observed geometry invalid")
    if any(row[index][0] + row[index][2] > row[index + 1][0] for row in (top, bottom) for index in range(2)):
        raise ValueError("observed geometry invalid")
    if max(cell[1] + cell[3] for cell in top) > min(cell[1] for cell in bottom):
        raise ValueError("observed geometry invalid")
    first_row_y = min(cell[1] for cell in top)
    last_row_bottom = max(cell[1] + cell[3] for cell in bottom)
    if title[1] + title[3] > subtitle[1] or subtitle[1] + subtitle[3] > first_row_y:
        raise ValueError("observed geometry invalid")
    if footer[1] < last_row_bottom:
        raise ValueError("observed geometry invalid")


def _check_review(record, preview):
    review = preview.get("human_review")
    template = review_template(record, preview["style"])
    if not isinstance(review, dict) or set(review) != set(template):
        raise ValueError("human review incomplete")
    if not _primary().GITHUB_REVIEWER.fullmatch(str(review["reviewer"])) or review["confirmation"] != confirmation(preview["style"]):
        raise ValueError("human review incomplete")
    if review["public_use_approved"] is not True or review["preview_sha256"] != preview.get("sha256") or review["evidence_sha256"] != template["evidence_sha256"]:
        raise ValueError("human review incomplete")
    if review["checks"] != {key: "pass" for key in template["checks"]}:
        raise ValueError("human review incomplete")
    if len(review["poses"]) != 6:
        raise ValueError("human review incomplete")
    for ordinal, pose in enumerate(review["poses"], start=1):
        expected = {
            "ordinal": ordinal, "product": "pass", "pose_layout": "pass",
            "identity_style": "pass", "ai_disclosure": "pass", "framing": "pass",
        }
        if pose != expected:
            raise ValueError("human review incomplete")
    _check_geometry(review["geometry"], preview["width"], preview["height"])
    if _primary().parse_iso_z(review["reviewed_at"]) < _primary().parse_iso_z(preview["generation"]["generated_at"]):
        raise ValueError("review predates generation")


def _validate_preview(record, preview, directory, require_approval, local):
    style = preview["style"]
    if preview.get("path") != f"{style}.jpg":
        raise ValueError("missing native output" if "path" not in preview else "preview path invalid")
    actual = _image(child(directory, preview["path"]))
    if any(preview.get(key) != value for key, value in actual.items()):
        raise ValueError("preview hash or metadata mismatch")
    if actual["width"] != actual["height"]:
        raise ValueError("preview board must be square")
    if not HASH.fullmatch(str(preview.get("original_sha256"))):
        raise ValueError("original preview hash missing")
    _generation(preview.get("generation"), preview)
    if local:
        receipt = read_json(child(directory, f"native-receipts/{style}.json"))
        if receipt.get("generation") != preview["generation"] or receipt.get("original_sha256") != preview["original_sha256"]:
            raise ValueError("native receipt mismatch")
        if receipt.get("bindings") != _receipt_bindings(record, preview):
            raise ValueError("native receipt binding mismatch")
        native = child(directory, receipt["retained_path"])
        if digest(native.read_bytes()) != preview["original_sha256"]:
            raise ValueError("native output hash mismatch")
        if receipt.get("native_dimensions") != _native_dimensions(native):
            raise ValueError("native output dimensions mismatch")
        if receipt["native_dimensions"][0] != receipt["native_dimensions"][1]:
            raise ValueError("preview board must be square")
    if _primary().parse_iso_z(preview["generation"]["generated_at"]) < _primary().parse_iso_z(record["source"]["authorization"]["declared_at"]):
        raise ValueError("generation predates source authorization")
    if require_approval or "human_review" in preview:
        _check_review(record, preview)


def audit(root, run_id, style=None, require_approval=False):
    try:
        directory = run_dir(root, run_id)
        record = read_json(directory / "evidence.json")
        if record.get("schema_version") in LEGACY_SCHEMAS:
            return [_legacy_error(record.get("schema_version"))]
        _check_plan(root, record, directory)
        selected = [_find_preview(record, style)] if style is not None else record["previews"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
        return [str(error)]
    findings = []
    for preview in selected:
        try:
            _validate_preview(record, preview, directory, require_approval or style is None, True)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
            findings.append(f"{preview['style']}: {error}")
    if _primary().has_sensitive_public_text(record):
        findings.append("sensitive public text")
    return findings


def approve(root, run_id, style, review):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    _check_plan(root, record, directory)
    preview = _find_preview(record, style)
    _validate_preview(record, preview, directory, False, True)
    if "human_review" in preview:
        if preview["human_review"] == review:
            return record
        raise ValueError("refuse to overwrite human approval")
    preview["human_review"] = copy.deepcopy(review)
    _check_review(record, preview)
    record["status"] = "approved" if all("human_review" in item for item in record["previews"]) else "awaiting-human-review"
    write_json(directory / "evidence.json", record)
    return record


def _legacy_html(record):
    schema = html.escape(str(record.get("schema_version", "unknown")))
    candidates = [*record.get("boards", []), *record.get("previews", [])]
    images = []
    for item in candidates:
        path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", path):
            continue
        width, height = item.get("width"), item.get("height")
        dimensions = (
            f' width="{width}" height="{height}"'
            if type(width) is int and type(height) is int and width > 0 and height > 0
            else ""
        )
        escaped = html.escape(path)
        images.append(
            f'<li><a href="{escaped}"><img src="{escaped}"{dimensions} '
            'alt="Historical preview image; not approved for current standard"></a></li>'
        )
    image_list = "<ul>" + "".join(images) + "</ul>" if images else "<p>No retained image path is recorded.</p>"
    return (
        f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<title>Historical v{schema[0]} preview</title><style>body{{max-width:900px;margin:2rem auto;font-family:system-ui}}'
        'img{display:block;width:auto;max-width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}'
        'a:focus-visible{outline:3px solid currentColor}</style>'
        f'<body><h1>Historical v{schema[0]} preview — read only</h1><p>Legacy evidence: not approved for current standard. '
        'Any earlier pass label is historical only; this record cannot be promoted.</p>'
        f'{image_list}<pre>{html.escape(json.dumps(record, ensure_ascii=False, indent=2))}</pre></body></html>\n'
    )


def _review_label(record, preview, directory, local):
    if "human_review" not in preview:
        return "not approved"
    try:
        _validate_preview(record, preview, directory, True, local)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        return "review invalid / pending"
    return "approved"


def _html(record, style=None, directory=None, local=False):
    previews = [_find_preview(record, style)] if style is not None else record["previews"]
    sections = []
    for preview in previews:
        visual = (
            f'<a href="{html.escape(preview["path"])}"><img src="{html.escape(preview["path"])}" '
            f'width="{int(preview["width"])}" height="{int(preview["height"])}" '
            f'alt="Complete {html.escape(preview["style"])} six-pose preview sheet"></a>'
            if "path" in preview else "<p>Not generated</p>"
        )
        poses = "".join(
            f"<li><strong>{pose['ordinal']}: {html.escape(pose['master'])}</strong><br>"
            f"{html.escape(pose['description'])}<br><small>{html.escape(pose['head_gaze'])}</small></li>"
            for pose in preview["poses"]
        )
        review = _review_label(record, preview, directory, local)
        sections.append(
            f"<section><h2>{html.escape(preview['display_name'])}</h2><p><code>{html.escape(preview['style'])}</code></p>"
            f"{visual}<p>{review}</p><ol>{poses}</ol></section>"
        )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Style preview review</title><style>body{max-width:1200px;margin:2rem auto;font-family:system-ui}'
        'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:2rem}'
        'section{min-width:0}img{display:block;width:auto;max-width:100%;height:auto}'
        'ol{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding-left:1.5rem}'
        'li{min-width:0;overflow-wrap:anywhere;word-break:break-word}'
        '@media(max-width:480px){ol{grid-template-columns:1fr}}</style><body>'
        f'<h1>{AI_LABEL}</h1><p>24 single-style, six-pose sheets. Every thumbnail is the complete sheet; click it for the original display image. '
        'Ungenerated entries are text only. Machine checks cannot prove pose layout or visual content.</p><main>'
        + "".join(sections) + "</main></body></html>\n"
    )


def gallery(root, run_id, style=None):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    if record.get("schema_version") in LEGACY_SCHEMAS:
        content, filename = _legacy_html(record), "gallery.html"
    else:
        _check_plan(root, record, directory)
        content = _html(record, style, directory, True)
        filename = f"gallery-{style}.html" if style else "gallery.html"
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def _readme(record):
    return f"""# Style preview collection: {record['run_id']}

{AI_LABEL}

[Review all 24 whole sheets](index.html). Each entry is one registered style applied to the same authorized garment in the six canonical action-0 poses. The gallery always displays the complete sheet; it does not crop or upscale cells.

Source authorization: [primary rights](../../primary-cases/{CASE}/rights.json). Four real garment sources remain authoritative; look-1 is identity-only.

[evidence.json](evidence.json) binds source rights, runtime rule hashes, actual pack versions/hashes, exact prompts, 24 native calls, observed JPEG metadata and per-sheet six-pose human review. Machine verification does not judge subjective visual quality, infer a six-pose layout from dimensions, or authenticate reviewer identity.

CC0 applies only to the extent the project can grant rights; Apache-2.0 does not cover media. AI-generated content requires applicable labeling. These previews never count as independent finals or runtime maturity evidence.
"""


def _public_record_valid(root, record, directory):
    _check_plan(root, record)
    if record["status"] != "approved":
        raise ValueError("public preview collection is not approved")
    for preview in record["previews"]:
        _validate_preview(record, preview, directory, True, False)
    if _primary().has_sensitive_public_text(record):
        raise ValueError("sensitive public text")


def validate_public_previews(root):
    base = child(root, "docs/demo/style-previews")
    if not base.exists():
        return []
    findings = []
    for directory in sorted(base.iterdir()):
        try:
            if directory.is_symlink() or not directory.is_dir() or not ID.fullmatch(directory.name):
                raise ValueError("orphan or unsafe preview entry")
            record = read_json(directory / "evidence.json")
            if record.get("schema_version") in LEGACY_SCHEMAS:
                raise ValueError("historical preview evidence cannot be public under current display standard")
            if record["run_id"] != directory.name:
                raise ValueError("run id mismatch")
            _public_record_valid(root, record, directory)
            expected = {"evidence.json", "README.md", "index.html", *[f"{item['style']}.jpg" for item in record["previews"]]}
            if {path.name for path in directory.iterdir()} != expected or any(path.is_symlink() or not path.is_file() for path in directory.iterdir()):
                raise ValueError("unregistered or missing preview artifact")
            if (directory / "README.md").read_text() != _readme(record) or (directory / "index.html").read_text() != _html(record, directory=directory):
                raise ValueError("stale preview disclosure or gallery")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
            findings.append(f"{directory.name}: {error}")
    return findings


def _links_from_record(record):
    return {
        preview["style"]: {
            "run_id": record["run_id"], "style": preview["style"],
            "path": f"style-previews/{record['run_id']}/{preview['path']}", "sha256": preview["sha256"],
        }
        for preview in record["previews"]
    }


def preview_links(root):
    findings = validate_public_previews(root)
    if findings:
        raise ValueError("; ".join(findings))
    links = {}
    for path in sorted(child(root, "docs/demo/style-previews").glob("*/evidence.json")):
        record = read_json(path)
        for style, link in _links_from_record(record).items():
            if style in links:
                raise ValueError("multiple approved previews for one style")
            links[style] = link
    return links


def _project_preview(root, record):
    index_path = child(root, "docs/demo/style-index.json")
    index = read_json(index_path)
    links = _links_from_record(record)
    if {item.get("slug") for item in index.get("styles", [])} != set(links):
        raise ValueError("style index and approved previews differ")
    for item in index["styles"]:
        item["preview"] = links[item["slug"]]
    primary = _primary()
    tracked = [index_path, *primary.expected_style_pages(root), child(root, "docs/demo/RIGHTS.md")]
    backups = {path: path.read_bytes() if path.exists() else None for path in tracked}
    try:
        _atomic_json(index_path, index)
        primary.render_style_pages(root)
        primary.render_rights_index(root)
        findings = [
            *validate_public_previews(root),
            *primary.validate_style_index(root),
            *primary.validate_style_pages(root),
        ]
        if findings:
            raise ValueError("public preview projection validation failed: " + "; ".join(findings))
    except Exception:
        for path, data in backups.items():
            if data is None:
                if path.exists():
                    path.unlink()
            else:
                path.write_bytes(data)
        raise


def promote(root, run_id):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    if record.get("schema_version") in LEGACY_SCHEMAS:
        raise ValueError(_legacy_error(record.get("schema_version")))
    _check_plan(root, record, directory)
    unapproved = [preview["style"] for preview in record["previews"] if "human_review" not in preview]
    if unapproved:
        raise ValueError("unapproved styles: " + ", ".join(unapproved))
    findings = audit(root, run_id, require_approval=True)
    if findings:
        raise ValueError("; ".join(findings))
    if record["status"] != "approved":
        raise ValueError("approval state invalid")
    target = child(root, f"docs/demo/style-previews/{run_id}")
    if target.exists():
        if read_json(target / "evidence.json") != record or validate_public_previews(root):
            raise ValueError("refuse to overwrite different or invalid public evidence")
        _project_preview(root, record)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        stage = Path(temporary) / "public"
        stage.mkdir()
        for preview in record["previews"]:
            shutil.copyfile(child(directory, preview["path"]), stage / preview["path"])
        write_json(stage / "evidence.json", record)
        (stage / "README.md").write_text(_readme(record), encoding="utf-8")
        (stage / "index.html").write_text(_html(record, directory=stage), encoding="utf-8")
        created_target = False
        try:
            stage.rename(target)
            created_target = True
            _project_preview(root, record)
        except Exception:
            if created_target:
                shutil.rmtree(target)
            raise
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "ingest", "audit", "gallery", "approve", "promote"):
        command = commands.add_parser(name)
        command.add_argument("--run-id", required=True)
        if name in {"ingest", "audit", "gallery", "approve"}:
            command.add_argument("--style")
        if name == "ingest":
            command.add_argument("--board", help=argparse.SUPPRESS)
            command.add_argument("--image", type=Path, required=True)
            command.add_argument("--generation-record", type=Path, required=True)
        if name == "approve":
            command.add_argument("--review", type=Path, required=True, help="Completed human review JSON; agents must never fill real QA.")
    args = parser.parse_args(argv)
    if args.command == "ingest" and args.board:
        parser.error("--board is superseded; use --style <registered-slug>")
    if args.command in {"ingest", "approve"} and not args.style:
        parser.error(f"{args.command} requires --style <registered-slug>")
    try:
        if args.command == "ingest":
            result = ingest(args.root, args.run_id, args.style, args.image, read_json(args.generation_record))
        elif args.command == "approve":
            result = approve(args.root, args.run_id, args.style, read_json(args.review))
        elif args.command in {"audit", "gallery"}:
            result = globals()[args.command](args.root, args.run_id, style=args.style)
        else:
            result = globals()[args.command](args.root, args.run_id)
        print(str(result) if isinstance(result, Path) else json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "audit" and result else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
