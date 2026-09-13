"""Development-only, offline four-board evidence workflow. Never generates images.

Approval records are human attestations, not cryptographic identity proofs. The
caller must supply the human's actual decision; agents must never sign real QA.
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
BOARD_STYLES = {
    "A": "korean-cold-editorial ecommerce-studio clean-fit nordic-minimal athleisure gorpcore".split(),
    "B": "old-money quiet-luxury french-effortless british-heritage italian-luxe preppy".split(),
    "C": "american-street y2k-millennium workwear-vintage cityboy korean-menswear office-commute-women".split(),
    "D": "japanese-lifestyle balletcore coquette-ladylike resort-vacation neo-chinese guochao-street".split(),
}
AI_LABEL = "AI-generated style preview — not six independent final images."
CONFIRMATION = "I reviewed all 24 preview tiles against the authorized sources."
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
MAX_BYTES = 8 * 1024 * 1024


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def object_hash(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def child(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("unsafe path")
    root = root.resolve()
    candidate = root / relative
    if any(p.is_symlink() for p in [candidate, *candidate.parents] if p != root and root in p.parents):
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
    return value.strip().strip('"\'')


def _visual(text):
    # Conservative extraction: keep environment/attitude/light; omit clothing
    # clauses rather than inviting a pack's suggested material or silhouette.
    visual = _field(text, "visual_language")
    clauses = re.split(r"[;,]", visual)
    excluded = re.compile(r"garment|reference|silhouette|tailor|cashmere|wool|tweed|silk|linen|logo|denim|leather|dress|skirt|ribbon|lace|pleat|uniform|embroid|collar|button|construction|nylon|shirting|knitwear|proportions|layering|metallic accents|cotton|tulle|bows|feminine details|oriental structure", re.I)
    mood = "; ".join(c.strip() for c in clauses if c.strip() and not excluded.search(c) and c.strip() not in {"do not add", "remove"})
    mood = re.sub(r"\bmenswear\b", "urban", mood, flags=re.I)
    return {"mood": mood, "persona": _field(text, "model_persona"),
            "scene": _field(text, "scenes").split(" - ")[0].removeprefix("- "),
            "lighting": _field(text, "lighting_palette")}


def _source(root):
    primary = _primary()
    if primary.validate_public_primary_cases(root):
        raise ValueError("source primary evidence invalid")
    path = child(root, SOURCE_REF)
    rights = read_json(path)
    auth = rights["source_rights"]
    if rights["case_id"] != CASE or not all(auth.get(k) is True for k in
            ("public_use_authorized", "project_media_policy_accepted", "source_model_display_authorized")):
        raise ValueError("source rights incomplete")
    sources = [a for a in rights["assets"] if a["role"] == "source"]
    if len(sources) != 4:
        raise ValueError("four authorized sources required")
    base = str(Path(SOURCE_REF).parent)
    source = {"rights_ref": SOURCE_REF, "rights_sha256": digest(path.read_bytes()),
              "authorization": auth,
              "assets": [{"path": f"{base}/{a['path']}", "sha256": a["public_sha256"], "role": "garment-source"} for a in sources]}
    anchor = next(a for a in rights["assets"] if a["name"] == "look-1")
    return source, {"path": f"{base}/{anchor['path']}", "sha256": anchor["public_sha256"], "role": "identity-only"}


def _prompt(board, source, anchor):
    lines = [f"Create board {board['id']}: exactly 3 columns x 2 rows, six equal tiles, row-major order.",
             "Canvas 1536x1536; each tile 512x768 (2:3 portrait). No gutters, no merged tiles, one adult female per tile.",
             "Same adult female identity in all 24 tiles. Attached images 1-4 are the only garment truth.",
             "Preserve the source white hooded puffer vest: white color, hood shape, zipper, length, padding, seams and construction.",
             "Never replace the vest or invent details. Keep it clearly visible in each tile. No age or gender change.",
             "Attached image 5 (look-1) is identity-only: face/hair identity, never garment authority.",
             "All styles borrow mood, background, pose and lighting only; garment/source truth overrides every pack suggestion.",
             "Tension styles including menswear, balletcore, neo-Chinese and resort must not change garment or adult female.",
             AI_LABEL,
             "Draw a visible, unobtrusive English label 'AI PREVIEW / NOT FINAL' at the bottom right of the board. Do not cover any face or vest; no large centered watermark.",
             "Apart from that preview label, use small A1-style tile identifiers only; external gallery supplies the style names.",
             "Garment references: " + ", ".join(a["path"] for a in source["assets"]),
             "Identity reference: " + anchor["path"]]
    for tile in board["tiles"]:
        visual = tile["visual"]
        lines += ["", f"TILE {board['id']}{tile['ordinal']} / row {tile['row']} column {tile['column']} / {tile['style']}",
                  f"Pack version {tile['pack']['version']}; SHA256 {tile['pack']['sha256']}",
                  f"Mood only: {visual['mood']}", f"Attitude: {visual['persona']}",
                  f"Background: {visual['scene']}", f"Lighting/background palette: {visual['lighting']}",
                  "Retain white vest color and all source construction; styling suggestions cannot override source truth."]
    return "\n".join(lines) + "\n"


def _plan(root, run_id):
    run_dir(root, run_id)
    source, anchor = _source(root)
    packs = {p.stem.removesuffix(".pack") for p in child(root, PACK_ROOT).glob("*.pack.yaml") if not p.name.startswith("_")}
    if packs != {s for styles in BOARD_STYLES.values() for s in styles}:
        raise ValueError("unknown or missing style packs")
    boards = []
    for board_id, styles in BOARD_STYLES.items():
        board = {"id": board_id, "grid": {"columns": 3, "rows": 2}, "tiles": []}
        for n, style in enumerate(styles):
            relative = f"{PACK_ROOT}/{style}.pack.yaml"
            path = child(root, relative)
            raw = path.read_bytes()
            text = raw.decode()
            if _field(text, "slug") != style:
                raise ValueError("pack slug mismatch")
            board["tiles"].append({"ordinal": n + 1, "row": n // 3 + 1, "column": n % 3 + 1,
                                   "style": style, "pack": {"path": relative, "sha256": digest(raw), "version": _field(text, "version")},
                                   "visual": _visual(text)})
        board["prompt_sha256"] = digest(_prompt(board, source, anchor).encode())
        boards.append(board)
    return {"schema_version": "1.0", "run_id": run_id, "role": "style-preview", "status": "prepared",
            "source": source, "identity_anchor": anchor, "ai_label": AI_LABEL, "boards": boards}


def prepare(root, run_id):
    plan = _plan(root, run_id)
    directory = run_dir(root, run_id)
    if directory.exists():
        existing = read_json(directory / "evidence.json")
        _check_plan(root, existing, directory)
        return existing
    directory.mkdir(parents=True)
    (directory / "prompts").mkdir()
    for board in plan["boards"]:
        (directory / "prompts" / f"board-{board['id']}.txt").write_text(_prompt(board, plan["source"], plan["identity_anchor"]), encoding="utf-8")
    write_json(directory / "evidence.json", plan)
    write_json(directory / "review-template.json", review_template(plan))
    return plan


def _check_plan(root, record, directory=None):
    if record.get("status") not in {"prepared", "awaiting-human-review", "approved"}:
        raise ValueError("invalid preview state")
    if directory is not None and record.get("run_id") != directory.name:
        raise ValueError("run id mismatch")
    expected = _plan(root, record["run_id"])
    if set(record) - (set(expected) | {"human_review"}):
        raise ValueError("unexpected evidence fields")
    for key in ("schema_version", "run_id", "role", "source", "identity_anchor", "ai_label"):
        if record.get(key) != expected[key]:
            raise ValueError(f"stale or invalid {key}")
    if len(record["boards"]) != 4:
        raise ValueError("four boards required")
    for board, planned in zip(record["boards"], expected["boards"]):
        if set(board) - (set(planned) | {"path", "sha256", "width", "height", "bytes", "original_sha256", "generation"}):
            raise ValueError("unexpected board fields")
        if any(board.get(k) != v for k, v in planned.items()):
            raise ValueError("stale pack, prompt or tile mapping")
        if directory is not None:
            prompt = child(directory, f"prompts/board-{board['id']}.txt")
            if digest(prompt.read_bytes()) != board["prompt_sha256"]:
                raise ValueError("prompt hash mismatch")


def _image(path):
    from PIL import Image
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("preview exceeds optimized image limit")
    with Image.open(path) as image:
        image.load()
        if image.format != "JPEG" or image.width != image.height or image.width % 3 or image.height % 2 or image.width < 600:
            raise ValueError("preview requires square JPEG grid divisible by 3 columns and 2 rows")
        if image.getexif() or image.info.get("comment") or image.info.get("icc_profile"):
            raise ValueError("preview contains embedded metadata")
        return {"sha256": digest(data), "bytes": len(data), "width": image.width, "height": image.height}


def _generation(generation, board):
    if not isinstance(generation, dict) or set(generation) != {"tool", "call_id", "generated_at", "prompt_sha256"}:
        raise ValueError("generation record fields invalid")
    if generation["tool"] != "native-imagegen" or not isinstance(generation["call_id"], str) or not ID.fullmatch(generation["call_id"]):
        raise ValueError("native generation call required")
    if generation["prompt_sha256"] != board["prompt_sha256"]:
        raise ValueError("generation prompt mismatch")
    _primary().parse_iso_z(generation["generated_at"])


def ingest(root, run_id, board_id, image, generation):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    _check_plan(root, record, directory)
    if record["status"] not in {"prepared", "awaiting-human-review"} or board_id not in BOARD_STYLES:
        raise ValueError("invalid ingest state or board")
    board = next(b for b in record["boards"] if b["id"] == board_id)
    _generation(generation, board)
    original = digest(image.read_bytes())
    if "path" in board:
        if board["original_sha256"] == original and board["generation"] == generation and _image(child(directory, board["path"])) == {k: board[k] for k in ("sha256", "bytes", "width", "height")}:
            return record
        raise ValueError("refuse to overwrite registered board")
    for other in record["boards"]:
        if other.get("original_sha256") == original or other.get("generation", {}).get("call_id") == generation["call_id"]:
            raise ValueError("duplicate board or native call")
    from PIL import Image, ImageOps
    target = child(directory, f"board-{board_id}.jpg")
    receipt = child(directory, f"native-receipts/board-{board_id}.json")
    if target.exists() or receipt.exists():
        raise ValueError("refuse to overwrite unregistered asset")
    with tempfile.TemporaryDirectory(dir=directory) as temp:
        output = Path(temp) / "board.jpg"
        with Image.open(image) as opened:
            source_extension = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}.get(opened.format)
            if source_extension is None:
                raise ValueError("unsupported native image format")
            native_relative = f"native-outputs/board-{board_id}.{source_extension}"
            native = child(directory, native_relative)
            if native.exists():
                raise ValueError("refuse to overwrite native output")
            clean = ImageOps.exif_transpose(opened).convert("RGB")
            clean.save(output, "JPEG", quality=86, optimize=True, progressive=True)
        metadata = _image(output)
        if any(b.get("sha256") == metadata["sha256"] for b in record["boards"]):
            raise ValueError("duplicate optimized board")
        shutil.copyfile(output, target)
    native.parent.mkdir(exist_ok=True)
    shutil.copyfile(image, native)
    receipt.parent.mkdir(exist_ok=True)
    write_json(receipt, {"native_output_path": str(image.resolve()), "retained_path": native_relative,
                         "original_sha256": original, "generation": generation})
    board.update(metadata, path=target.name, original_sha256=original, generation=generation)
    record["status"] = "awaiting-human-review"
    write_json(directory / "evidence.json", record)
    write_json(directory / "review-template.json", review_template(record))
    return record


def review_template(record):
    return {"reviewer": "", "reviewed_at": "", "confirmation": "", "ai_label_acknowledged": False,
            "public_use_approved": False, "evidence_sha256": _review_hash(record),
            "tiles": [{"board": b["id"], "ordinal": t["ordinal"], "style": t["style"],
                       "board_sha256": b.get("sha256", ""), "product": "pending", "style_check": "pending",
                       "identity_layout": "pending"} for b in record["boards"] for t in b["tiles"]]}


def _review_hash(record):
    return object_hash({k: v for k, v in record.items() if k not in {"status", "human_review"}})


def _check_review(record):
    review = record.get("human_review")
    template = review_template(record)
    if not isinstance(review, dict) or set(review) != set(template):
        raise ValueError("human review incomplete")
    primary = _primary()
    if not primary.GITHUB_REVIEWER.fullmatch(str(review["reviewer"])) or review["confirmation"] != CONFIRMATION:
        raise ValueError("explicit human confirmation required")
    if review["ai_label_acknowledged"] is not True or review["public_use_approved"] is not True or review["evidence_sha256"] != template["evidence_sha256"]:
        raise ValueError("review not bound to current evidence and AI disclosure")
    if len(review["tiles"]) != 24:
        raise ValueError("24 tile reviews required")
    for tile, expected in zip(review["tiles"], template["tiles"]):
        expected.update(product="pass", style_check="pass", identity_layout="pass")
        if tile != expected:
            raise ValueError("tile product/style/identity-layout QA incomplete")
    reviewed_at = primary.parse_iso_z(review["reviewed_at"])
    if any(primary.parse_iso_z(b["generation"]["generated_at"]) > reviewed_at for b in record["boards"]):
        raise ValueError("review predates generation")


def _validate(root, record, directory, require_approval, local):
    _check_plan(root, record, directory if local else None)
    if record["status"] not in {"awaiting-human-review", "approved"}:
        raise ValueError("invalid preview state")
    hashes, calls = [], []
    for board in record["boards"]:
        if board.get("path") != f"board-{board['id']}.jpg":
            raise ValueError("board path invalid")
        actual = _image(child(directory, board["path"]))
        if any(board.get(k) != v for k, v in actual.items()):
            raise ValueError("board hash or metadata mismatch")
        if not re.fullmatch(r"[a-f0-9]{64}", str(board.get("original_sha256"))):
            raise ValueError("original board hash missing")
        _generation(board["generation"], board)
        if local:
            receipt = read_json(child(directory, f"native-receipts/board-{board['id']}.json"))
            if receipt.get("generation") != board["generation"] or receipt.get("original_sha256") != board["original_sha256"]:
                raise ValueError("native receipt mismatch")
            if digest(child(directory, receipt["retained_path"]).read_bytes()) != board["original_sha256"]:
                raise ValueError("native output hash mismatch")
        if _primary().parse_iso_z(board["generation"]["generated_at"]) < _primary().parse_iso_z(record["source"]["authorization"]["declared_at"]):
            raise ValueError("generation predates source authorization")
        hashes.append(board["sha256"])
        calls.append(board["generation"]["call_id"])
    if len(set(hashes)) != 4 or len(set(calls)) != 4:
        raise ValueError("four distinct boards and native calls required")
    if require_approval or record["status"] == "approved" or "human_review" in record:
        _check_review(record)
        if record["status"] != "approved":
            raise ValueError("approval state invalid")
    if _primary().has_sensitive_public_text(record):
        raise ValueError("sensitive public text")


def audit(root, run_id, require_approval=False):
    try:
        directory = run_dir(root, run_id)
        _validate(root, read_json(directory / "evidence.json"), directory, require_approval, True)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
        return [str(error)]
    return []


def approve(root, run_id, review):
    findings = audit(root, run_id)
    if findings:
        raise ValueError("; ".join(findings))
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    if record["status"] == "approved" and record.get("human_review") != review:
        raise ValueError("refuse to overwrite human approval")
    record["human_review"] = copy.deepcopy(review)
    record["status"] = "approved"
    _validate(root, record, directory, True, True)
    write_json(directory / "evidence.json", record)
    return record


def _html(record):
    sections = []
    for board in record["boards"]:
        labels = "".join(f"<li>{board['id']}{t['ordinal']}: {html.escape(t['style'])}</li>" for t in board["tiles"])
        visual = f'<img src="{html.escape(board["path"])}" alt="Board {board["id"]}, six preview tiles">' if "path" in board else "<p>Not generated</p>"
        sections.append(f"<section><h2>Board {board['id']}</h2>{visual}<ol>{labels}</ol></section>")
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Style preview review</title><style>body{max-width:1100px;margin:2rem auto;font-family:system-ui}img{width:100%}ol{display:grid;grid-template-columns:repeat(3,1fr)}li{padding:1rem}</style><body><h1>' + AI_LABEL + '</h1><p>3 columns × 2 rows; row-major mapping. Machine audit checks files and evidence only. Human review checks product, style and identity/layout for every tile.</p>' + "".join(sections) + '</body></html>\n'


def gallery(root, run_id):
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    _check_plan(root, record, directory)
    path = directory / "gallery.html"
    path.write_text(_html(record), encoding="utf-8")
    return path


def _readme(record):
    return f"# Style preview: {record['run_id']}\n\n{AI_LABEL}\n\n[Review four boards and 24 tile labels](index.html). Each board is 3 columns × 2 rows, row-major.\n\nSource authorization: [primary rights](../../primary-cases/{CASE}/rights.json). Four real garment sources; look-1 is identity-only.\n\n[evidence.json](evidence.json) binds source rights, actual pack versions/hashes, prompts, four native calls, optimized JPEG hashes and human per-tile QA. Machine verification does not judge subjective visual quality or authenticate the reviewer's identity.\n\nCC0 applies only to the extent the project can grant rights; Apache-2.0 does not cover media. AI-generated content requires applicable labeling. These previews never count as independent finals or runtime maturity evidence.\n"


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
            if record["run_id"] != directory.name:
                raise ValueError("run id mismatch")
            _validate(root, record, directory, True, False)
            expected = {"evidence.json", "README.md", "index.html", *[f"board-{b}.jpg" for b in "ABCD"]}
            if {p.name for p in directory.iterdir()} != expected or any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
                raise ValueError("unregistered or missing preview artifact")
            if (directory / "README.md").read_text() != _readme(record) or (directory / "index.html").read_text() != _html(record):
                raise ValueError("stale preview disclosure or gallery")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as error:
            findings.append(f"{directory.name}: {error}")
    return findings


def preview_links(root):
    findings = validate_public_previews(root)
    if findings:
        raise ValueError("; ".join(findings))
    links = {}
    for path in sorted(child(root, "docs/demo/style-previews").glob("*/evidence.json")):
        record = read_json(path)
        for board in record["boards"]:
            for tile in board["tiles"]:
                links[tile["style"]] = {"run_id": record["run_id"], "board": board["id"], "tile": tile["ordinal"],
                                        "path": f"style-previews/{record['run_id']}/{board['path']}", "sha256": board["sha256"]}
    return links


def promote(root, run_id):
    findings = audit(root, run_id, require_approval=True)
    if findings:
        raise ValueError("; ".join(findings))
    directory = run_dir(root, run_id)
    record = read_json(directory / "evidence.json")
    target = child(root, f"docs/demo/style-previews/{run_id}")
    if target.exists():
        if read_json(target / "evidence.json") != record or validate_public_previews(root):
            raise ValueError("refuse to overwrite different or invalid public evidence")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as temp:
            stage = Path(temp) / "public"
            stage.mkdir()
            for board in record["boards"]:
                shutil.copyfile(child(directory, board["path"]), stage / board["path"])
            write_json(stage / "evidence.json", record)
            (stage / "README.md").write_text(_readme(record), encoding="utf-8")
            (stage / "index.html").write_text(_html(record), encoding="utf-8")
            stage.rename(target)
    links = preview_links(root)
    index_path = child(root, "docs/demo/style-index.json")
    index = read_json(index_path)
    for item in index["styles"]:
        item["preview"] = links.get(item["slug"])
    write_json(index_path, index)
    primary = _primary()
    primary.render_style_pages(root)
    primary.render_rights_index(root)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "ingest", "audit", "gallery", "approve", "promote"):
        command = commands.add_parser(name)
        command.add_argument("--run-id", required=True)
        if name == "ingest":
            command.add_argument("--board", choices=list(BOARD_STYLES), required=True)
            command.add_argument("--image", type=Path, required=True)
            command.add_argument("--generation-record", type=Path, required=True)
        if name == "approve":
            command.add_argument("--review", type=Path, required=True,
                                 help="Completed human review JSON. Never fill or approve real QA on behalf of a human.")
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            result = ingest(args.root, args.run_id, args.board, args.image, read_json(args.generation_record))
        elif args.command == "approve":
            result = approve(args.root, args.run_id, read_json(args.review))
        else:
            result = globals()[args.command](args.root, args.run_id)
        print(str(result) if isinstance(result, Path) else json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == "audit" and result else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
