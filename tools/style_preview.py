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


def _demo_media():
    spec = importlib.util.spec_from_file_location("preview_demo_media", Path(__file__).with_name("demo_media.py"))
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
MODEL_DOCS_URL = "https://learn.chatgpt.com/docs/image-generation"
MODEL_DOCS_VERIFIED_AT = "2026-09-14"
REPRESENTATIVE_COLLECTION_ID = "white-vest-24-v1"
HISTORICAL_SCHEMAS = {"1.0", "2.0", "3.0"}
LEGACY_SCHEMAS = HISTORICAL_SCHEMAS
FROZEN_PUBLIC_SCHEMA = "4.0"
CURRENT_SCHEMA = "5.0"
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
GENERATED_FIELDS = {
    "path", "sha256", "width", "height", "bytes", "original_sha256",
    "generation", "correction", "failed_retry", "human_review", "composition",
}


def _cards():
    spec = importlib.util.spec_from_file_location('preview_cards', Path(__file__).with_name('preview_cards.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def load_preview_source(root: Path, case_id: str) -> tuple[dict, dict | None]:
    if not isinstance(case_id, str) or not ID.fullmatch(case_id):
        raise ValueError("unknown preview source")
    if case_id != "beige-blazer-denim-outfit":
        raise ValueError("unknown preview source")
    findings = _demo_media().validate_preview_sources(root)
    if findings:
        raise ValueError("preview source invalid: " + "; ".join(findings))
    rights_ref = f"docs/demo/preview-sources/{case_id}/rights.json"
    rights_path = child(root, rights_ref)
    rights = read_json(rights_path)
    public = rights["public_asset"]
    source = {
        "case_id": case_id,
        "rights_ref": rights_ref,
        "rights_sha256": digest(rights_path.read_bytes()),
        "assets": [{
            "path": f"docs/demo/preview-sources/{case_id}/{public['path']}",
            "role": "outfit-source",
            "sha256": public["sha256"],
        }],
        "subtitle": "同款完整套装",
        "outfit": copy.deepcopy(rights["outfit"]),
        "review_contract": rights["review_contract"],
    }
    _, anchor = _source(root)
    return source, anchor


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
    source_count = len(source["assets"])
    lines = [
        f"Create one action-0 preview for style {preview['style']}.",
        "Use a single 2x3 grid contact-sheet preview on a square 1:1 board showing the same complete coordinated outfit in six different directions.",
        "Top row poses 1-2-3; bottom row poses 4-5-6. Six equal 3:4 portrait cells, one pose per cell, one adult female model identity throughout this sheet.",
        "Reserve independent title, subtitle and footer bands outside all six pose cells; keep the three text bands distinct and clear of every subject.",
        f"Render this exact full bilingual title natively at the top: {preview['label_contract']['title']}",
        f"Render this exact subtitle natively below the title: {preview['label_contract']['subtitle']}",
        f"Render this exact disclosure natively in the footer: {preview['label_contract']['footer']}",
        f"Attached image{'s' if source_count != 1 else ''} 1{'-' + str(source_count) if source_count != 1 else ''} {'are' if source_count != 1 else 'is'} the only authoritative outfit truth.",
        "Preserve every core item exactly: " + "; ".join(source["outfit"]["core_items"]) + ".",
        "Keep the complete coordinated outfit visible in all six cells. Never replace a garment or invent a brand, logo or text.",
        f"Attached image {source_count + 1} is identity-only: preserve face, hair, apparent age and body proportions; never treat it as outfit authority.",
        "Style may change mood, low-distraction background, pose treatment and lighting only; source truth overrides every style-pack suggestion.",
        f"Mode: {preview['mode']} derived from the registered pack default and runtime mode rules.",
        f"Mood only: {visual['mood']}",
        f"Attitude: {visual['persona']}",
        f"Lighting/background palette: {visual['lighting']}",
        "This is a LOW-RES DIRECTION PREVIEW, not a final deliverable. Keep the footer visible and unobtrusive, no larger than about 3-4% of image height.",
        "All requested text must be native-rendered in the generated board. Never cover the model, face, vest, shoes, bag or pose. Do not place a large centered watermark.",
        "Outfit references: " + ", ".join(asset["path"] for asset in source["assets"]),
        "Identity-only reference: " + anchor["path"],
    ]
    for pose in preview["poses"]:
        lines.extend([
            "",
            f"POSE {pose['ordinal']} / row {pose['row']} column {pose['column']}: {pose['master']} — {pose['description']}",
            f"Head/gaze: {pose['head_gaze']}",
            f"Mode/scene: {pose['scene']}",
            f"Framing: {preview['layout_contract']['framing'][pose['ordinal'] - 1]}",
            "Retain every core outfit item and all visible source construction detail.",
        ])
    lines.extend([
        "",
        "Preview negative (grid is intentionally allowed): " + preview_negative,
        "Style negative append: " + ", ".join(preview["negative_delta_add"]),
    ])
    return "\n".join(lines) + "\n"


def _plan_v5(root, run_id, source_case):
    run_dir(root, run_id)
    source, anchor = load_preview_source(root, source_case)
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
                "subtitle": f"{source['subtitle']} · {mode} {MODE_NAMES[mode]} · 六姿势预览",
                "footer": PREVIEW_MARK,
            },
        }
        preview["prompt_sha256"] = digest(_prompt(preview, source, anchor, preview_negative).encode())
        preview["display_contract"] = copy.deepcopy(_cards().CONTRACT)
        previews.append(preview)
    return {
        "schema_version": CURRENT_SCHEMA, "run_id": run_id, "role": "style-preview", "status": "prepared",
        "source": source, "identity_anchor": anchor, "rules": rules, "ai_label": AI_LABEL,
        "batches": [], "previews": previews,
    }


def _legacy_error(schema):
    return f"preview schema {schema} is superseded historical evidence, not approved for current standard; it is read-only and cannot be prepared, ingested, approved or promoted"


def _require_mutable_v5(record):
    schema = record.get("schema_version")
    if schema == FROZEN_PUBLIC_SCHEMA:
        raise ValueError("preview schema 4.0 is frozen public evidence; mutation is forbidden")
    if schema in HISTORICAL_SCHEMAS:
        raise ValueError(_legacy_error(schema))
    if schema != CURRENT_SCHEMA:
        raise ValueError("unsupported preview schema")


def _validated_batch(record, manifest):
    required = {
        "schema_version", "batch_id", "run_id", "styles", "maximum_calls",
        "authorization_sha256", "authorized_at", "scope",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("batch manifest fields invalid")
    if manifest["schema_version"] != "1.0" or not ID.fullmatch(str(manifest["batch_id"])):
        raise ValueError("batch manifest fields invalid")
    if manifest["run_id"] != record["run_id"]:
        raise ValueError("batch run id mismatch")
    styles = manifest["styles"]
    if not isinstance(styles, list) or not 1 <= len(styles) <= 6 or len(styles) != len(set(styles)):
        raise ValueError("batch requires one through six unique styles")
    planned = [preview["style"] for preview in record["previews"]]
    if any(style not in planned for style in styles) or styles != [style for style in planned if style in styles]:
        raise ValueError("batch styles must preserve planned order")
    if type(manifest["maximum_calls"]) is not int or manifest["maximum_calls"] != len(styles):
        raise ValueError("batch maximum_calls must equal its one through six styles")
    if not HASH.fullmatch(str(manifest["authorization_sha256"])):
        raise ValueError("batch authorization hash missing")
    _primary().parse_iso_z(manifest["authorized_at"])
    if manifest["scope"] != "serial-native-generation;no-auto-retry":
        raise ValueError("batch scope must require serial generation and no auto retry")
    return copy.deepcopy(manifest)


def _check_batches(record, directory=None, require_complete=False):
    batches = record.get("batches")
    if not isinstance(batches, list) or len(batches) > 4:
        raise ValueError("at most four batches are allowed")
    validated = [_validated_batch(record, batch) for batch in batches]
    ids = [batch["batch_id"] for batch in validated]
    styles = [style for batch in validated for style in batch["styles"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate batch id")
    if len(styles) != len(set(styles)):
        raise ValueError("batch style overlap")
    if directory is not None:
        batch_dir = directory / "batches"
        actual = sorted(path.name for path in batch_dir.glob("*.json")) if batch_dir.is_dir() else []
        expected = sorted(f"{batch_id}.json" for batch_id in ids)
        if actual != expected:
            raise ValueError("local batch manifest set mismatch")
        for batch in validated:
            if read_json(child(directory, f"batches/{batch['batch_id']}.json")) != batch:
                raise ValueError("immutable batch manifest changed")
    if require_complete:
        planned = [preview["style"] for preview in record["previews"]]
        if len(validated) != 4 or styles != planned:
            raise ValueError("four batches must cover the ordered 24-style plan")
    return {batch["batch_id"]: batch for batch in validated}


def register_batch(root: Path, run_id: str, manifest: dict) -> dict:
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    _require_mutable_v5(record)
    _check_plan(root, record, directory)
    existing = next((batch for batch in record["batches"] if batch.get("batch_id") == manifest.get("batch_id")), None)
    if existing is not None:
        if existing != manifest:
            raise ValueError("immutable batch manifest cannot be overwritten")
        return record
    if len(record["batches"]) >= 4:
        raise ValueError("at most four batches are allowed")
    validated = _validated_batch(record, manifest)
    registered_styles = {style for batch in record["batches"] for style in batch["styles"]}
    if registered_styles.intersection(validated["styles"]):
        raise ValueError("batch style overlap")
    record["batches"].append(validated)
    path = child(directory, f"batches/{validated['batch_id']}.json")
    if path.exists():
        raise ValueError("immutable batch manifest collision")
    _atomic_json(path, validated)
    _atomic_json(directory / "evidence.json", record)
    return record


def prepare(root, run_id, source_case=None):
    directory = run_dir(root, run_id)
    if directory.exists():
        existing = read_json(directory / "evidence.json")
        _require_mutable_v5(existing)
        if source_case is not None and existing.get("source", {}).get("case_id") != source_case:
            raise ValueError("source case does not match existing run")
        _check_plan(root, existing, directory)
        return existing
    if source_case is None:
        raise ValueError("source case is required for schema 5.0 preview runs")
    plan = _plan_v5(root, run_id, source_case)
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
    expected = _plan_v5(root, record["run_id"], record.get("source", {}).get("case_id"))
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
    batches = _check_batches(record, directory)
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
    calls = [preview.get("generation", {}).get("call_id") for preview in generated if preview.get("generation", {}).get("call_id") is not None]
    originals = [preview.get("original_sha256") for preview in generated]
    optimized = [preview.get("sha256") for preview in generated]
    if len(calls) != len(set(calls)) or len(originals) != len(set(originals)) or len(optimized) != len(set(optimized)):
        raise ValueError("duplicate native call or preview hash")
    for batch_id, batch in batches.items():
        consumed = sum(
            1 + int("correction" in preview)
            for preview in generated
            if preview.get("generation", {}).get("batch_id") == batch_id
        )
        if consumed > batch["maximum_calls"]:
            raise ValueError("batch maximum_calls consumed")


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


def _check_correction(correction, preview, generation):
    if not isinstance(correction, dict) or set(correction) != {
        "kind", "reason_code", "generation_prompt_sha256",
        "generation_authorization_sha256", "visual_acceptance_sha256", "replaces",
    }:
        raise ValueError("correction record fields invalid")
    if correction["kind"] != "targeted-correction" or correction["reason_code"] != "maintainer-requested-visual-fix":
        raise ValueError("correction record fields invalid")
    if any(not HASH.fullmatch(str(correction[key])) for key in (
        "generation_prompt_sha256", "generation_authorization_sha256", "visual_acceptance_sha256",
    )):
        raise ValueError("correction record fields invalid")
    replaces = correction["replaces"]
    if not isinstance(replaces, dict) or set(replaces) != {
        "call_id", "original_sha256", "native_sha256", "display_sha256",
    }:
        raise ValueError("correction record fields invalid")
    if not isinstance(replaces["call_id"], str) or not ID.fullmatch(replaces["call_id"]):
        raise ValueError("correction record fields invalid")
    if any(not HASH.fullmatch(str(replaces[key])) for key in (
        "original_sha256", "native_sha256", "display_sha256",
    )):
        raise ValueError("correction record fields invalid")
    if generation["call_id"] == replaces["call_id"]:
        raise ValueError("correction must bind a new native call")
    if generation["prompt_sha256"] != correction["generation_prompt_sha256"]:
        raise ValueError("generation prompt mismatch")


def _check_failed_retry(failed_retry, preview, generation, record, batch, directory):
    required = {
        "kind", "reason_code", "failure_record_path", "failure_record_sha256",
        "generation_prompt_sha256", "generation_authorization_sha256",
        "authorized_at", "attempt_number", "scope",
    }
    if not isinstance(failed_retry, dict) or set(failed_retry) != required:
        raise ValueError("failed retry record fields invalid")
    if (failed_retry["kind"] != "failed-call-retry"
            or failed_retry["scope"] != "single-target-retry;no-auto-retry"):
        raise ValueError("failed retry record fields invalid")
    if failed_retry["reason_code"] not in {
        "prompt-binding-failed", "native-generation-timeout-no-output",
    }:
        raise ValueError("failed retry reason invalid")
    if any(not HASH.fullmatch(str(failed_retry[key])) for key in (
        "failure_record_sha256", "generation_prompt_sha256",
        "generation_authorization_sha256",
    )):
        raise ValueError("failed retry record fields invalid")
    expected_path = f"failed-calls/{preview['style']}/failure.json"
    if failed_retry["failure_record_path"] != expected_path or directory is None:
        raise ValueError("failed retry failure record path invalid")
    failure_path = child(directory, expected_path)
    if not failure_path.is_file() or digest(failure_path.read_bytes()) != failed_retry["failure_record_sha256"]:
        raise ValueError("failed retry failure record hash mismatch")
    failure = read_json(failure_path)
    failure_required = {
        "schema_version", "run_id", "batch_id", "style", "status",
        "attempt_number", "batch_halted", "automatic_retry_performed",
        "authorization_sha256", "native_output_path", "native_output_sha256",
    }
    if not failure_required.issubset(failure):
        raise ValueError("failed retry source record invalid")
    if (failure["schema_version"] != "failure-record-v1"
            or failure["run_id"] != record["run_id"]
            or failure["batch_id"] != batch["batch_id"]
            or failure["style"] != preview["style"]
            or failure["status"] != failed_retry["reason_code"]
            or failure["batch_halted"] is not True
            or failure["automatic_retry_performed"] is not False
            or failure["authorization_sha256"] != batch["authorization_sha256"]):
        raise ValueError("failed retry source record invalid")
    if type(failure["attempt_number"]) is not int or failure["attempt_number"] < 1:
        raise ValueError("failed retry source record invalid")
    if (type(failed_retry["attempt_number"]) is not int
            or failed_retry["attempt_number"] != failure["attempt_number"] + 1):
        raise ValueError("failed retry attempt number invalid")
    failure_prompt_hash = (
        failure.get("planned_prompt_sha256")
        if failure["status"] == "prompt-binding-failed"
        else failure.get("prompt_sha256")
    )
    if failure_prompt_hash != preview["prompt_sha256"]:
        raise ValueError("failed retry source prompt mismatch")
    if failure["status"] == "native-generation-timeout-no-output" and (
        failure["native_output_path"] is not None or failure["native_output_sha256"] is not None
    ):
        raise ValueError("failed retry timeout record contains output")
    if (failed_retry["generation_prompt_sha256"] != preview["prompt_sha256"]
            or generation["prompt_sha256"] != failed_retry["generation_prompt_sha256"]):
        raise ValueError("generation prompt mismatch")
    if (failed_retry["generation_authorization_sha256"] == batch["authorization_sha256"]
            or generation["authorization_sha256"] != failed_retry["generation_authorization_sha256"]):
        raise ValueError("failed retry requires a new authorization hash")
    authorized_at = _primary().parse_iso_z(failed_retry["authorized_at"])
    failed_at_value = failure.get("terminated_at") or failure.get("generated_at")
    if not failed_at_value or authorized_at <= _primary().parse_iso_z(failed_at_value):
        raise ValueError("failed retry authorization must postdate failure")
    if _primary().parse_iso_z(generation["generated_at"]) < authorized_at:
        raise ValueError("generation predates failed retry authorization")


def _generation(generation, preview, record, directory=None):
    if record.get("schema_version") == FROZEN_PUBLIC_SCHEMA:
        if not isinstance(generation, dict) or set(generation) != {"tool", "call_id", "generated_at", "prompt_sha256"}:
            raise ValueError("generation record fields invalid")
        if generation["tool"] != "native-imagegen" or not isinstance(generation["call_id"], str) or not ID.fullmatch(generation["call_id"]):
            raise ValueError("native generation call required")
        if preview.get("correction") is not None:
            _check_correction(preview["correction"], preview, generation)
        elif generation["prompt_sha256"] != preview["prompt_sha256"]:
            raise ValueError("generation prompt mismatch")
        _primary().parse_iso_z(generation["generated_at"])
        return
    required = {
        "tool", "call_id", "generated_at", "prompt_sha256", "batch_id",
        "authorization_sha256", "model_docs_url", "model_docs_verified_at", "per_call_model",
    }
    if not isinstance(generation, dict) or set(generation) != required:
        raise ValueError("generation record fields invalid")
    call_id = generation["call_id"]
    if generation["tool"] != "native-imagegen" or (call_id is not None and (not isinstance(call_id, str) or not ID.fullmatch(call_id))):
        raise ValueError("native generation call required")
    batches = _check_batches(record)
    batch = batches.get(generation["batch_id"])
    if batch is None or preview["style"] not in batch["styles"]:
        raise ValueError("style is outside registered batch")
    correction = preview.get("correction")
    failed_retry = preview.get("failed_retry")
    if correction is not None and failed_retry is not None:
        raise ValueError("correction and failed retry are mutually exclusive")
    if correction is not None:
        _check_correction(correction, preview, generation)
        if generation["authorization_sha256"] != correction["generation_authorization_sha256"] or generation["authorization_sha256"] == batch["authorization_sha256"]:
            raise ValueError("targeted correction requires a new authorization hash")
    elif failed_retry is not None:
        _check_failed_retry(failed_retry, preview, generation, record, batch, directory)
    elif generation["prompt_sha256"] != preview["prompt_sha256"]:
        raise ValueError("generation prompt mismatch")
    elif generation["authorization_sha256"] != batch["authorization_sha256"]:
        raise ValueError("generation authorization hash mismatch")
    if generation["model_docs_url"] != MODEL_DOCS_URL or generation["model_docs_verified_at"] != MODEL_DOCS_VERIFIED_AT or generation["per_call_model"] != "unavailable":
        raise ValueError("generation model disclosure invalid")
    generated_at = _primary().parse_iso_z(generation["generated_at"])
    if generated_at < _primary().parse_iso_z(batch["authorized_at"]):
        raise ValueError("generation predates batch authorization")


def _find_preview(record, style):
    if not isinstance(style, str) or not ID.fullmatch(style):
        raise ValueError("registered style required")
    preview = next((item for item in record.get("previews", []) if item.get("style") == style), None)
    if preview is None:
        raise ValueError("registered style required")
    return preview


def _receipt_bindings(record, preview):
    bindings = {
        "style": preview["style"], "source_sha256": object_hash(record["source"]),
        "rules_sha256": object_hash(record["rules"]), "pack_sha256": preview["pack"]["sha256"],
        "prompt_sha256": preview["prompt_sha256"],
        "layout_contract_sha256": object_hash(preview["layout_contract"]),
        "label_contract_sha256": object_hash(preview["label_contract"]),
    }
    if "correction" in preview:
        bindings.update(
            correction_sha256=object_hash(preview["correction"]),
            generation_prompt_sha256=preview["generation"]["prompt_sha256"],
        )
    if "failed_retry" in preview:
        bindings.update(
            failed_retry_sha256=object_hash(preview["failed_retry"]),
            generation_prompt_sha256=preview["generation"]["prompt_sha256"],
        )
    return bindings


def _native_dimensions(path):
    from PIL import Image, ImageOps
    with Image.open(path) as opened:
        if opened.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("unsupported native image format")
        oriented = ImageOps.exif_transpose(opened)
        oriented.load()
        return [oriented.width, oriented.height]


def ingest(root, run_id, style, image, generation, correction=None, failed_retry=None):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    _require_mutable_v5(record)
    _check_plan(root, record, directory)
    preview = _find_preview(record, style)
    if record["status"] not in {"prepared", "awaiting-human-review"}:
        raise ValueError("invalid ingest state")
    candidate = copy.deepcopy(preview)
    if correction is not None and failed_retry is not None:
        raise ValueError("correction and failed retry are mutually exclusive")
    if correction is not None:
        candidate["correction"] = copy.deepcopy(correction)
    if failed_retry is not None:
        candidate["failed_retry"] = copy.deepcopy(failed_retry)
    candidate["generation"] = copy.deepcopy(generation)
    _generation(generation, candidate, record, directory)
    original = digest(image.read_bytes())
    if correction is not None and original == correction["replaces"]["original_sha256"]:
        raise ValueError("correction must replace a different native output")
    if "path" in preview:
        expected = {key: preview[key] for key in ("sha256", "bytes", "width", "height")}
        if preview["original_sha256"] == original and preview["generation"] == generation and _image(child(directory, preview["path"])) == expected:
            _validate_preview(record, preview, directory, False, True, require_composition=False)
            return record
        raise ValueError("refuse to overwrite registered preview")
    for other in record["previews"]:
        if generation["call_id"] is not None and other.get("generation", {}).get("call_id") == generation["call_id"]:
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
        "generation": generation, "bindings": _receipt_bindings(record, candidate),
    })
    if correction is not None:
        preview["correction"] = copy.deepcopy(correction)
    if failed_retry is not None:
        preview["failed_retry"] = copy.deepcopy(failed_retry)
    preview.update(metadata, path=target.name, original_sha256=original, generation=generation)
    record["status"] = "awaiting-human-review"
    write_json(directory / "evidence.json", record)
    write_json(directory / f"review-template-{style}.json", review_template(record, style))
    return record


def confirmation(style):
    return f"I reviewed the complete six-pose {style} preview against the authorized sources."


def public_assets(record):
    """Registered publishable image assets; paths are relative to the run directory.

    Call validate_public_previews before using a public record. Retained raw
    originals, receipt absolute paths, layouts and font binaries are private.
    """
    assets = []
    for preview in record['previews']:
        if 'path' in preview:
            assets.append({'style': preview['style'], 'role': 'native-preview',
                           **{key: preview[key] for key in ('path', 'sha256', 'width', 'height', 'bytes')}})
        for role, key in [('display-preview', 'display'), ('preview-thumbnail', 'thumbnail')]:
            if 'composition' in preview:
                assets.append({'style': preview['style'], 'role': role, **preview['composition'][key]})
    return assets


def compose(root, run_id, style, layout, font):
    directory = run_dir(root, run_id)
    record = read_json(directory / 'evidence.json')
    _require_mutable_v5(record)
    _check_plan(root, record, directory)
    preview = _find_preview(record, style)
    _validate_preview(record, preview, directory, False, True, require_composition=False)
    receipt = read_json(child(directory, f'native-receipts/{style}.json'))
    cards = _cards()
    cells = cards.rectangles(layout, preview['original_sha256'], receipt['native_dimensions'])
    font_hash = digest(font.read_bytes())
    if 'composition' in preview:
        comp = preview['composition']
        if comp['layout_sha256'] == object_hash(layout) and comp['font_sha256'] == font_hash:
            _check_composition(preview, directory, True)
            return record
        raise ValueError('refuse to overwrite registered composition; prepare a fresh run')
    labels = {**preview['label_contract'], 'footer': cards.CONTRACT['footer_text']}
    layout_path = f'layouts/{style}.json'
    for relative in (layout_path, f'{style}-display.jpg', f'{style}-thumb.jpg'):
        if child(directory, relative).exists():
            raise ValueError('refuse to overwrite unregistered composition asset')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        stage = Path(temporary)
        rendering = cards.render(child(directory, receipt['retained_path']), cells, labels, font, stage, style)
        comp = {
            'original_sha256': preview['original_sha256'], 'native_sha256': preview['sha256'],
            'native_dimensions': receipt['native_dimensions'],
            'generation': copy.deepcopy(preview['generation']),
            'layout_path': layout_path, 'layout_sha256': object_hash(layout), 'observed_layout': copy.deepcopy(layout),
            'font_sha256': font_hash, 'parameters': copy.deepcopy(cards.CONTRACT),
            'geometry': 'pass', 'geometry_scope': 'deterministic-display-cards-only',
            'native_geometry': 'not-certified-by-composition', **rendering,
        }
        for key, suffix in [('display', 'display'), ('thumbnail', 'thumb')]:
            relative = f'{style}-{suffix}.jpg'
            comp[key] = {'path': relative, **_image(stage / relative)}
        for key in ('display', 'thumbnail'):
            relative = comp[key]['path']
            shutil.copyfile(stage / relative, child(directory, relative))
    _atomic_json(child(directory, layout_path), layout)
    preview['composition'] = comp
    _atomic_json(directory / 'evidence.json', record)
    _atomic_json(directory / f'review-template-{style}.json', review_template(record, style))
    return record


def _check_composition(preview, directory, local):
    comp = preview.get('composition')
    required = {'original_sha256', 'native_sha256', 'native_dimensions', 'generation', 'layout_path',
                'layout_sha256', 'observed_layout', 'font_sha256', 'font_name', 'parameters', 'geometry',
                'geometry_scope', 'native_geometry', 'transforms', 'text', 'display', 'thumbnail'}
    if not isinstance(comp, dict) or set(comp) != required:
        raise ValueError('missing or malformed composition')
    if (comp['original_sha256'] != preview['original_sha256'] or comp['native_sha256'] != preview['sha256']
            or comp['generation'] != preview['generation']):
        raise ValueError('composition source or prompt binding mismatch')
    if comp['native_dimensions'] != [preview['width'], preview['height']]:
        raise ValueError('composition native dimensions mismatch')
    cards = _cards()
    if comp['parameters'] != cards.CONTRACT or comp['geometry'] != 'pass' or comp['geometry_scope'] != 'deterministic-display-cards-only' or comp['native_geometry'] != 'not-certified-by-composition':
        raise ValueError('composition geometry contract mismatch')
    cells = cards.rectangles(comp['observed_layout'], preview['original_sha256'], comp['native_dimensions'])
    if object_hash(comp['observed_layout']) != comp['layout_sha256'] or comp['transforms'] != cards.transforms(cells):
        raise ValueError('composition layout or transforms mismatch')
    if comp['layout_path'] != f"layouts/{preview['style']}.json":
        raise ValueError('composition layout path invalid')
    if local and read_json(child(directory, comp['layout_path'])) != comp['observed_layout']:
        raise ValueError('composition observed layout changed')
    if not HASH.fullmatch(str(comp['font_sha256'])) or not isinstance(comp['font_name'], str) or not comp['font_name'] or '/' in comp['font_name'] or '\\' in comp['font_name']:
        raise ValueError('composition font provenance invalid')
    labels = {**preview['label_contract'], 'footer': cards.CONTRACT['footer_text']}
    if not isinstance(comp['text'], dict) or set(comp['text']) != set(labels):
        raise ValueError('composition labels incomplete')
    for name, label in labels.items():
        text = comp['text'][name]
        if not isinstance(text, dict) or set(text) != {'text', 'rendered', 'font_size', 'bounds'}:
            raise ValueError('composition label record invalid')
        if text['text'] != label or not isinstance(text['rendered'], str) or text['rendered'].replace('\n', '') != label.replace('\n', ''):
            raise ValueError('composition label content mismatch')
        if type(text['font_size']) is not int or not 18 <= text['font_size'] <= 34:
            raise ValueError('composition label font size invalid')
        x, y, w, h = _rect(text['bounds'], 1200, 1200)
        bx, by, bw, bh = cards.CONTRACT[name]
        if x < bx or y < by or x+w > bx+bw or y+h > by+bh:
            raise ValueError('composition label escapes reserved band')
    for key, suffix, size in [('display', 'display', [1200, 1200]), ('thumbnail', 'thumb', [600, 600])]:
        asset = comp[key]
        if not isinstance(asset, dict) or set(asset) != {'path', 'sha256', 'width', 'height', 'bytes'} or asset['path'] != f"{preview['style']}-{suffix}.jpg":
            raise ValueError('composition asset path invalid')
        actual = _image(child(directory, asset['path']))
        if any(asset[k] != v for k, v in actual.items()) or [actual['width'], actual['height']] != size:
            raise ValueError('composition asset hash or dimensions mismatch')


def _review_hash(record, preview):
    return object_hash({
        "source": record["source"], "identity_anchor": record["identity_anchor"], "rules": record["rules"],
        "preview": {key: value for key, value in preview.items() if key != "human_review"},
    })


def _v4_review_template(record, style):
    preview = _find_preview(record, style)
    comp = preview.get('composition', {})
    return {
        "reviewer": "", "reviewed_at": "", "confirmation": "", "preview_sha256": comp.get('display', {}).get('sha256', ''),
        "original_sha256": preview.get('original_sha256', ''),
        "native_sha256": preview.get('sha256', ''),
        "composition_sha256": object_hash(comp) if comp else '',
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
            "complete_panel_extraction": "pending",
            "padding_no_subject_loss": "pending",
            "derivative_disclosure": "pending",
        },
        "poses": [
            {
                "ordinal": ordinal, "product": "pending", "pose_layout": "pending",
                "identity_style": "pending", "ai_disclosure": "pending", "framing": "pending",
            }
            for ordinal in range(1, 7)
        ],
    }


def _outfit_item_keys(record):
    outfit = record["source"]["outfit"]
    core_tokens = {
        "blazer": "blazer", "top": "top", "jeans": "jeans", "tote": "tote", "loafers": "loafers",
    }
    optional_tokens = {"watch": "watch", "jewelry": "jewelry"}
    core = {
        key for key, token in core_tokens.items()
        if any(token in fact.lower() for fact in outfit["core_items"])
    }
    optional = {
        key for key, token in optional_tokens.items()
        if any(token in fact.lower() for fact in outfit["optional_when_visible"])
    }
    if core != set(core_tokens) or optional != set(optional_tokens):
        raise ValueError("outfit review item mapping invalid")
    return list(core_tokens), list(optional_tokens)


def outfit_review_template(record: dict, style: str) -> dict:
    preview = _find_preview(record, style)
    comp = preview.get("composition", {})
    core, optional = _outfit_item_keys(record)
    return {
        "reviewer": "", "reviewed_at": "", "confirmation": "",
        "preview_sha256": comp.get("display", {}).get("sha256", ""),
        "original_sha256": preview.get("original_sha256", ""),
        "native_sha256": preview.get("sha256", ""),
        "composition_sha256": object_hash(comp) if comp else "",
        "evidence_sha256": _review_hash(record, preview), "public_use_approved": False,
        "geometry": {
            "cells": [None, None, None, None, None, None],
            "title": None, "subtitle": None, "footer": None,
        },
        "checks": {
            "observed_boundaries": "pending",
            "full_bilingual_title": "pending",
            "correct_subtitle": "pending",
            "readable_ai_footer": "pending",
            "text_subject_non_overlap": "pending",
            "complete_panel_extraction": "pending",
            "padding_no_subject_loss": "pending",
            "derivative_disclosure": "pending",
        },
        "cells": [
            {
                "ordinal": ordinal,
                "core_items": {key: "pending" for key in core},
                "optional_items": {key: "pending" for key in optional},
                "complete_outfit_visible": "pending",
                "adult_identity": "pending",
                "anatomy": "pending",
                "pose_layout": "pending",
                "registered_style_distinct": "pending",
                "ai_disclosure": "pending",
                "framing": "pending",
            }
            for ordinal in range(1, 7)
        ],
    }


def review_template(record, style):
    if record.get("source", {}).get("review_contract") == "coordinated-outfit-v1":
        return outfit_review_template(record, style)
    return _v4_review_template(record, style)


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


def _check_v4_review(record, preview):
    review = preview.get("human_review")
    template = _v4_review_template(record, preview["style"])
    if not isinstance(review, dict) or set(review) != set(template):
        raise ValueError("human review incomplete")
    if not _primary().GITHUB_REVIEWER.fullmatch(str(review["reviewer"])) or review["confirmation"] != confirmation(preview["style"]):
        raise ValueError("human review incomplete")
    if review["public_use_approved"] is not True or any(review[k] != template[k] for k in
            ('preview_sha256', 'original_sha256', 'native_sha256', 'composition_sha256', 'evidence_sha256')):
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
    _check_geometry(review["geometry"], 1200, 1200)
    contract = preview['display_contract']
    if review['geometry']['cells'] != contract['cells']:
        raise ValueError('observed geometry invalid')
    for name in ('title', 'subtitle', 'footer'):
        x, y, w, h = review['geometry'][name]
        bx, by, bw, bh = contract[name]
        if x < bx or y < by or x+w > bx+bw or y+h > by+bh:
            raise ValueError('observed geometry invalid')
    if _primary().parse_iso_z(review["reviewed_at"]) < _primary().parse_iso_z(preview["generation"]["generated_at"]):
        raise ValueError("review predates generation")


def _check_outfit_review(record, preview):
    review = preview.get("human_review")
    template = outfit_review_template(record, preview["style"])
    if not isinstance(review, dict) or set(review) != set(template):
        raise ValueError("human review incomplete")
    if not _primary().GITHUB_REVIEWER.fullmatch(str(review["reviewer"])) or review["confirmation"] != confirmation(preview["style"]):
        raise ValueError("human review incomplete")
    if review["public_use_approved"] is not True or any(
        review[key] != template[key]
        for key in ("preview_sha256", "original_sha256", "native_sha256", "composition_sha256", "evidence_sha256")
    ):
        raise ValueError("human review incomplete")
    if review["checks"] != {key: "pass" for key in template["checks"]}:
        raise ValueError("human review incomplete")
    if not isinstance(review["cells"], list) or len(review["cells"]) != 6:
        raise ValueError("human review incomplete")
    core, optional = _outfit_item_keys(record)
    required_pass = {
        "complete_outfit_visible", "adult_identity", "anatomy", "pose_layout",
        "registered_style_distinct", "ai_disclosure", "framing",
    }
    for ordinal, cell in enumerate(review["cells"], start=1):
        if not isinstance(cell, dict) or set(cell) != {"ordinal", "core_items", "optional_items", *required_pass}:
            raise ValueError("human review incomplete")
        if cell["ordinal"] != ordinal or cell["core_items"] != {key: "pass" for key in core}:
            raise ValueError("human review incomplete")
        if set(cell["optional_items"]) != set(optional) or any(
            value not in {"pass", "not-visible-no-contradiction"}
            for value in cell["optional_items"].values()
        ):
            raise ValueError("human review incomplete")
        if any(cell[key] != "pass" for key in required_pass):
            raise ValueError("human review incomplete")
    _check_geometry(review["geometry"], 1200, 1200)
    contract = preview["display_contract"]
    if review["geometry"]["cells"] != contract["cells"]:
        raise ValueError("observed geometry invalid")
    for name in ("title", "subtitle", "footer"):
        x, y, width, height = review["geometry"][name]
        box_x, box_y, box_width, box_height = contract[name]
        if x < box_x or y < box_y or x + width > box_x + box_width or y + height > box_y + box_height:
            raise ValueError("observed geometry invalid")
    if _primary().parse_iso_z(review["reviewed_at"]) < _primary().parse_iso_z(preview["generation"]["generated_at"]):
        raise ValueError("review predates generation")


def _check_review(record, preview):
    if record.get("source", {}).get("review_contract") == "coordinated-outfit-v1":
        _check_outfit_review(record, preview)
    else:
        _check_v4_review(record, preview)


def _validate_preview(record, preview, directory, require_approval, local, require_composition=True):
    style = preview["style"]
    if preview.get("path") != f"{style}.jpg":
        raise ValueError("missing native output" if "path" not in preview else "preview path invalid")
    actual = _image(child(directory, preview["path"]))
    if any(preview.get(key) != value for key, value in actual.items()):
        raise ValueError("preview hash or metadata mismatch")
    if not HASH.fullmatch(str(preview.get("original_sha256"))):
        raise ValueError("original preview hash missing")
    _generation(preview.get("generation"), preview, record, directory)
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
    authorization = record["source"].get("authorization")
    if authorization is not None and _primary().parse_iso_z(preview["generation"]["generated_at"]) < _primary().parse_iso_z(authorization["declared_at"]):
        raise ValueError("generation predates source authorization")
    if require_composition or 'composition' in preview:
        _check_composition(preview, directory, local)
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
    _require_mutable_v5(record)
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
        if 'path' in preview and preview['path'] != f"{preview['style']}.jpg":
            raise ValueError('preview path invalid')
        if 'composition' in preview:
            for key, suffix in [('display', 'display'), ('thumbnail', 'thumb')]:
                if preview['composition'][key]['path'] != f"{preview['style']}-{suffix}.jpg":
                    raise ValueError('composition asset path invalid')
        visual = (
            f'<a href="{html.escape(preview["path"])}"><img src="{html.escape(preview["path"])}" '
            f'width="{int(preview["width"])}" height="{int(preview["height"])}" '
            f'alt="Complete {html.escape(preview["style"])} six-pose preview sheet"></a>'
            if "path" in preview else "<p>Not generated</p>"
        )
        if 'path' in preview:
            visual = '<p>Native whole sheet (optimized original). Native exact-grid qualification is independent.</p>' + visual
        if 'composition' in preview:
            comp = preview['composition']
            display, thumb = comp['display'], comp['thumbnail']
            visual = (
                '<p>排版衍生预览 / Composed display: six fixed 360×480 cards on a 1200×1200 board. '
                'Complete extracted panels are contained with white padding and no upscale. '
                'Geometry PASS covers deterministic cards only; panel completeness and visual preservation require human review.</p>'
                f'<a href="{html.escape(display["path"])}"><img src="{html.escape(thumb["path"])}" '
                f'width="600" height="600" alt="Complete composed {html.escape(preview["style"])} six-pose preview board"></a>' + visual
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
    if record.get("source", {}).get("review_contract") == "coordinated-outfit-v1" and not local:
        case_id = html.escape(record["source"]["case_id"])
        introduction = (
            f'<figure><img src="../../preview-sources/{case_id}/source.jpg" width="543" height="724" '
            'alt="Authorized coordinated outfit source"><figcaption>Authorized real physical outfit source / 已授权真实实物套装源图</figcaption></figure>'
            '<p><strong>AI-generated · locally composed direction preview · not final imagery</strong><br>'
            '<strong>AI生成 · 排版衍生方向预览 · 非成片</strong></p>'
            f'<p>Generation documentation: <a href="{MODEL_DOCS_URL}">{MODEL_DOCS_URL}</a>; verified {MODEL_DOCS_VERIFIED_AT}. '
            'The host did not expose a per-call model identifier (<code>per_call_model: unavailable</code>).</p>'
            '<p>Media license: <code>ThreadTruth-Demo-Only-1.0</code>. Repository/release display only; no standalone reuse, resale, relicensing or CC0 dedication.</p>'
            '<h2>Limitations / 局限</h2><p>These 24 whole-sheet direction previews are not 144 independent finals, do not prove universal garment or outfit coverage, and do not count as external adoption or complete primary cases.</p>'
        )
    else:
        introduction = ""
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Style preview review</title><style>body{max-width:1200px;margin:2rem auto;font-family:system-ui}'
        'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:2rem}'
        'section{min-width:0}img{display:block;width:auto;max-width:100%;height:auto}'
        'ol{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding-left:1.5rem}'
        'li{min-width:0;overflow-wrap:anywhere;word-break:break-word}'
        '@media(max-width:480px){ol{grid-template-columns:1fr}}</style><body>'
        f'<h1>{AI_LABEL}</h1>{introduction}<p>24 single-style, six-pose sheets. Every thumbnail is the complete sheet; click it for the original display image. '
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


def _readme_v4(record):
    return f"""# Style preview collection: {record['run_id']}

{AI_LABEL}

[Review all 24 whole sheets](index.html). Each entry is one registered style applied to the same authorized garment in the six canonical action-0 poses. The gallery always displays the complete sheet; it does not crop or upscale cells.

Source authorization: [primary rights](../../primary-cases/{CASE}/rights.json). Four real garment sources remain authoritative; look-1 is identity-only.

[evidence.json](evidence.json) binds source rights, runtime rule hashes, actual pack versions/hashes, prompt hashes, 24 native calls, observed JPEG metadata and per-sheet six-pose human review. Targeted corrections also retain the replaced call/image hashes and the actual correction prompt hash. Machine verification does not judge subjective visual quality, infer a six-pose layout from dimensions, or authenticate reviewer identity.

CC0 applies only to the extent the project can grant rights; Apache-2.0 does not cover media. AI-generated content requires applicable labeling. These previews never count as independent finals or runtime maturity evidence.
"""


def _readme_v5(record):
    case_id = record["source"]["case_id"]
    return f"""# Coordinated outfit preview collection: {record['run_id']}

AI-generated · locally composed direction preview · not final imagery<br>
AI生成 · 排版衍生方向预览 · 非成片

[Review all 24 whole sheets](index.html). Each entry applies one registered style to the same complete authorized outfit and shows the six canonical action-0 poses. [Source and rights](../../preview-sources/{case_id}/rights.json).

Generation documentation: {MODEL_DOCS_URL} (verified {MODEL_DOCS_VERIFIED_AT}). The host evidence records `per_call_model: unavailable`; it does not infer a per-call model ID.

The source and every native/display/thumbnail asset use `ThreadTruth-Demo-Only-1.0`: repository and release display only, with no standalone reuse, resale, relicensing or CC0 dedication. Apache-2.0 covers code and documentation, not this media.

These 24 direction previews are not 144 independent finals, do not prove universal apparel coverage, and do not count as external adoption, a complete primary case, or runtime maturity evidence.
"""


def _readme(record):
    return _readme_v5(record) if record.get("schema_version") == CURRENT_SCHEMA else _readme_v4(record)


def _public_record_valid(root, record, directory):
    _check_plan(root, record)
    if record["status"] != "approved":
        raise ValueError("public preview collection is not approved")
    for preview in record["previews"]:
        _validate_preview(record, preview, directory, True, False)
    if _primary().has_sensitive_public_text(record):
        raise ValueError("sensitive public text")


def validate_frozen_v4(root: Path, directory: Path, record: dict) -> None:
    if directory.name != "white-vest-24-v1" or record.get("run_id") != directory.name:
        raise ValueError("schema 4.0 is reserved for the frozen white-vest collection")
    manifest_path = child(root, "tests/fixtures/white-vest-24-v1-beta3.sha256.json")
    manifest = read_json(manifest_path)
    actual_paths = sorted(path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file())
    if actual_paths != sorted(manifest):
        raise ValueError("frozen schema 4.0 file set mismatch")
    for relative, expected in manifest.items():
        data = child(directory, relative).read_bytes()
        if expected != {"sha256": digest(data), "bytes": len(data)}:
            raise ValueError(f"frozen schema 4.0 asset mismatch: {relative}")
    if record.get("schema_version") != FROZEN_PUBLIC_SCHEMA or record.get("status") != "approved":
        raise ValueError("frozen schema 4.0 record invalid")
    previews = record.get("previews")
    if not isinstance(previews, list) or len(previews) != 24 or len({item.get("style") for item in previews}) != 24:
        raise ValueError("frozen schema 4.0 requires 24 unique previews")
    for preview in previews:
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
            if record.get("schema_version") == FROZEN_PUBLIC_SCHEMA:
                validate_frozen_v4(root, directory, record)
                continue
            _public_record_valid(root, record, directory)
            expected = {"evidence.json", "README.md", "index.html", *[asset['path'] for asset in public_assets(record)]}
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
            "path": f"style-previews/{record['run_id']}/{preview['composition']['display']['path']}",
            "sha256": preview['composition']['display']['sha256'],
            "native": {**{key: preview[key] for key in ('sha256', 'width', 'height', 'bytes')},
                       'path': f"style-previews/{record['run_id']}/{preview['path']}"},
            "thumbnail": {**preview['composition']['thumbnail'],
                          'path': f"style-previews/{record['run_id']}/{preview['composition']['thumbnail']['path']}"},
        }
        for preview in record["previews"]
    }


def all_preview_collections(root: Path) -> dict[str, dict]:
    findings = validate_public_previews(root)
    if findings:
        raise ValueError("; ".join(findings))
    collections = {}
    for path in sorted(child(root, "docs/demo/style-previews").glob("*/evidence.json")):
        record = read_json(path)
        run_id = record["run_id"]
        if run_id in collections:
            raise ValueError("duplicate preview collection id")
        collections[run_id] = record
    return collections


def representative_preview_links(root: Path) -> dict[str, dict]:
    collections = all_preview_collections(root)
    if not collections:
        return {}
    representative = collections.get(REPRESENTATIVE_COLLECTION_ID)
    if representative is None:
        raise ValueError("representative preview collection is missing")
    return _links_from_record(representative)


def preview_links(root):
    """Compatibility alias; new callers must choose the representative projection explicitly."""
    return representative_preview_links(root)


def _project_preview(root, record):
    index_path = child(root, "docs/demo/style-index.json")
    index = read_json(index_path)
    links = _links_from_record(record)
    if {item.get("slug") for item in index.get("styles", [])} != set(links):
        raise ValueError("style index and approved previews differ")
    for item in index["styles"]:
        item["preview"] = links[item["slug"]]
    primary = _primary()
    tracked = [index_path, *primary.expected_style_pages(root), child(root, "docs/demo/RIGHTS.md"),
               *[root / name for name in ('README.md', 'README.zh-CN.md') if (root / name).is_file()]]
    backups = {path: path.read_bytes() if path.exists() else None for path in tracked}
    try:
        _atomic_json(index_path, index)
        primary.render_style_pages(root)
        primary.render_rights_index(root)
        primary.render_readme_previews(root)
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
    _require_mutable_v5(record)
    _check_plan(root, record, directory)
    _check_batches(record, directory, require_complete=True)
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
        _primary().render_rights_index(root)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        stage = Path(temporary) / "public"
        stage.mkdir()
        for asset in public_assets(record):
            shutil.copyfile(child(directory, asset['path']), stage / asset['path'])
        write_json(stage / "evidence.json", record)
        (stage / "README.md").write_text(_readme(record), encoding="utf-8")
        (stage / "index.html").write_text(_html(record, directory=stage), encoding="utf-8")
        created_target = False
        rights_path = child(root, "docs/demo/RIGHTS.md")
        rights_before = rights_path.read_bytes() if rights_path.exists() else None
        try:
            stage.rename(target)
            created_target = True
            findings = validate_public_previews(root)
            if findings:
                raise ValueError("public preview validation failed: " + "; ".join(findings))
            _primary().render_rights_index(root)
        except Exception:
            if created_target:
                shutil.rmtree(target)
            if rights_before is None:
                if rights_path.exists():
                    rights_path.unlink()
            else:
                rights_path.write_bytes(rights_before)
            raise
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "register-batch", "ingest", "compose", "audit", "gallery", "approve", "promote"):
        command = commands.add_parser(name)
        command.add_argument("--run-id", required=True)
        if name == "prepare":
            command.add_argument("--source-case", required=True)
        if name == "register-batch":
            command.add_argument("--manifest", type=Path, required=True)
        if name in {"ingest", "compose", "audit", "gallery", "approve"}:
            command.add_argument("--style")
        if name == "ingest":
            command.add_argument("--board", help=argparse.SUPPRESS)
            command.add_argument("--image", type=Path, required=True)
            command.add_argument("--generation-record", type=Path, required=True)
            command.add_argument("--correction-record", type=Path)
            command.add_argument("--failed-retry-record", type=Path)
        if name == "approve":
            command.add_argument("--review", type=Path, required=True, help="Completed human review JSON; agents must never fill real QA.")
        if name == 'compose':
            command.add_argument('--layout-json', type=Path, required=True)
            command.add_argument('--font', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "ingest" and args.board:
        parser.error("--board is superseded; use --style <registered-slug>")
    if args.command in {"ingest", "compose", "approve"} and not args.style:
        parser.error(f"{args.command} requires --style <registered-slug>")
    try:
        if args.command == "register-batch":
            result = register_batch(args.root, args.run_id, read_json(args.manifest))
        elif args.command == "ingest":
            correction = read_json(args.correction_record) if args.correction_record else None
            failed_retry = read_json(args.failed_retry_record) if args.failed_retry_record else None
            result = ingest(
                args.root,
                args.run_id,
                args.style,
                args.image,
                read_json(args.generation_record),
                correction=correction,
                failed_retry=failed_retry,
            )
        elif args.command == 'compose':
            result = compose(args.root, args.run_id, args.style, read_json(args.layout_json), args.font)
        elif args.command == "approve":
            result = approve(args.root, args.run_id, args.style, read_json(args.review))
        elif args.command in {"audit", "gallery"}:
            result = globals()[args.command](args.root, args.run_id, style=args.style)
        else:
            result = globals()[args.command](args.root, args.run_id, args.source_case) if args.command == "prepare" else globals()[args.command](args.root, args.run_id)
        print(str(result) if isinstance(result, Path) else json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "audit" and result else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
