#!/usr/bin/env python3
"""Audit D1 evidence directories for threadtruth-studio.

This is a read-only verifier for the local evidence shape used by the
style-pack D1 batch and A-anchor raw-event packets:

- one evidence directory per pack, named ``<pack>-d1``;
- exactly ``look-1.png`` ... ``look-6.png`` in each directory;
- each file is a PNG and has MD5/SHA256 recorded in README.md;
- MD5 values are unique within each pack;
- README/MATRIX wording keeps the boundary: D1 host-caveat evidence is not
  a tracked maturity upgrade.

A-anchor mode audits directories named by pack slug under an
``a-anchor-raw-event-*`` root, plus ``hashes.txt``, ``raw-event-count.txt``,
``cache-sources.txt``, and ``pack-local-audit.txt``.

Exit codes: 0=PASS, 1=FAIL, 2=usage error.
Dependencies: standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_NAMES = [f"look-{i}.png" for i in range(1, 7)]
EXPECTED_PROMPT_NAMES = [f"look-{i}.prompt.txt" for i in range(1, 7)]
A_ANCHOR_REQUIRED_FILES = [
    "README.md",
    "hashes.txt",
    "cache-sources.txt",
    "raw-event-count.txt",
    "pack-local-audit.txt",
]


def digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise ValueError("not PNG image data")
    return struct.unpack(">II", data[16:24])


def normalized_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def matrix_rows(matrix_path: Path | None) -> dict[str, str]:
    if not matrix_path or not matrix_path.exists():
        return {}
    rows: dict[str, str] = {}
    for line in matrix_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|", line)
        if m:
            rows[m.group(1)] = line
    return rows


def text_has_open_findings_zero(text: str) -> bool:
    return bool(re.search(r"open[\s_-]findings\s*[:=]\s*\**0\b", text, re.IGNORECASE))


def text_mentions_structured_raw_event_zero(text: str) -> bool:
    patterns = [
        r"structured raw-event count\s*(?:total)?\s*[:=]\s*0\b",
        r"observed_total_structured_image_generation_end_count\s*:\s*0\b",
        r"structured_image_generation_end_count\s*:\s*0\b",
        r"observed result\s*:\s*`?0(?:\s*\+\s*0)*\s*=\s*0`?",
        r"structured [`\"]?image_generation_end[`\"]? count (?:is |= )0\b",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def text_mentions_no_tracked_upgrade(text: str) -> bool:
    low = text.lower()
    candidate_blocked = bool(
        re.search(r"(?:not|no)\s+`?candidate`?", low)
        or re.search(r"do not mark[^.\n|]*`?candidate`?", low)
        or re.search(r"does not support tracked[^.\n|]*`?candidate`?", low)
        or re.search(r"cannot support (?:a )?tracked[^.\n|]*`?candidate`?", low)
    )
    verified_blocked = bool(
        re.search(r"(?:not|no)\s+`?verified-codex`?", low)
        or re.search(r"do not mark[^.\n|]*`?verified-codex`?", low)
        or re.search(r"does not support tracked[^.\n|]*`?verified-codex`?", low)
        or re.search(r"cannot support (?:a )?tracked[^.\n|]*`?verified-codex`?", low)
    )
    broad_no_upgrade = any(
        re.search(pattern, low)
        for pattern in [
            r"\bno tracked (?:maturity|release|status|upgrade)",
            r"\bno maturity upgrade\b",
            r"\bdoes not support tracked (?:maturity|release|upgrade)",
            r"\bcannot support a tracked `?verified-codex`?",
            r"\bunavailable/inconclusive for tracked `?verified-codex`?",
        ]
    )
    return (candidate_blocked and verified_blocked) or broad_no_upgrade


def check_hashes_in_text(label: str, text: str, files: list[dict[str, object]]) -> list[str]:
    failures: list[str] = []
    for item in files:
        name = str(item["name"])
        md5 = str(item["md5"])
        sha256 = str(item["sha256"])
        if name not in text:
            failures.append(f"{label} missing file row/name for {name}")
        if md5 not in text:
            failures.append(f"{label} missing MD5 for {name}: {md5}")
        if sha256 not in text:
            failures.append(f"{label} missing SHA256 for {name}: {sha256}")
    return failures


def check_style_pack_readme(
    pack: str, readme: Path, files: list[dict[str, object]]
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    text = normalized_text(readme)
    low = text.lower()
    if not text:
        failures.append("README.md missing")
        return failures, warnings

    if "d1 verified evidence" not in low or "host caveat accepted" not in low:
        failures.append("README missing D1 verified evidence with host caveat accepted status")
    if not text_has_open_findings_zero(text):
        failures.append("README missing Open findings: 0")
    if "verified-codex" not in low:
        warnings.append("README does not mention tracked VERIFIED-CODEX boundary")
    if "maturity" not in low:
        warnings.append("README does not mention tracked maturity boundary")
    if "raw" not in low or "event_msg" not in low:
        warnings.append("README does not mention raw event host caveat")

    failures.extend(check_hashes_in_text("README", text, files))

    if pack not in readme.parent.name:
        warnings.append(f"README parent directory name does not include pack slug {pack!r}")
    return failures, warnings


def check_a_anchor_artifacts(d: Path, files: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    for name in A_ANCHOR_REQUIRED_FILES:
        p = d / name
        if not p.exists():
            failures.append(f"{name} missing")
        elif not normalized_text(p).strip():
            # Empty required artifacts must FAIL, not silently skip the
            # boundary/hash content checks gated on non-empty text below.
            failures.append(f"{name} empty")
    for name in EXPECTED_PROMPT_NAMES + ["prompts.md"]:
        if not (d / name).exists():
            warnings.append(f"{name} missing")

    readme = normalized_text(d / "README.md")
    low = readme.lower()
    if readme:
        if "d1 six-image evidence" not in low and "a-anchor raw-event d1" not in low:
            failures.append("README missing A-anchor D1 six-image evidence status")
        if not text_has_open_findings_zero(readme):
            failures.append("README missing Open findings: 0")
        if not text_mentions_structured_raw_event_zero(readme):
            failures.append("README missing structured raw-event count = 0 boundary")
        if not text_mentions_no_tracked_upgrade(readme):
            failures.append("README missing no tracked CANDIDATE/VERIFIED-CODEX boundary")
        failures.extend(check_hashes_in_text("README", readme, files))

    hashes = normalized_text(d / "hashes.txt")
    if hashes:
        failures.extend(check_hashes_in_text("hashes.txt", hashes, files))

    raw_event = normalized_text(d / "raw-event-count.txt")
    if raw_event:
        if not text_mentions_structured_raw_event_zero(raw_event):
            failures.append("raw-event-count.txt missing structured raw-event total count 0")
        if (
            "deferred(raw-event-schema-unavailable)" not in raw_event
            and "unavailable/inconclusive" not in raw_event.lower()
        ):
            failures.append("raw-event-count.txt missing deferred or unavailable raw-event boundary")
        if not text_mentions_no_tracked_upgrade(raw_event):
            failures.append("raw-event-count.txt missing no tracked maturity impact boundary")

    local_audit = normalized_text(d / "pack-local-audit.txt")
    if local_audit:
        if not re.search(r"(file_count_look_png\s*=\s*6|file_count\s*:\s*6)", local_audit):
            failures.append("pack-local-audit.txt missing file count 6")
        if not re.search(r"md5_unique_count\s*[:=]\s*6", local_audit):
            failures.append("pack-local-audit.txt missing md5_unique_count 6")
        if not re.search(r"(structured_raw_event_count|raw_event_structured_count)\s*[:=]\s*0", local_audit):
            failures.append("pack-local-audit.txt missing structured raw-event count 0")
        if not text_has_open_findings_zero(local_audit):
            failures.append("pack-local-audit.txt missing open_findings = 0")

    return failures, warnings


def check_matrix_row(pack: str, row: str | None, mode: str) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    if row is None:
        failures.append("MATRIX.md missing pack row")
        return failures, warnings

    row_low = row.lower()
    if mode == "style-pack-d1":
        if "d1 verified evidence" not in row_low or "host caveat accepted" not in row_low:
            failures.append("MATRIX row missing D1 host-caveat accepted evidence status")
        if "no maturity upgrade" not in row_low and "not tracked" not in row_low:
            warnings.append("MATRIX row does not state no tracked maturity upgrade")
        return failures, warnings

    if "d1 six-image evidence complete" not in row_low:
        failures.append("MATRIX row missing A-anchor D1 six-image evidence completion status")
    if not re.search(r"\|\s*6\s*\|", row):
        failures.append("MATRIX row missing image count 6")
    if not re.search(r"\|\s*0\s*\|", row):
        failures.append("MATRIX row missing structured raw-event count 0")
    if "raw-event" not in row_low or "deferred" not in row_low:
        failures.append("MATRIX row missing raw-event deferred boundary")
    if not text_mentions_no_tracked_upgrade(row):
        failures.append("MATRIX row missing not CANDIDATE / not VERIFIED-CODEX boundary")
    if pack not in row:
        warnings.append(f"MATRIX row does not visibly include pack slug {pack!r}")
    return failures, warnings


def audit_pack(d: Path, matrix: dict[str, str], mode: str) -> dict[str, object]:
    pack = d.name[:-3] if mode == "style-pack-d1" and d.name.endswith("-d1") else d.name
    failures: list[str] = []
    warnings: list[str] = []
    files: list[dict[str, object]] = []

    looks = sorted(p.name for p in d.glob("look-*.png"))
    if looks != EXPECTED_NAMES:
        failures.append(f"expected {EXPECTED_NAMES}, found {looks}")

    for name in EXPECTED_NAMES:
        path = d / name
        if not path.exists():
            continue
        try:
            width, height = png_dimensions(path)
        except Exception as exc:  # noqa: BLE001 - report as evidence failure
            failures.append(f"{name}: {exc}")
            width, height = 0, 0
        files.append(
            {
                "name": name,
                "path": str(path),
                "dimensions": [width, height],
                "md5": digest(path, "md5"),
                "sha256": digest(path, "sha256"),
            }
        )

    md5s = [str(item["md5"]) for item in files]
    if len(md5s) == 6 and len(set(md5s)) != 6:
        failures.append(f"MD5 unique count is {len(set(md5s))}, expected 6")

    if mode == "style-pack-d1":
        readme_fail, readme_warn = check_style_pack_readme(pack, d / "README.md", files)
        failures.extend(readme_fail)
        warnings.extend(readme_warn)
    else:
        artifact_fail, artifact_warn = check_a_anchor_artifacts(d, files)
        failures.extend(artifact_fail)
        warnings.extend(artifact_warn)

    row = matrix.get(pack)
    # a-anchor mode requires a MATRIX boundary row per pack: a missing/empty
    # MATRIX.md must FAIL (row=None) rather than silently skip the
    # raw-event-deferred / not-CANDIDATE / not-VERIFIED-CODEX guard.
    if matrix or mode == "a-anchor":
        matrix_fail, matrix_warn = check_matrix_row(pack, row, mode)
        failures.extend(matrix_fail)
        warnings.extend(matrix_warn)

    return {
        "pack": pack,
        "dir": str(d),
        "ok": not failures,
        "failures": failures,
        "warnings": warnings,
        "files": files,
        "md5_unique_count": len(set(md5s)),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only audit for threadtruth-studio D1 evidence directories."
    )
    parser.add_argument(
        "root",
        type=Path,
        help="Evidence root containing <pack>-d1 directories, or pack slug dirs with --mode a-anchor.",
    )
    parser.add_argument(
        "--mode",
        choices=["style-pack-d1", "a-anchor"],
        default="style-pack-d1",
        help="Evidence layout to audit. Default preserves the original *-d1 batch behavior.",
    )
    parser.add_argument("--matrix", type=Path, help="MATRIX.md path. Defaults to <root>/MATRIX.md when present.")
    parser.add_argument("--expected-dirs", type=int, help="Expected number of evidence directories.")
    parser.add_argument("--expected-total-images", type=int, help="Expected total look-*.png count.")
    parser.add_argument("--json", type=Path, help="Optional path to write a JSON report.")
    parser.add_argument("--quiet", action="store_true", help="Only print failures and final summary.")
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"[FAIL] evidence root not found or not a directory: {root}", file=sys.stderr)
        return 2

    matrix_path = args.matrix.expanduser().resolve() if args.matrix else root / "MATRIX.md"
    matrix = matrix_rows(matrix_path if matrix_path.exists() else None)
    if args.mode == "style-pack-d1":
        dirs = sorted(p for p in root.glob("*-d1") if p.is_dir())
    else:
        dirs = sorted(
            p
            for p in root.iterdir()
            if p.is_dir() and any((p / name).exists() for name in ("README.md", "look-1.png"))
        )
    packs = [audit_pack(d, matrix, args.mode) for d in dirs]
    total_images = sum(len(item["files"]) for item in packs)

    summary_failures: list[str] = []
    if args.expected_dirs is not None and len(dirs) != args.expected_dirs:
        summary_failures.append(f"expected {args.expected_dirs} evidence dirs, found {len(dirs)}")
    if args.expected_total_images is not None and total_images != args.expected_total_images:
        summary_failures.append(f"expected {args.expected_total_images} look PNGs, found {total_images}")

    failing = [p for p in packs if not p["ok"]]
    warning_count = sum(len(p["warnings"]) for p in packs)
    ok = not failing and not summary_failures
    report = {
        "ok": ok,
        "mode": args.mode,
        "root": str(root),
        "matrix": str(matrix_path) if matrix_path.exists() else None,
        "evidence_dirs": len(dirs),
        "d1_dirs": len(dirs) if args.mode == "style-pack-d1" else 0,
        "look_png_total": total_images,
        "summary_failures": summary_failures,
        "warning_count": warning_count,
        "packs": packs,
    }

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        print("=== d1-evidence-audit ===")
        print(f"mode={args.mode}")
        print(f"root={root}")
        print(f"matrix={matrix_path if matrix_path.exists() else 'N/A'}")
        print(f"evidence_dirs={len(dirs)}")
        print(f"look_png_total={total_images}")
        print(f"warnings={warning_count}")

    for msg in summary_failures:
        print(f"[FAIL] {msg}")
    for pack in packs:
        for msg in pack["failures"]:
            print(f"[FAIL] {pack['pack']}: {msg}")
        if not args.quiet:
            for msg in pack["warnings"]:
                print(f"[WARN] {pack['pack']}: {msg}")

    if ok:
        print(
            f"PASS: {len(dirs)} evidence dirs, {total_images} PNGs, "
            "per-pack hashes and README/MATRIX checks passed."
        )
        return 0

    print(f"FAIL: {len(failing)} pack(s) failed; {len(summary_failures)} summary failure(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
