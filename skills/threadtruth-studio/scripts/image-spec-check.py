#!/usr/bin/env python3
"""Validate PNG aspect-ratio and batch-dimension contracts without mutation.

The native image host may return content-adaptive dimensions even when a prompt
asks for a fixed canvas. This checker reads the PNG IHDR metadata and turns that
host uncertainty into a deterministic commercial QA gate.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def positive_pair(value: str, separator: str, label: str) -> tuple[int, int]:
    try:
        left, right = value.lower().split(separator, 1)
        first, second = int(left), int(right)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError(
            f"{label} must use positive integers separated by '{separator}'"
        ) from exc
    if first <= 0 or second <= 0:
        raise argparse.ArgumentTypeError(f"{label} values must be positive")
    return first, second


def parse_ratio(value: str) -> tuple[int, int]:
    return positive_pair(value, ":", "ratio")


def parse_size(value: str) -> tuple[int, int]:
    return positive_pair(value, "x", "size")


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file or PNG signature is truncated")
    chunk_length = struct.unpack(">I", header[8:12])[0]
    if header[12:16] != b"IHDR" or chunk_length < 13:
        raise ValueError("PNG IHDR chunk is missing or invalid")
    return struct.unpack(">II", header[16:24])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read PNG metadata and fail when an image misses the target aspect "
            "ratio, optional exact size, or shared batch dimensions."
        )
    )
    parser.add_argument(
        "--ratio",
        required=True,
        type=parse_ratio,
        metavar="W:H",
        help="Required exact reduced-or-equivalent aspect ratio, for example 2:3.",
    )
    parser.add_argument(
        "--size",
        type=parse_size,
        metavar="WIDTHxHEIGHT",
        help="Optional required exact pixel dimensions.",
    )
    parser.add_argument(
        "--same-size",
        action="store_true",
        help="Require every input to match the first input's pixel dimensions.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one machine-readable JSON object instead of the text report.",
    )
    parser.add_argument("files", nargs="+", type=Path, metavar="PNG")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    ratio_width, ratio_height = args.ratio

    if args.size:
        size_width, size_height = args.size
        if size_width * ratio_height != size_height * ratio_width:
            parser.error("--size dimensions do not match --ratio")

    baseline_size: tuple[int, int] | None = None
    results: list[dict[str, object]] = []
    all_passed = True

    for index, path in enumerate(args.files):
        errors: list[str] = []
        width: int | None = None
        height: int | None = None
        try:
            width, height = png_dimensions(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))

        if width is not None and height is not None:
            current_size = (width, height)
            ratio_passed = width * ratio_height == height * ratio_width
            size_passed = not args.size or current_size == args.size
            if not ratio_passed:
                errors.append(
                    f"ratio {width}:{height} does not equal target "
                    f"{ratio_width}:{ratio_height}"
                )
            if not size_passed and args.size:
                errors.append(
                    f"size {width}x{height} does not equal target "
                    f"{args.size[0]}x{args.size[1]}"
                )
            if args.same_size:
                if index == 0:
                    if ratio_passed and size_passed:
                        baseline_size = current_size
                    else:
                        errors.append(
                            "first input failed the canvas contract and cannot "
                            "establish the batch baseline"
                        )
                elif baseline_size is None:
                    errors.append(
                        "batch baseline is unavailable because the first input "
                        "failed the canvas contract"
                    )
                elif current_size != baseline_size:
                    errors.append(
                        f"size {width}x{height} does not equal batch baseline "
                        f"{baseline_size[0]}x{baseline_size[1]}"
                    )

        passed = not errors
        all_passed = all_passed and passed
        results.append(
            {
                "file": str(path),
                "width": width,
                "height": height,
                "passed": passed,
                "errors": errors,
            }
        )

    report = {
        "target_ratio": f"{ratio_width}:{ratio_height}",
        "target_size": (
            f"{args.size[0]}x{args.size[1]}" if args.size else None
        ),
        "require_same_size": args.same_size,
        "baseline_size": (
            f"{baseline_size[0]}x{baseline_size[1]}" if baseline_size else None
        ),
        "passed": all_passed,
        "files": results,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"target_ratio={report['target_ratio']} "
            f"target_size={report['target_size'] or 'unset'} "
            f"same_size={str(args.same_size).lower()}"
        )
        for item in results:
            dimensions = (
                f"{item['width']}x{item['height']}"
                if item["width"] is not None
                else "unreadable"
            )
            status = "PASS" if item["passed"] else "FAIL"
            print(f"{status} {item['file']} {dimensions}")
            for error in item["errors"]:
                print(f"  - {error}")
        print(f"result={'PASS' if all_passed else 'FAIL'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
