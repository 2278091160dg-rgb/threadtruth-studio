#!/usr/bin/env python3
"""Build the public Plugin envelope from a fixed allowlist.

This script never publishes or installs anything. It stages only the Plugin
manifest, runtime skill, and user-facing release documents; development evals,
tests, and tools remain outside the archive.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path


PUBLIC_FILES = (
    "install-local.py",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "README.zh-CN.md",
    "USER-GUIDE.html",
    "MIGRATION.md",
    "PROVENANCE.md",
    "RELEASE.md",
    "ROADMAP.md",
    "SECURITY.md",
)
SOURCE_DIRS = (".codex-plugin", "skills", "docs")


def _validate_public_demo(root: Path) -> None:
    module_path = Path(__file__).with_name("demo_media.py")
    spec = importlib.util.spec_from_file_location("threadtruth_demo_media", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load public demo rights validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    findings = module.validate_public_cases(root)
    if findings:
        raise ValueError("public demo rights validation failed:\n" + "\n".join(findings))
    preview_path = Path(__file__).with_name("style_preview.py")
    preview_spec = importlib.util.spec_from_file_location("threadtruth_release_previews", preview_path)
    if preview_spec is None or preview_spec.loader is None:
        raise RuntimeError("cannot load preview release validator")
    preview = importlib.util.module_from_spec(preview_spec)
    preview_spec.loader.exec_module(preview)
    collections = preview.all_preview_collections(root)
    allowed = {"white-vest-24-v1", "beige-blazer-denim-outfit-24-v1"}
    if set(collections) - allowed or "white-vest-24-v1" not in collections:
        raise ValueError("public demo rights validation failed:\npreview collection allowlist mismatch")
    white_vest = collections["white-vest-24-v1"]
    if white_vest.get("schema_version") != "4.0" or len(preview.public_assets(white_vest)) != 72:
        raise ValueError("public demo rights validation failed:\nfrozen white-vest release assets invalid")
    outfit = collections.get("beige-blazer-denim-outfit-24-v1")
    if outfit is not None and (
        outfit.get("schema_version") != "5.0"
        or outfit.get("status") != "approved"
        or outfit.get("source", {}).get("case_id") != "beige-blazer-denim-outfit"
        or len(preview.public_assets(outfit)) != 72
    ):
        raise ValueError("public demo rights validation failed:\noutfit preview release assets invalid")


def _copy_allowlist(root: Path, stage: Path) -> None:
    for name in SOURCE_DIRS:
        source = root / name
        if not source.is_dir():
            raise FileNotFoundError(f"missing release directory: {source}")
        shutil.copytree(
            source,
            stage / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"),
        )
    for name in PUBLIC_FILES:
        source = root / name
        if not source.is_file():
            raise FileNotFoundError(f"missing release file: {source}")
        shutil.copy2(source, stage / name)


def _zip_tree(stage: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(stage.parent).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".py" else 0o644) << 16
            bundle.writestr(info, path.read_bytes())


def build_release(root: Path, output_dir: Path) -> tuple[Path, Path]:
    root = root.resolve()
    output_dir = output_dir.resolve()
    _validate_public_demo(root)
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text())
    version = manifest["version"]
    artifact_name = f"threadtruth-studio-{version}"
    stage = output_dir / artifact_name
    archive = output_dir / f"{artifact_name}.zip"
    checksum = output_dir / f"{artifact_name}.zip.sha256"

    if stage == root or stage in root.parents:
        raise ValueError("release output must not contain the source repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    _copy_allowlist(root, stage)
    if archive.exists():
        archive.unlink()
    _zip_tree(stage, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n")
    return archive, checksum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.root / "dist"
    archive, checksum = build_release(args.root, output)
    print(f"built {archive}")
    print(f"checksum {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
