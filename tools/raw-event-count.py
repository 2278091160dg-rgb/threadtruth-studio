#!/usr/bin/env python3
"""Count structured native image-generation events in Codex rollout sessions.

Read-only raw-event gate helper for threadtruth-studio. It implements the
A-anchor "unlock path": the only way to support a tracked ``VERIFIED-CODEX``
discussion is a real Codex TUI rollout session JSONL
(``~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl``) that exposes structured
``image_generation_end`` events. Headless ``codex exec --json`` thread streams do
NOT emit these events (observed count 0), so they cannot clear this gate.

This tool parses each session line as JSON and counts a record only when a
structured ``type`` field (top-level or under ``payload``/``msg``/``event``/
``event_msg``) equals ``image_generation_end``. Prose mentions of the string in
prompts/READMEs/handoffs are not structured ``type`` fields and are never
counted.

It does NOT generate images, change maturity, read secrets, or touch the
network. The only optional write is a user-specified ``--json`` report path.

Exit codes: 0=PASS, 1=FAIL (count mismatch), 2=usage error.
Dependencies: standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EVENT_NAME = "image_generation_end"


def event_type_values(obj: object):
    """Yield candidate structured ``type`` values from one rollout record."""
    if not isinstance(obj, dict):
        return
    yield obj.get("type")
    for key in ("payload", "msg", "event", "event_msg"):
        sub = obj.get(key)
        if isinstance(sub, dict):
            yield sub.get("type")
            inner = sub.get("payload")
            if isinstance(inner, dict):
                yield inner.get("type")


def is_image_gen_end(obj: object) -> bool:
    return any(value == EVENT_NAME for value in event_type_values(obj) if value)


def count_session(path: Path) -> dict[str, int]:
    count = 0
    records = 0
    malformed = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if is_image_gen_end(obj):
                count += 1
    return {"count": count, "records": records, "malformed": malformed}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only structured count of image_generation_end events in "
        "Codex rollout session JSONL (A-anchor raw-event gate).",
    )
    parser.add_argument(
        "sessions",
        type=Path,
        nargs="+",
        help="One or more Codex rollout session JSONL paths "
        "(~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl). Do NOT pass codex exec "
        "--json /tmp thread streams; they do not expose the structured event.",
    )
    parser.add_argument(
        "--expected",
        type=int,
        default=6,
        help="Expected TOTAL structured image_generation_end count (default 6).",
    )
    parser.add_argument(
        "--min-per-session",
        type=int,
        default=0,
        help="Optional minimum structured count required in each session (default 0).",
    )
    parser.add_argument("--json", type=Path, help="Optional path to write a JSON report.")
    parser.add_argument("--quiet", action="store_true", help="Only print failures and final summary.")
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    sessions: list[dict[str, object]] = []
    for raw in args.sessions:
        path = raw.expanduser().resolve()
        if not path.exists() or not path.is_file():
            print(f"[FAIL] session not found or not a file: {path}", file=sys.stderr)
            return 2
        stats = count_session(path)
        sessions.append({"session": str(path), **stats})

    total = sum(int(s["count"]) for s in sessions)
    failures: list[str] = []
    if total != args.expected:
        failures.append(f"expected total structured {EVENT_NAME} count {args.expected}, found {total}")
    if args.min_per_session > 0:
        for s in sessions:
            if int(s["count"]) < args.min_per_session:
                failures.append(
                    f"session below floor ({args.min_per_session}): "
                    f"{s['session']} has {s['count']}"
                )

    ok = not failures
    report = {
        "ok": ok,
        "expected_total": args.expected,
        "observed_total_structured_image_generation_end_count": total,
        "min_per_session": args.min_per_session,
        "sessions": sessions,
        "failures": failures,
    }

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        print("=== raw-event-count ===")
        print(f"expected_total={args.expected}")
        print(f"observed_total_structured_image_generation_end_count={total}")
        for s in sessions:
            print(f"  {s['count']:>3}  ({s['records']} records, {s['malformed']} malformed)  {s['session']}")

    for msg in failures:
        print(f"[FAIL] {msg}")

    if ok:
        print(
            f"PASS: structured {EVENT_NAME} count = {total} across {len(sessions)} session(s); "
            "raw-event gate count met (still requires md5/visual/audit + user sign-off to upgrade)."
        )
        return 0

    if total == 0:
        print(
            "FAIL: structured count is 0 — this looks like a headless codex exec --json stream "
            "(no image_generation_end events). Re-run in a real Codex TUI session and use its "
            "~/.codex/sessions/.../rollout-*.jsonl; keep host-caveat, do not upgrade tracked maturity."
        )
    else:
        print(f"FAIL: {len(failures)} raw-event gate failure(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
