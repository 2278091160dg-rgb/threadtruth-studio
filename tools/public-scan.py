#!/usr/bin/env python3
"""Scan the public tree and optional Git history for private or secret material."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


PATTERNS = {
    "absolute macOS user path": re.compile("/" + "Users/" + r"[A-Za-z0-9._-]+/"),
    "QQ email": re.compile(r"[A-Za-z0-9._%+-]+@" + r"qq\.com", re.I),
    "private key header": re.compile("BEGIN " + r"(?:RSA|OPENSSH|EC) PRIVATE KEY"),
    "secret-shaped token": re.compile("sk" + r"-[A-Za-z0-9_-]{20,}"),
    "cookie header": re.compile(r"(?im)^cookie\s*:\s*[^<\s][^\r\n]{8,}$"),
    "home-relative private path": re.compile("~" + "/" + r"(?!\.)[A-Za-z0-9._-]+/"),
    "session identifier": re.compile("session" + r"\s+" + "0" + r"[0-9a-f]{7,}", re.I),
}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".html", ".py", ".txt"}


def scan_text(text: str, source: str) -> list[str]:
    findings = []
    for label, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{source}:{line}: {label}")
    return findings


def scan_tree(root: Path) -> list[str]:
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "dist" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        findings.extend(scan_text(path.read_text(errors="ignore"), str(path.relative_to(root))))
    return findings


def scan_history(root: Path) -> list[str]:
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=root, capture_output=True, text=True
    )
    if probe.returncode:
        return []
    result = subprocess.run(
        ["git", "log", "-p", "--all", "--no-ext-diff"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
    )
    return scan_text(result.stdout, "git-history")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = scan_tree(args.root.resolve())
    if args.history:
        findings.extend(scan_history(args.root.resolve()))
    if findings:
        print("PUBLIC SCAN FAIL")
        print("\n".join(findings))
        return 1
    print("PUBLIC SCAN PASS" + (" (tree + history)" if args.history else " (tree)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
