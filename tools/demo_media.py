#!/usr/bin/env python3
"""Govern rights-cleared public demo media outside the Plugin runtime."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shlex import quote
from urllib.parse import urlparse


SCHEMA_VERSION = "1.0"
MAX_QUERY_LENGTH = 80
DEFAULT_LIMIT = 8
MAX_LIMIT = 12
MAX_IMAGE_BYTES = 50 * 1024 * 1024
MIN_LONG_EDGE = 1200
DEMO_ROOT_FILES = {
    "GROWTH.md",
    "MEDIA-POLICY.md",
    "README.md",
    "RIGHTS.md",
    "STYLES.md",
    "primary-rights-v1.schema.json",
    "preview-source-v1.schema.json",
    "rights-v1.schema.json",
    "style-index.json",
    "style-preview-v1.schema.json",
    "style-preview-v2.schema.json",
    "style-preview-v4.schema.json",
}
DEMO_ROOT_DIRS = {"cases", "primary-cases", "preview-sources", "styles", "style-previews"}
PUBLIC_CASE_FILES = {"README.md", "rights.json", "source-metadata.json", "source.jpg"}
CC0_ID = "CC0-1.0"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
MET_POLICY_URL = "https://www.metmuseum.org/policies/image-resources"
APPROVAL_CONFIRMATION = "I reviewed this asset for public demo use"
REVIEW_CHECKS = (
    "no_person",
    "no_logo",
    "no_watermark",
    "physical_garment",
    "not_sensitive",
)
ALLOWED_HOSTS = {
    "collectionapi.metmuseum.org",
    "images.metmuseum.org",
    "www.metmuseum.org",
}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
PREVIEW_SOURCE_CASES = {"beige-blazer-denim-outfit"}
PREVIEW_SOURCE_FILES = {"README.md", "rights.json", "source.jpg"}
PREVIEW_SOURCE_LICENSE = "ThreadTruth-Demo-Only-1.0"

REJECTION_CODES = {
    "METADATA_NOT_PUBLIC_DOMAIN",
    "MISSING_PRIMARY_IMAGE",
    "WRONG_DEPARTMENT",
    "UNTRUSTED_HOST",
    "OBJECT_ID_MISMATCH",
    "LICENSE_NOT_CC0",
    "DOWNLOAD_TYPE_INVALID",
    "DOWNLOAD_TOO_LARGE",
    "IMAGE_CORRUPT",
    "IMAGE_TOO_SMALL",
    "DUPLICATE_HASH",
    "EVIDENCE_INCOMPLETE",
    "RUN_EXPIRED",
    "HUMAN_REVIEW_INCOMPLETE",
    "PERSON_PRESENT",
    "LOGO_OR_TRADEMARK",
    "WATERMARK_PRESENT",
    "NOT_PHYSICAL_GARMENT",
    "CULTURAL_OR_SENSITIVE_CONTEXT",
    "SOURCE_METADATA_CHANGED",
    "STATE_TRANSITION_INVALID",
}

FORWARD_TRANSITIONS = {
    "discovered": {"fetched", "rights-rejected", "expired"},
    "fetched": {"machine-passed", "rights-rejected", "expired"},
    "machine-passed": {"human-approved", "rights-rejected", "expired"},
    "human-approved": {"promoted", "rights-rejected"},
    "promoted": set(),
    "rights-rejected": {"expired"},
    "expired": set(),
}


def validate_transition(current: str, target: str) -> None:
    if target not in FORWARD_TRANSITIONS.get(current, set()):
        raise ValueError(f"STATE_TRANSITION_INVALID: {current} -> {target}")


def validate_query(value: str) -> str:
    query = value.strip()
    if not query or len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"query must contain 1..{MAX_QUERY_LENGTH} characters")
    return query


def validate_limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_LIMIT:
        raise ValueError(f"limit must be an integer from 1 through {MAX_LIMIT}")
    return value


def validate_identifier(value: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError("identifier must contain only safe ASCII filename characters")
    return value


def validate_reviewer(value: str) -> str:
    if value == "github:YOUR-HANDLE" or not isinstance(value, str) or not re.fullmatch(
        r"github:(?=.{1,39}$)[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", value
    ):
        raise ValueError("HUMAN_REVIEW_INCOMPLETE: reviewer must be a public GitHub handle")
    return value


def iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def candidate_root(root: Path) -> Path:
    return root.resolve() / ".threadtruth" / "demo-candidates"


def run_path(root: Path, run_id: str) -> Path:
    return candidate_root(root) / validate_identifier(run_id)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialized_json_bytes(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialized_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def trusted_https_url(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_HOSTS
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
    )


def validate_redirect(source_url: str, target_url: str) -> None:
    if not trusted_https_url(source_url) or not trusted_https_url(target_url):
        raise ValueError("UNTRUSTED_HOST: redirect URL is outside the allowlist")
    if urlparse(source_url).hostname != urlparse(target_url).hostname:
        raise ValueError("UNTRUSTED_HOST: cross-host redirects are forbidden")


class SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_redirect(req.full_url, newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class MetClient:
    def __init__(self, *, requests_per_second: float = 2.0, timeout: int = 30):
        if requests_per_second <= 0 or requests_per_second > 2:
            raise ValueError("requests_per_second must be greater than zero and at most two")
        self.minimum_interval = 1.0 / requests_per_second
        self.timeout = timeout
        self.last_request_started: float | None = None
        self.opener = urllib.request.build_opener(SameHostRedirectHandler())

    def _open(self, url: str):
        if not trusted_https_url(url):
            raise ValueError("UNTRUSTED_HOST: request URL is outside the allowlist")
        if self.last_request_started is not None:
            remaining = self.minimum_interval - (time.monotonic() - self.last_request_started)
            if remaining > 0:
                time.sleep(remaining)
        self.last_request_started = time.monotonic()
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ThreadTruth-Studio-demo-evidence/1.0"},
        )
        return self.opener.open(request, timeout=self.timeout)

    def _json(self, url: str) -> dict[str, object]:
        with self._open(url) as response:
            data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                raise ValueError("EVIDENCE_INCOMPLETE: metadata response is too large")
        try:
            value = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("EVIDENCE_INCOMPLETE: metadata response is not JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("EVIDENCE_INCOMPLETE: metadata response is not an object")
        return value

    def search(self, query: str, limit: int) -> tuple[list[int], dict[str, object]]:
        params = urllib.parse.urlencode(
            {
                "q": validate_query(query),
                "hasImages": "true",
                "departmentId": 8,
                "offset": 0,
                "limit": validate_limit(limit),
            }
        )
        raw = self._json(
            "https://collectionapi.metmuseum.org/public/collection/v1.1/search?"
            + params
        )
        values = raw.get("objectIDs")
        object_ids = [value for value in values if isinstance(value, int)] if isinstance(values, list) else []
        return object_ids[:limit], raw

    def get_object(self, object_id: int) -> dict[str, object]:
        if not isinstance(object_id, int) or isinstance(object_id, bool) or object_id <= 0:
            raise ValueError("OBJECT_ID_MISMATCH: object ID must be a positive integer")
        return self._json(
            "https://collectionapi.metmuseum.org/public/collection/v1/objects/"
            f"{object_id}"
        )

    def download_image(self, url: str) -> dict[str, object]:
        with self._open(url) as response:
            final_url = response.geturl()
            if final_url != url:
                validate_redirect(url, final_url)
            data = response.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("DOWNLOAD_TOO_LARGE: image exceeds 50 MiB")
            content_type = response.headers.get_content_type()
        return {"data": data, "content_type": content_type, "final_url": final_url}


def metadata_rejection_codes(object_id: int, item: dict[str, object]) -> list[str]:
    codes: list[str] = []
    if item.get("objectID") != object_id:
        codes.append("OBJECT_ID_MISMATCH")
    if item.get("department") != "Costume Institute":
        codes.append("WRONG_DEPARTMENT")
    if item.get("isPublicDomain") is not True:
        codes.append("METADATA_NOT_PUBLIC_DOMAIN")
    primary_image = item.get("primaryImage")
    if not isinstance(primary_image, str) or not primary_image:
        codes.append("MISSING_PRIMARY_IMAGE")
    elif not trusted_https_url(primary_image):
        codes.append("UNTRUSTED_HOST")
    object_url = item.get("objectURL")
    if not isinstance(object_url, str) or not object_url:
        codes.append("EVIDENCE_INCOMPLETE")
    elif not trusted_https_url(object_url):
        codes.append("UNTRUSTED_HOST")
    thumbnail_url = item.get("primaryImageSmall")
    if thumbnail_url and not trusted_https_url(thumbnail_url):
        codes.append("UNTRUSTED_HOST")
    return list(dict.fromkeys(codes))


def candidate_from_metadata(
    object_id: int, item: dict[str, object], fetched_at: str
) -> dict[str, object]:
    metadata_digest = sha256_bytes(serialized_json_bytes(item))
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": f"met-{object_id}",
        "state": "discovered",
        "source": {
            "provider": "met",
            "object_id": object_id,
            "api_url": (
                "https://collectionapi.metmuseum.org/public/collection/v1/objects/"
                f"{object_id}"
            ),
            "object_url": item.get("objectURL", ""),
            "primary_image_url": item.get("primaryImage", ""),
            "thumbnail_url": item.get("primaryImageSmall", ""),
            "department": item.get("department", ""),
            "is_public_domain": item.get("isPublicDomain") is True,
            "object_name": item.get("objectName", ""),
            "title": item.get("title", ""),
            "culture": item.get("culture", ""),
            "object_date": item.get("objectDate", ""),
            "medium": item.get("medium", ""),
            "credit_line": item.get("creditLine", ""),
            "fetched_at": fetched_at,
            "raw_metadata_sha256": metadata_digest,
        },
        "license": {
            "id": CC0_ID if item.get("isPublicDomain") is True else None,
            "url": CC0_URL,
            "policy_url": MET_POLICY_URL,
        },
        "asset": None,
        "machine_audit": {
            "decision": "pending",
            "reason_codes": metadata_rejection_codes(object_id, item),
        },
        "human_review": {
            "decision": "pending",
            "reviewer": None,
            "reviewed_at": None,
            "checks": {
                "no_person": None,
                "no_logo": None,
                "no_watermark": None,
                "physical_garment": None,
                "not_sensitive": None,
            },
            "confirmation": None,
            "note": None,
        },
    }


def search_run(
    root: Path,
    query: str,
    limit: int,
    client: object,
    *,
    now: datetime | None = None,
    run_id: str | None = None,
) -> str:
    query = validate_query(query)
    limit = validate_limit(limit)
    now = now or datetime.now(timezone.utc)
    if run_id is None:
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") or "query"
        run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{slug[:32]}"
    validate_identifier(run_id)
    destination = run_path(root, run_id)
    if destination.exists():
        raise FileExistsError(f"run already exists: {run_id}")
    object_ids, raw_search = client.search(query, limit)
    object_ids = [value for value in object_ids if isinstance(value, int)][:limit]
    created_at = iso_z(now)
    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "provider": "met",
        "query": query,
        "requested_limit": limit,
        "object_ids": object_ids,
        "state": "discovered",
        "created_at": created_at,
        "expires_at": iso_z(now + timedelta(days=7)),
        "counts": {"discovered": len(object_ids)},
        "search_response_sha256": sha256_bytes(serialized_json_bytes(raw_search)),
    }
    write_json(destination / "raw" / "search.json", raw_search)
    write_json(destination / "run.json", run)
    return run_id


def reject_record(record: dict[str, object], codes: list[str]) -> dict[str, object]:
    current = str(record.get("state"))
    if current != "rights-rejected":
        validate_transition(current, "rights-rejected")
    record["state"] = "rights-rejected"
    record["machine_audit"] = {
        "decision": "reject",
        "reason_codes": list(dict.fromkeys(codes)),
    }
    return record


def fetch_run(
    root: Path,
    run_id: str,
    client: object,
    *,
    fetched_at: str | None = None,
) -> dict[str, object]:
    destination = run_path(root, run_id)
    fetched_at = fetched_at or iso_z(datetime.now(timezone.utc))
    run = ensure_run_active(root, run_id, fetched_at)
    if run.get("state") != "discovered":
        raise ValueError(f"STATE_TRANSITION_INVALID: {run.get('state')} -> fetched")
    counts = {"fetched": 0, "rights-rejected": 0}
    for object_id in run.get("object_ids", []):
        if not isinstance(object_id, int):
            continue
        item = client.get_object(object_id)
        record = candidate_from_metadata(object_id, item, fetched_at)
        write_json(destination / "raw" / f"met-{object_id}.json", item)
        codes = list(record["machine_audit"].get("reason_codes", []))
        if codes:
            reject_record(record, codes)
            counts["rights-rejected"] += 1
            write_json(destination / "candidates" / f"met-{object_id}.json", record)
            continue
        try:
            response = client.download_image(str(record["source"]["primary_image_url"]))
        except ValueError as exc:
            candidate_code = str(exc).split(":", 1)[0]
            code = (
                candidate_code
                if candidate_code in REJECTION_CODES
                and candidate_code != "STATE_TRANSITION_INVALID"
                else "DOWNLOAD_TYPE_INVALID"
            )
            reject_record(record, [code])
            counts["rights-rejected"] += 1
            write_json(destination / "candidates" / f"met-{object_id}.json", record)
            continue
        final_url = response.get("final_url")
        source_url = str(record["source"]["primary_image_url"])
        try:
            if final_url != source_url:
                validate_redirect(source_url, str(final_url))
            elif not trusted_https_url(final_url):
                raise ValueError("UNTRUSTED_HOST: final image URL is outside the allowlist")
        except ValueError:
            reject_record(record, ["UNTRUSTED_HOST"])
            counts["rights-rejected"] += 1
            write_json(destination / "candidates" / f"met-{object_id}.json", record)
            continue
        data = response.get("data")
        if not isinstance(data, bytes):
            reject_record(record, ["DOWNLOAD_TYPE_INVALID"])
            counts["rights-rejected"] += 1
            write_json(destination / "candidates" / f"met-{object_id}.json", record)
            continue
        image_path = destination / "images" / f"met-{object_id}.jpg"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(data)
        validate_transition("discovered", "fetched")
        record["state"] = "fetched"
        record["asset"] = {
            "relative_path": f"images/met-{object_id}.jpg",
            "sha256": sha256_bytes(data),
            "mime": str(response.get("content_type", "")),
            "bytes": len(data),
            "width": None,
            "height": None,
            "final_url": final_url,
        }
        counts["fetched"] += 1
        write_json(destination / "candidates" / f"met-{object_id}.json", record)
    run["state"] = "fetched"
    run["counts"] = counts
    write_json(destination / "run.json", run)
    return run


def audit_fetched_candidate(
    candidate: dict[str, object], data: bytes, *, seen_hashes: set[str]
) -> dict[str, object]:
    if candidate.get("state") != "fetched":
        raise ValueError(
            f"STATE_TRANSITION_INVALID: {candidate.get('state')} -> machine-passed"
        )
    asset = candidate.get("asset")
    codes = list(candidate["machine_audit"].get("reason_codes", []))
    if not isinstance(asset, dict):
        return reject_record(candidate, codes + ["EVIDENCE_INCOMPLETE"])
    digest = sha256_bytes(data)
    if asset.get("sha256") != digest or asset.get("bytes") != len(data):
        codes.append("EVIDENCE_INCOMPLETE")
    if str(asset.get("mime", "")).split(";", 1)[0].strip().lower() != "image/jpeg":
        codes.append("DOWNLOAD_TYPE_INVALID")
    if len(data) > MAX_IMAGE_BYTES:
        codes.append("DOWNLOAD_TOO_LARGE")
    width = None
    height = None
    try:
        width, height = jpeg_dimensions(data)
    except ValueError:
        codes.append("IMAGE_CORRUPT")
    if width is not None and height is not None and max(width, height) < MIN_LONG_EDGE:
        codes.append("IMAGE_TOO_SMALL")
    if digest in seen_hashes:
        codes.append("DUPLICATE_HASH")
    if not trusted_https_url(asset.get("final_url")):
        codes.append("UNTRUSTED_HOST")
    asset["width"] = width
    asset["height"] = height
    if codes:
        return reject_record(candidate, codes)
    validate_transition("fetched", "machine-passed")
    candidate["state"] = "machine-passed"
    candidate["machine_audit"] = {"decision": "pass", "reason_codes": []}
    return candidate


def audit_run(
    root: Path, run_id: str, *, audited_at: str | None = None
) -> dict[str, object]:
    destination = run_path(root, run_id)
    audited_at = audited_at or iso_z(datetime.now(timezone.utc))
    run = ensure_run_active(root, run_id, audited_at)
    if run.get("state") != "fetched":
        raise ValueError(
            f"STATE_TRANSITION_INVALID: {run.get('state')} -> machine-passed"
        )
    seen_hashes: set[str] = set()
    counts = {"machine-passed": 0, "rights-rejected": 0}
    for path in sorted((destination / "candidates").glob("met-*.json")):
        record = read_json(path)
        if record.get("state") == "rights-rejected":
            counts["rights-rejected"] += 1
            continue
        asset = record.get("asset")
        if not isinstance(asset, dict) or not isinstance(asset.get("relative_path"), str):
            reject_record(record, ["EVIDENCE_INCOMPLETE"])
        else:
            try:
                image_path = candidate_image_path(
                    root,
                    run_id,
                    str(record.get("candidate_id", "")),
                    asset["relative_path"],
                )
                data = image_path.read_bytes()
            except (OSError, ValueError):
                reject_record(record, ["EVIDENCE_INCOMPLETE"])
            else:
                record = audit_fetched_candidate(record, data, seen_hashes=seen_hashes)
                if record.get("state") == "machine-passed":
                    seen_hashes.add(str(record["asset"]["sha256"]))
        counts[str(record["state"])] += 1
        write_json(path, record)
    run["state"] = "machine-passed"
    run["counts"] = counts
    write_json(destination / "run.json", run)
    return run


def candidate_path(root: Path, run_id: str, candidate_id: str) -> Path:
    validate_identifier(candidate_id)
    if not candidate_id.startswith("met-"):
        raise ValueError("candidate identifier must start with met-")
    return run_path(root, run_id) / "candidates" / f"{candidate_id}.json"


def candidate_image_path(
    root: Path, run_id: str, candidate_id: str, relative_path: object
) -> Path:
    expected = f"images/{candidate_id}.jpg"
    if relative_path != expected:
        raise ValueError("EVIDENCE_INCOMPLETE: candidate image path is not canonical")
    return run_path(root, run_id) / expected


def parse_iso_z(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("timestamp must be ISO-8601 with a timezone") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def ensure_run_active(root: Path, run_id: str, at: str) -> dict[str, object]:
    run = read_json(run_path(root, run_id) / "run.json")
    checked_at = parse_iso_z(at)
    if checked_at < parse_iso_z(str(run["created_at"])):
        raise ValueError("EVIDENCE_INCOMPLETE: action predates the candidate run")
    if checked_at >= parse_iso_z(str(run["expires_at"])):
        raise ValueError("RUN_EXPIRED: candidate run is older than seven days")
    return run


def approve_candidate(
    root: Path,
    run_id: str,
    candidate_id: str,
    *,
    reviewer: str,
    checks: dict[str, bool],
    confirmation: str,
    reviewed_at: str,
    note: str | None = None,
) -> dict[str, object]:
    run = ensure_run_active(root, run_id, reviewed_at)
    path = candidate_path(root, run_id, candidate_id)
    record = read_json(path)
    try:
        validate_reviewer(reviewer)
    except ValueError:
        reviewer_ok = False
    else:
        reviewer_ok = True
    checks_ok = set(checks) == set(REVIEW_CHECKS) and all(
        checks.get(name) is True for name in REVIEW_CHECKS
    )
    if (
        record.get("state") != "machine-passed"
        or not reviewer_ok
        or not checks_ok
        or confirmation != APPROVAL_CONFIRMATION
    ):
        raise ValueError("HUMAN_REVIEW_INCOMPLETE: every visual check and confirmation is required")
    validate_transition("machine-passed", "human-approved")
    record["state"] = "human-approved"
    record["human_review"] = {
        "decision": "approved",
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "checks": {name: True for name in REVIEW_CHECKS},
        "confirmation": confirmation,
        "note": note,
    }
    write_json(path, record)
    run["state"] = "human-approved"
    approved_candidates = run.get("approved_candidates")
    if not isinstance(approved_candidates, list):
        approved_candidates = []
    if candidate_id not in approved_candidates:
        approved_candidates.append(candidate_id)
    run["approved_candidates"] = approved_candidates
    write_json(run_path(root, run_id) / "run.json", run)
    return record


def reject_candidate(
    root: Path,
    run_id: str,
    candidate_id: str,
    *,
    reason: str,
    reviewer: str,
    reviewed_at: str,
    note: str | None = None,
) -> dict[str, object]:
    if reason not in REJECTION_CODES or reason == "STATE_TRANSITION_INVALID":
        raise ValueError(f"unknown rejection reason: {reason}")
    validate_reviewer(reviewer)
    run = read_json(run_path(root, run_id) / "run.json")
    reviewed = parse_iso_z(reviewed_at)
    if reviewed < parse_iso_z(str(run["created_at"])):
        raise ValueError("EVIDENCE_INCOMPLETE: review predates the candidate run")
    path = candidate_path(root, run_id, candidate_id)
    record = read_json(path)
    if record.get("state") not in {"discovered", "fetched", "machine-passed", "human-approved"}:
        raise ValueError(
            f"STATE_TRANSITION_INVALID: {record.get('state')} -> rights-rejected"
        )
    reject_record(record, [reason])
    human_review = record.get("human_review")
    if not isinstance(human_review, dict):
        human_review = {}
    human_review.update(
        {
            "decision": "rejected",
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "confirmation": None,
            "note": note,
        }
    )
    record["human_review"] = human_review
    write_json(path, record)
    rejected_candidates = run.get("rejected_candidates")
    if not isinstance(rejected_candidates, list):
        rejected_candidates = []
    if candidate_id not in rejected_candidates:
        rejected_candidates.append(candidate_id)
    run["rejected_candidates"] = rejected_candidates
    approved_candidates = run.get("approved_candidates")
    if isinstance(approved_candidates, list):
        run["approved_candidates"] = [
            value for value in approved_candidates if value != candidate_id
        ]
    write_json(run_path(root, run_id) / "run.json", run)
    return record


def generate_gallery(root: Path, run_id: str) -> Path:
    destination = run_path(root, run_id)
    run = read_json(destination / "run.json")
    cards: list[str] = []
    for path in sorted((destination / "candidates").glob("met-*.json")):
        record = read_json(path)
        candidate_id = str(record.get("candidate_id", "unknown"))
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        asset = record.get("asset") if isinstance(record.get("asset"), dict) else {}
        image_path = asset.get("relative_path")
        image_html = (
            f'<img src="{html.escape(str(image_path), quote=True)}" '
            f'alt="The Met candidate {html.escape(candidate_id)}">'
            if isinstance(image_path, str)
            else '<p class="missing">No local image downloaded.</p>'
        )
        source_url = html.escape(str(source.get("object_url", "")), quote=True)
        approve_command = (
            f"python3 tools/demo-media.py approve --run {quote(run_id)} "
            f"--candidate {quote(candidate_id)} --reviewer github:YOUR-HANDLE "
            "--no-person --no-logo --no-watermark --physical-garment --not-sensitive "
            f"--confirm {quote(APPROVAL_CONFIRMATION)}"
        )
        reject_command = (
            f"python3 tools/demo-media.py reject --run {quote(run_id)} "
            f"--candidate {quote(candidate_id)} --reason LOGO_OR_TRADEMARK "
            "--reviewer github:YOUR-HANDLE"
        )
        reasons = record.get("machine_audit", {}).get("reason_codes", [])
        cards.append(
            "<article>"
            f"<h2>{html.escape(candidate_id)} · {html.escape(str(record.get('state')))}</h2>"
            f"{image_html}"
            f"<p><strong>{html.escape(str(source.get('title', 'Untitled')))}</strong></p>"
            f"<p>Department: {html.escape(str(source.get('department', '')))}</p>"
            f"<p>Date: {html.escape(str(source.get('object_date', '')))} · "
            f"Medium: {html.escape(str(source.get('medium', '')))}</p>"
            f'<p><a href="{source_url}">Open the authoritative object page</a></p>'
            f'<p>License: <a href="{CC0_URL}">CC0-1.0</a> · '
            f'<a href="{MET_POLICY_URL}">The Met Open Access basis</a> · '
            f"machine reasons: {html.escape(', '.join(reasons) or 'none')}</p>"
            "<ul><li>No identifiable person</li><li>No logo or trademark</li>"
            "<li>No watermark</li><li>Physical garment</li>"
            "<li>No cultural or sensitive context</li></ul>"
            f"<h3>Approve</h3><pre>{html.escape(approve_command)}</pre>"
            f"<h3>Reject (replace the reason when needed)</h3><pre>{html.escape(reject_command)}</pre>"
            "</article>"
        )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ThreadTruth rights review · {html.escape(run_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:auto;padding:1.25rem;color:#171717}}
main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}}
article{{border:1px solid #bbb;border-radius:.6rem;padding:1rem;overflow-wrap:anywhere}}
img{{display:block;max-width:100%;height:auto;margin:auto}} pre{{white-space:pre-wrap;background:#f3f3f3;padding:.75rem}}
a:focus{{outline:3px solid #005fcc}} .missing{{padding:2rem;background:#eee}}
@media print{{main{{display:block}} article{{break-inside:avoid;margin-bottom:1rem}}}}
</style></head><body>
<a href="#candidates">Skip to candidates</a>
<h1>ThreadTruth Studio · local rights review</h1>
<p>Run {html.escape(run_id)} · query {html.escape(str(run.get('query', '')))}. This local page does not approve media.</p>
<p>Replace <code>github:YOUR-HANDLE</code> with the public handle of the person who actually performs the review.</p>
<main id="candidates">{''.join(cards)}</main>
</body></html>
"""
    output = destination / "review.html"
    output.write_text(document, encoding="utf-8")
    return output


def validate_human_approval(record: dict[str, object]) -> list[str]:
    findings: list[str] = []
    review = record.get("human_review")
    if record.get("state") not in {"human-approved", "promoted"} or not isinstance(review, dict):
        return ["HUMAN_REVIEW_INCOMPLETE"]
    if review.get("decision") != "approved":
        findings.append("HUMAN_REVIEW_INCOMPLETE")
    if review.get("confirmation") != APPROVAL_CONFIRMATION:
        findings.append("HUMAN_REVIEW_INCOMPLETE")
    try:
        parse_iso_z(str(review.get("reviewed_at", "")))
    except ValueError:
        findings.append("HUMAN_REVIEW_INCOMPLETE")
    checks = review.get("checks")
    if not isinstance(checks, dict) or any(checks.get(name) is not True for name in REVIEW_CHECKS):
        findings.append("HUMAN_REVIEW_INCOMPLETE")
    try:
        validate_reviewer(str(review.get("reviewer", "")))
    except ValueError:
        findings.append("HUMAN_REVIEW_INCOMPLETE")
    return list(dict.fromkeys(findings))


def promotion_evidence_findings(
    record: dict[str, object],
    image_data: bytes,
    current_item: dict[str, object],
    *,
    promoted_at: str,
) -> list[str]:
    findings = validate_human_approval(record)
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    license_record = record.get("license") if isinstance(record.get("license"), dict) else {}
    asset = record.get("asset") if isinstance(record.get("asset"), dict) else {}
    review = record.get("human_review") if isinstance(record.get("human_review"), dict) else {}
    try:
        if parse_iso_z(str(review.get("reviewed_at", ""))) > parse_iso_z(
            promoted_at
        ):
            findings.append("HUMAN_REVIEW_INCOMPLETE")
    except ValueError:
        findings.append("HUMAN_REVIEW_INCOMPLETE")
    object_id = source.get("object_id")
    if not isinstance(object_id, int):
        findings.append("EVIDENCE_INCOMPLETE")
    else:
        current_codes = metadata_rejection_codes(object_id, current_item)
        if current_codes:
            findings.append("SOURCE_METADATA_CHANGED")
        for source_key, current_key in (
            ("object_id", "objectID"),
            ("is_public_domain", "isPublicDomain"),
            ("primary_image_url", "primaryImage"),
            ("department", "department"),
        ):
            if source.get(source_key) != current_item.get(current_key):
                findings.append("SOURCE_METADATA_CHANGED")
                break
    if license_record.get("id") != CC0_ID or license_record.get("url") != CC0_URL:
        findings.append("LICENSE_NOT_CC0")
    digest = sha256_bytes(image_data)
    if asset.get("sha256") != digest or asset.get("bytes") != len(image_data):
        findings.append("EVIDENCE_INCOMPLETE")
    try:
        width, height = jpeg_dimensions(image_data)
    except ValueError:
        findings.append("IMAGE_CORRUPT")
    else:
        if asset.get("width") != width or asset.get("height") != height:
            findings.append("EVIDENCE_INCOMPLETE")
    return list(dict.fromkeys(findings))


def public_case_root(root: Path) -> Path:
    return root.resolve() / "docs" / "demo" / "cases"


def build_public_rights_record(
    case_id: str,
    record: dict[str, object],
    current_item: dict[str, object],
    promoted_at: str,
) -> dict[str, object]:
    source = record["source"]
    asset = record["asset"]
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "candidate_id": record["candidate_id"],
        "status": "promoted",
        "role": "auxiliary",
        "primary_demo_status": "sample-blocked",
        "source": {
            "provider": "The Metropolitan Museum of Art Open Access",
            "object_id": source["object_id"],
            "object_url": source["object_url"],
            "api_url": source["api_url"],
            "primary_image_url": source["primary_image_url"],
            "metadata_sha256_at_discovery": source["raw_metadata_sha256"],
            "metadata_sha256_at_promotion": sha256_bytes(serialized_json_bytes(current_item)),
        },
        "source_license": {
            "id": CC0_ID,
            "url": CC0_URL,
            "policy_url": MET_POLICY_URL,
        },
        "media_license": {
            "id": CC0_ID,
            "url": CC0_URL,
            "scope": "Source media and generated demo media to the extent the project can grant rights.",
        },
        "asset": {
            "path": "source.jpg",
            "sha256": asset["sha256"],
            "mime": "image/jpeg",
            "bytes": asset["bytes"],
            "width": asset["width"],
            "height": asset["height"],
        },
        "human_review": {
            key: value
            for key, value in record["human_review"].items()
            if key != "note"
        },
        "promoted_at": promoted_at,
        "notices": [
            "This project is not endorsed by The Metropolitan Museum of Art.",
            "Apache-2.0 does not apply to media in this case.",
            "CC0 does not eliminate possible trademark, privacy, personality, or cultural rights.",
        ],
    }


def public_case_readme(rights: dict[str, object], item: dict[str, object]) -> str:
    return f"""# Auxiliary public demo source — {rights['case_id']}

Status: `auxiliary-demo-ready`. This auxiliary case does not determine or satisfy primary-demo status; see the repository rights index for the current primary record.

This physical garment source comes from [The Metropolitan Museum of Art Open Access]({item.get('objectURL', '')}) and is identified by object ID `{item.get('objectID')}`. This independent community project is not endorsed by The Metropolitan Museum of Art.

The source image is CC0. Project-generated demo media is offered under CC0 to the extent the project can grant rights. Apache-2.0 covers project code and documentation, not media in this case. CC0 does not eliminate possible trademark, privacy, personality, moral, or cultural rights.

See `rights.json` and `source-metadata.json` for the retained evidence record.
"""


def rights_index_content(root: Path) -> str:
    module_path = Path(__file__).with_name("primary_demo.py")
    spec = importlib.util.spec_from_file_location("threadtruth_primary_demo", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load primary demo rights index")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.primary_rights_index_content(root)


def render_rights_index(root: Path) -> Path:
    demo_root = root.resolve() / "docs" / "demo"
    content = rights_index_content(root)
    output = demo_root / "RIGHTS.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def _preview_source_readme(rights: dict[str, object]) -> str:
    return f"""# Controlled preview source — beige blazer and dark-denim outfit

Status: `approved-for-preview`. This 3:4 image documents one real coordinated physical outfit for the ThreadTruth Studio 24-style public direction-preview collection.

The source and its generated or derived preview media use `{PREVIEW_SOURCE_LICENSE}`: they may be displayed and distributed only as part of this repository and its releases. Standalone reuse, resale, relicensing and CC0 dedication are not granted. Rights remain with their respective holders, and trademark, privacy, personality and cultural rights are not waived. Apache-2.0 covers project code and documentation, not this media.

See `rights.json` for the original PNG digest, optimized JPEG derivation, structured outfit truth and maintainer attestation.
"""


def validate_preview_sources(root: Path) -> list[str]:
    findings: list[str] = []
    demo_root = root.resolve() / "docs" / "demo"
    base = demo_root / "preview-sources"
    if not base.exists() and not (demo_root / "preview-source-v1.schema.json").exists():
        return []
    if not base.is_dir() or base.is_symlink():
        return ["preview-sources: controlled source directory is missing or unsafe"]
    entries = list(sorted(base.iterdir()))
    if {entry.name for entry in entries} != PREVIEW_SOURCE_CASES:
        findings.append("preview-sources: source allowlist mismatch")
    for case in entries:
        prefix = case.name
        if case.is_symlink() or not case.is_dir() or case.name not in PREVIEW_SOURCE_CASES:
            findings.append(f"{prefix}: unregistered or unsafe preview source")
            continue
        children = list(sorted(case.iterdir()))
        if {entry.name for entry in children} != PREVIEW_SOURCE_FILES or any(entry.is_symlink() or not entry.is_file() for entry in children):
            findings.append(f"{prefix}: unregistered or missing preview source artifact")
            continue
        try:
            rights = read_json(case / "rights.json")
            image_data = (case / "source.jpg").read_bytes()
            readme = (case / "README.md").read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError) as error:
            findings.append(f"{prefix}: unreadable preview source: {error}")
            continue
        expected_keys = {"schema_version", "case_id", "status", "license", "attestation", "original", "public_asset", "outfit", "review_contract"}
        if set(rights) != expected_keys or rights.get("schema_version") != "1.0" or rights.get("case_id") != case.name or rights.get("status") != "approved-for-preview":
            findings.append(f"{prefix}: preview source record invalid")
        license_record = rights.get("license")
        if not isinstance(license_record, dict) or set(license_record) != {"id", "scope", "notice"} or license_record.get("id") != PREVIEW_SOURCE_LICENSE:
            findings.append(f"{prefix}: preview source license invalid")
        elif "no standalone reuse, resale, relicensing or CC0 dedication" not in str(license_record.get("scope")) or "Apache-2.0 covers project code and documentation, not this media" not in str(license_record.get("notice")):
            findings.append(f"{prefix}: preview source license scope incomplete")
        attestation = rights.get("attestation")
        if attestation != {"physical_outfit": True, "repository_and_release_demo_rights": True}:
            findings.append(f"{prefix}: maintainer attestation incomplete")
        original = rights.get("original")
        if original != {"sha256": "40163fcb0aeae44b1e9b690de9fec047bd517a0764260a4d3f1d014dbfc16d5a", "width": 1086, "height": 1448, "mime": "image/png"}:
            findings.append(f"{prefix}: original source binding invalid")
        asset = rights.get("public_asset")
        if not isinstance(asset, dict) or asset.get("path") != "source.jpg" or asset.get("mime") != "image/jpeg" or asset.get("sha256") != sha256_bytes(image_data) or asset.get("bytes") != len(image_data):
            findings.append(f"{prefix}: public source asset binding invalid")
        else:
            try:
                dimensions = jpeg_dimensions(image_data)
            except ValueError:
                dimensions = None
            if dimensions != (1086, 1448) or [asset.get("width"), asset.get("height")] != [1086, 1448] or asset.get("derivation") != "EXIF-transposed RGB JPEG transcode; metadata removed":
                findings.append(f"{prefix}: public source JPEG metadata invalid")
        outfit = rights.get("outfit")
        expected_outfit = {
            "name_en": "Beige blazer and dark-denim outfit",
            "name_zh": "米色西装与深色牛仔套装",
            "core_items": ["beige single-breasted notched-lapel blazer", "white crew-neck top", "dark indigo straight-leg jeans", "olive structured tote", "dark-brown loafers"],
            "optional_when_visible": ["watch", "restrained gold jewelry"],
            "forbidden": ["brand invention", "logo invention", "text invention", "replacement garment"],
        }
        if outfit != expected_outfit or rights.get("review_contract") != "coordinated-outfit-v1":
            findings.append(f"{prefix}: structured outfit truth invalid")
        serialized = json.dumps(rights, ensure_ascii=False)
        if re.search(r"(?:/Users/|/home/|/tmp/|[A-Za-z]:\\\\)", serialized) or "@qq.com" in serialized.lower():
            findings.append(f"{prefix}: unsafe preview source text")
        if readme != _preview_source_readme(rights):
            findings.append(f"{prefix}: preview source README is stale")
    return findings


def promote_candidate(
    root: Path,
    run_id: str,
    candidate_id: str,
    case_id: str,
    client: object,
    *,
    promoted_at: str,
) -> dict[str, object]:
    validate_identifier(case_id)
    ensure_run_active(root, run_id, promoted_at)
    path = candidate_path(root, run_id, candidate_id)
    record = read_json(path)
    approval_findings = validate_human_approval(record)
    if approval_findings:
        raise ValueError("HUMAN_REVIEW_INCOMPLETE: candidate is not approved")
    asset = record.get("asset")
    if not isinstance(asset, dict) or not isinstance(asset.get("relative_path"), str):
        raise ValueError("EVIDENCE_INCOMPLETE: image evidence is missing")
    try:
        image_path = candidate_image_path(root, run_id, candidate_id, asset["relative_path"])
        image_data = image_path.read_bytes()
    except (OSError, ValueError) as exc:
        raise ValueError("EVIDENCE_INCOMPLETE: local candidate image is missing") from exc
    source = record.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("object_id"), int):
        raise ValueError("EVIDENCE_INCOMPLETE: source object id is missing")
    expected_candidate_id = f"met-{source['object_id']}"
    if candidate_id != expected_candidate_id or record.get("candidate_id") != candidate_id:
        raise ValueError("OBJECT_ID_MISMATCH: candidate id does not match source object id")
    discovery_path = run_path(root, run_id) / "raw" / f"{candidate_id}.json"
    try:
        discovery_bytes = discovery_path.read_bytes()
        discovery_item = json.loads(discovery_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("EVIDENCE_INCOMPLETE: discovery metadata is unreadable") from exc
    if source.get("raw_metadata_sha256") != sha256_bytes(discovery_bytes):
        raise ValueError("EVIDENCE_INCOMPLETE: discovery metadata hash does not match")
    for source_key, discovery_key in (
        ("object_id", "objectID"),
        ("object_url", "objectURL"),
        ("primary_image_url", "primaryImage"),
        ("department", "department"),
        ("is_public_domain", "isPublicDomain"),
    ):
        if source.get(source_key) != discovery_item.get(discovery_key):
            raise ValueError("EVIDENCE_INCOMPLETE: discovery metadata record drifted")
    current_item = client.get_object(source["object_id"])
    findings = promotion_evidence_findings(
        record, image_data, current_item, promoted_at=promoted_at
    )
    if findings:
        if "SOURCE_METADATA_CHANGED" in findings:
            reject_record(record, ["SOURCE_METADATA_CHANGED"])
            write_json(path, record)
        raise ValueError(f"{findings[0]}: promotion evidence failed")

    destination = public_case_root(root) / case_id
    rights = build_public_rights_record(case_id, record, current_item, promoted_at)
    if record.get("state") == "promoted" and not destination.exists():
        raise ValueError("EVIDENCE_INCOMPLETE: promoted public case is missing")
    if destination.exists():
        existing_rights_path = destination / "rights.json"
        if not existing_rights_path.is_file():
            raise FileExistsError(f"public case collision: {case_id}")
        existing = read_json(existing_rights_path)
        if (
            existing.get("candidate_id") != candidate_id
            or existing.get("asset", {}).get("sha256") != rights["asset"]["sha256"]
            or sha256_bytes((destination / "source.jpg").read_bytes())
            != rights["asset"]["sha256"]
        ):
            raise FileExistsError(f"public case collision: {case_id}")
        if record.get("state") == "human-approved":
            validate_transition("human-approved", "promoted")
        elif record.get("state") != "promoted":
            raise ValueError(
                f"STATE_TRANSITION_INVALID: {record.get('state')} -> promoted"
            )
        record["state"] = "promoted"
        record["public_case"] = {
            "case_id": case_id,
            "relative_path": f"docs/demo/cases/{case_id}",
            "promoted_at": existing.get("promoted_at"),
        }
        write_json(path, record)
        run = read_json(run_path(root, run_id) / "run.json")
        run["state"] = "promoted"
        promoted_cases = run.get("promoted_cases")
        if not isinstance(promoted_cases, list):
            promoted_cases = []
        if case_id not in promoted_cases:
            promoted_cases.append(case_id)
        run["promoted_cases"] = promoted_cases
        write_json(run_path(root, run_id) / "run.json", run)
        render_rights_index(root)
        return existing

    public_case_root(root).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{case_id}-", dir=candidate_root(root)) as temp_dir:
        stage = Path(temp_dir) / case_id
        stage.mkdir()
        (stage / "source.jpg").write_bytes(image_data)
        write_json(stage / "source-metadata.json", current_item)
        write_json(stage / "rights.json", rights)
        (stage / "README.md").write_text(
            public_case_readme(rights, current_item), encoding="utf-8"
        )
        shutil.move(str(stage), str(destination))

    validate_transition(str(record.get("state")), "promoted")
    record["state"] = "promoted"
    record["public_case"] = {
        "case_id": case_id,
        "relative_path": f"docs/demo/cases/{case_id}",
        "promoted_at": promoted_at,
    }
    write_json(path, record)
    run = read_json(run_path(root, run_id) / "run.json")
    run["state"] = "promoted"
    promoted_cases = run.get("promoted_cases")
    if not isinstance(promoted_cases, list):
        promoted_cases = []
    if case_id not in promoted_cases:
        promoted_cases.append(case_id)
    run["promoted_cases"] = promoted_cases
    write_json(run_path(root, run_id) / "run.json", run)
    render_rights_index(root)
    return rights


def validate_public_cases(root: Path) -> list[str]:
    findings: list[str] = []
    demo_root = root.resolve() / "docs" / "demo"
    cases_root = public_case_root(root)
    findings.extend(validate_preview_sources(root))
    if demo_root.exists():
        for entry in sorted(demo_root.iterdir()):
            if entry.is_symlink():
                findings.append(f"{entry.name}: symlinks are forbidden")
            elif entry.is_file() and entry.name not in DEMO_ROOT_FILES:
                findings.append(f"{entry.name}: unregistered demo artifact")
            elif entry.is_dir() and entry.name not in DEMO_ROOT_DIRS:
                findings.append(f"{entry.name}: unregistered demo directory")
    cases_available = cases_root.is_dir() and not cases_root.is_symlink()
    if cases_available:
        for entry in sorted(cases_root.iterdir()):
            if entry.is_symlink():
                findings.append(f"{entry.name}: symlinks are forbidden")
            elif entry.is_file():
                findings.append(f"{entry.name}: unregistered case entry")
    case_dirs = (
        sorted(
            path
            for path in cases_root.iterdir()
            if path.is_dir() and not path.is_symlink()
        )
        if cases_available
        else []
    )
    for case_dir in case_dirs:
        required = ("source.jpg", "source-metadata.json", "rights.json", "README.md")
        case_findings: list[str] = []
        for entry in sorted(case_dir.iterdir()):
            if entry.is_symlink():
                case_findings.append(f"{case_dir.name}/{entry.name}: symlinks are forbidden")
            elif not entry.is_file() or entry.name not in PUBLIC_CASE_FILES:
                case_findings.append(
                    f"{case_dir.name}/{entry.name}: unregistered demo case artifact"
                )
        for name in required:
            if not (case_dir / name).is_file():
                case_findings.append(f"{case_dir.name}: missing {name}")
        findings.extend(case_findings)
        if not (case_dir / "rights.json").is_file():
            continue
        try:
            rights = read_json(case_dir / "rights.json")
            metadata = read_json(case_dir / "source-metadata.json")
            image_data = (case_dir / "source.jpg").read_bytes()
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(f"{case_dir.name}: unreadable evidence: {exc}")
            continue
        if rights.get("status") != "promoted" or rights.get("role") != "auxiliary":
            findings.append(f"{case_dir.name}: case is not promoted auxiliary media")
        if rights.get("schema_version") != SCHEMA_VERSION:
            findings.append(f"{case_dir.name}: unsupported rights schema version")
        if rights.get("case_id") != case_dir.name:
            findings.append(f"{case_dir.name}: case identifier does not match directory")
        review_findings = validate_human_approval(
            {"state": "human-approved", "human_review": rights.get("human_review")}
        )
        if review_findings:
            findings.append(f"{case_dir.name}: human review evidence is incomplete")
        try:
            public_review = rights.get("human_review")
            reviewed_time = parse_iso_z(
                str(public_review.get("reviewed_at", ""))
                if isinstance(public_review, dict)
                else ""
            )
            promoted_time = parse_iso_z(str(rights.get("promoted_at", "")))
            if reviewed_time > promoted_time:
                findings.append(f"{case_dir.name}: human review postdates promotion")
        except (AttributeError, ValueError):
            findings.append(f"{case_dir.name}: review or promotion timestamp is invalid")
        for key in ("source_license", "media_license"):
            license_record = rights.get(key)
            if (
                not isinstance(license_record, dict)
                or license_record.get("id") != CC0_ID
                or license_record.get("url") != CC0_URL
            ):
                findings.append(f"{case_dir.name}: {key} must be CC0-1.0")
        asset = rights.get("asset")
        if not isinstance(asset, dict) or asset.get("sha256") != sha256_bytes(image_data):
            findings.append(f"{case_dir.name}: source image hash does not match rights.json")
        else:
            if len(image_data) > MAX_IMAGE_BYTES:
                findings.append(f"{case_dir.name}: source image exceeds 50 MiB")
            try:
                width, height = jpeg_dimensions(image_data)
            except ValueError:
                findings.append(f"{case_dir.name}: source image is not a valid JPEG")
            else:
                if max(width, height) < MIN_LONG_EDGE:
                    findings.append(f"{case_dir.name}: source image is too small")
                if (
                    asset.get("path") != "source.jpg"
                    or asset.get("mime") != "image/jpeg"
                    or asset.get("bytes") != len(image_data)
                    or asset.get("width") != width
                    or asset.get("height") != height
                ):
                    findings.append(f"{case_dir.name}: source image evidence is incomplete")
        source = rights.get("source")
        if not isinstance(source, dict) or source.get("object_id") != metadata.get("objectID"):
            findings.append(f"{case_dir.name}: source object metadata mismatch")
        elif (
            source.get("object_url") != metadata.get("objectURL")
            or source.get("primary_image_url") != metadata.get("primaryImage")
        ):
            findings.append(f"{case_dir.name}: source URL metadata mismatch")
        if not isinstance(source, dict) or source.get(
            "metadata_sha256_at_promotion"
        ) != sha256_bytes((case_dir / "source-metadata.json").read_bytes()):
            findings.append(f"{case_dir.name}: promotion metadata hash does not match")
        if metadata.get("isPublicDomain") is not True:
            findings.append(f"{case_dir.name}: source metadata is not public domain")
        if metadata.get("department") != "Costume Institute":
            findings.append(f"{case_dir.name}: source metadata is outside Costume Institute")
        if not trusted_https_url(metadata.get("primaryImage")):
            findings.append(f"{case_dir.name}: source image URL is untrusted")
        if not trusted_https_url(metadata.get("objectURL")):
            findings.append(f"{case_dir.name}: source object URL is untrusted")
    primary_markers = (
        demo_root / "primary-cases",
        demo_root / "primary-rights-v1.schema.json",
        demo_root / "style-index.json",
        demo_root / "styles",
        demo_root / "STYLES.md",
    )
    if any(path.exists() for path in primary_markers):
        module_path = Path(__file__).with_name("primary_demo.py")
        spec = importlib.util.spec_from_file_location("threadtruth_primary_demo", module_path)
        if spec is None or spec.loader is None:
            findings.append("primary demo validator is unavailable")
        else:
            primary = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(primary)
            findings.extend(primary.validate_public_primary_cases(root))
            findings.extend(primary.validate_style_index(root))
            findings.extend(primary.validate_style_pages(root))
    preview_path = Path(__file__).with_name("style_preview.py")
    spec = importlib.util.spec_from_file_location("threadtruth_style_preview", preview_path)
    if spec is None or spec.loader is None:
        findings.append("preview validator unavailable")
    else:
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        try:
            findings.extend(preview.validate_public_previews(root))
        except (OSError, ValueError, TypeError):
            findings.append("unsafe preview root")
    index_path = root.resolve() / "docs" / "demo" / "RIGHTS.md"
    try:
        current_index = index_path.read_text(encoding="utf-8")
    except OSError:
        findings.append("public rights index is missing")
    else:
        try:
            expected_index = rights_index_content(root)
        except (OSError, ValueError, KeyError, TypeError):
            findings.append("public rights index cannot be derived from invalid records")
        else:
            if current_index != expected_index:
                findings.append("public rights index is stale")
    return findings


def audit_download(
    candidate: dict[str, object],
    data: bytes,
    content_type: str,
    *,
    seen_hashes: set[str],
) -> dict[str, object]:
    if candidate.get("state") != "discovered":
        raise ValueError(
            f"STATE_TRANSITION_INVALID: {candidate.get('state')} -> fetched"
        )
    validate_transition("discovered", "fetched")
    candidate["state"] = "fetched"
    codes = list(candidate["machine_audit"].get("reason_codes", []))
    digest = sha256_bytes(data)
    width = None
    height = None
    if content_type.split(";", 1)[0].strip().lower() != "image/jpeg":
        codes.append("DOWNLOAD_TYPE_INVALID")
    if len(data) > MAX_IMAGE_BYTES:
        codes.append("DOWNLOAD_TOO_LARGE")
    try:
        width, height = jpeg_dimensions(data)
    except ValueError:
        codes.append("IMAGE_CORRUPT")
    if width is not None and height is not None and max(width, height) < MIN_LONG_EDGE:
        codes.append("IMAGE_TOO_SMALL")
    if digest in seen_hashes:
        codes.append("DUPLICATE_HASH")
    candidate["asset"] = {
        "relative_path": f"images/{candidate['candidate_id']}.jpg",
        "sha256": digest,
        "mime": "image/jpeg",
        "bytes": len(data),
        "width": width,
        "height": height,
    }
    unique_codes = list(dict.fromkeys(codes))
    if unique_codes:
        validate_transition("fetched", "rights-rejected")
        candidate["state"] = "rights-rejected"
        candidate["machine_audit"] = {
            "decision": "reject",
            "reason_codes": unique_codes,
        }
    else:
        validate_transition("fetched", "machine-passed")
        candidate["state"] = "machine-passed"
        candidate["machine_audit"] = {
            "decision": "pass",
            "reason_codes": [],
        }
    return candidate


def parse_jpeg_quantization_tables(payload: bytes) -> set[int]:
    table_ids: set[int] = set()
    cursor = 0
    while cursor < len(payload):
        table_info = payload[cursor]
        cursor += 1
        precision = table_info >> 4
        table_id = table_info & 0x0F
        if precision not in {0, 1} or table_id > 3:
            raise ValueError("IMAGE_CORRUPT: invalid JPEG quantization table")
        table_size = 64 * (precision + 1)
        if cursor + table_size > len(payload):
            raise ValueError("IMAGE_CORRUPT: truncated JPEG quantization table")
        raw_values = payload[cursor : cursor + table_size]
        values = (
            [
                int.from_bytes(raw_values[index : index + 2], "big")
                for index in range(0, table_size, 2)
            ]
            if precision == 1
            else list(raw_values)
        )
        if any(value == 0 for value in values):
            raise ValueError("IMAGE_CORRUPT: zero JPEG quantization value")
        table_ids.add(table_id)
        cursor += table_size
    if not table_ids:
        raise ValueError("IMAGE_CORRUPT: empty JPEG quantization segment")
    return table_ids


def parse_jpeg_huffman_tables(payload: bytes) -> tuple[set[int], set[int]]:
    dc_tables: set[int] = set()
    ac_tables: set[int] = set()
    cursor = 0
    while cursor < len(payload):
        if cursor + 17 > len(payload):
            raise ValueError("IMAGE_CORRUPT: truncated JPEG Huffman table")
        table_info = payload[cursor]
        cursor += 1
        table_class = table_info >> 4
        table_id = table_info & 0x0F
        if table_class not in {0, 1} or table_id > 3:
            raise ValueError("IMAGE_CORRUPT: invalid JPEG Huffman table selector")
        counts = payload[cursor : cursor + 16]
        cursor += 16
        symbol_count = sum(counts)
        if symbol_count == 0 or cursor + symbol_count > len(payload):
            raise ValueError("IMAGE_CORRUPT: empty or truncated JPEG Huffman table")
        remaining_codes = 1
        for count in counts:
            remaining_codes = remaining_codes * 2 - count
            if remaining_codes < 0:
                raise ValueError("IMAGE_CORRUPT: oversubscribed JPEG Huffman table")
        cursor += symbol_count
        (dc_tables if table_class == 0 else ac_tables).add(table_id)
    return dc_tables, ac_tables


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError("IMAGE_CORRUPT: missing JPEG SOI marker")
    offset = 2
    dimensions: tuple[int, int] | None = None
    sampling: list[tuple[int, int]] = []
    frame_component_ids: set[int] = set()
    frame_quantization_ids: set[int] = set()
    quantization_tables: set[int] = set()
    dc_huffman_tables: set[int] = set()
    ac_huffman_tables: set[int] = set()
    while offset < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker == 0xD9:
            break
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            break
        payload = data[offset + 2 : offset + segment_length]
        if marker == 0xDB:
            quantization_tables.update(parse_jpeg_quantization_tables(payload))
        elif marker == 0xC4:
            dc_tables, ac_tables = parse_jpeg_huffman_tables(payload)
            dc_huffman_tables.update(dc_tables)
            ac_huffman_tables.update(ac_tables)
        if marker == 0xDA:
            if not payload:
                break
            scan_component_count = payload[0]
            if (
                scan_component_count != len(frame_component_ids)
                or len(payload) != 1 + scan_component_count * 2 + 3
            ):
                break
            scan_component_ids: set[int] = set()
            scan_tables_valid = True
            for scan_index in range(scan_component_count):
                component_id = payload[1 + scan_index * 2]
                table_selector = payload[2 + scan_index * 2]
                if (
                    component_id not in frame_component_ids
                    or table_selector >> 4 not in dc_huffman_tables
                    or table_selector & 0x0F not in ac_huffman_tables
                ):
                    scan_tables_valid = False
                    break
                scan_component_ids.add(component_id)
            spectral = payload[-3:]
            if (
                not scan_tables_valid
                or scan_component_ids != frame_component_ids
                or spectral != b"\x00\x3f\x00"
                or not frame_quantization_ids.issubset(quantization_tables)
            ):
                break
            scan_start = offset + segment_length
            entropy_bytes = 0
            cursor = scan_start
            while cursor + 1 < len(data):
                if data[cursor] != 0xFF:
                    entropy_bytes += 1
                    cursor += 1
                    continue
                following = data[cursor + 1]
                if following == 0x00:
                    entropy_bytes += 1
                    cursor += 2
                    continue
                if 0xD0 <= following <= 0xD7:
                    cursor += 2
                    continue
                if following == 0xD9:
                    if (
                        dimensions is None
                        or not sampling
                        or not quantization_tables
                        or not dc_huffman_tables
                        or not ac_huffman_tables
                    ):
                        break
                    width, height = dimensions
                    max_horizontal = max(value[0] for value in sampling)
                    max_vertical = max(value[1] for value in sampling)
                    mcus_across = (width + 8 * max_horizontal - 1) // (
                        8 * max_horizontal
                    )
                    mcus_down = (height + 8 * max_vertical - 1) // (
                        8 * max_vertical
                    )
                    blocks_per_mcu = sum(
                        horizontal * vertical for horizontal, vertical in sampling
                    )
                    minimum_entropy_bits = mcus_across * mcus_down * blocks_per_mcu * 2
                    if entropy_bytes * 8 >= minimum_entropy_bits:
                        return dimensions
                    break
                break
            break
        if marker == 0xC0:
            if segment_length < 11 or data[offset + 2] != 8:
                break
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            component_count = data[offset + 7]
            if (
                width <= 0
                or height == 0
                or component_count not in {1, 3, 4}
                or segment_length != 8 + component_count * 3
            ):
                break
            sampling = []
            frame_component_ids = set()
            frame_quantization_ids = set()
            for component_index in range(component_count):
                component_id = data[offset + 8 + component_index * 3]
                sample_byte = data[offset + 9 + component_index * 3]
                quantization_id = data[offset + 10 + component_index * 3]
                horizontal = sample_byte >> 4
                vertical = sample_byte & 0x0F
                if (
                    horizontal == 0
                    or vertical == 0
                    or component_id in frame_component_ids
                    or quantization_id > 3
                ):
                    sampling = []
                    break
                frame_component_ids.add(component_id)
                frame_quantization_ids.add(quantization_id)
                sampling.append((horizontal, vertical))
            if sampling:
                dimensions = (width, height)
        elif marker in {
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            break
        offset += segment_length
    raise ValueError("IMAGE_CORRUPT: complete baseline JPEG evidence is missing")


def prune_expired_runs(root: Path, *, now: datetime | None = None) -> list[str]:
    base = candidate_root(root)
    if not base.exists():
        return []
    now = now or datetime.now(timezone.utc)
    removed: list[str] = []
    for destination in sorted(base.iterdir()):
        if not destination.is_dir() or destination.is_symlink():
            continue
        try:
            validate_identifier(destination.name)
            run = read_json(destination / "run.json")
            expires_at = parse_iso_z(str(run["expires_at"]))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        if now.astimezone(timezone.utc) < expires_at:
            continue
        states = []
        for path in sorted((destination / "candidates").glob("met-*.json")):
            try:
                record = read_json(path)
            except (OSError, json.JSONDecodeError):
                states.append("unreadable")
                continue
            states.append(str(record.get("state")))
        if any(state in {"human-approved", "promoted", "unreadable"} for state in states):
            continue
        for path in sorted((destination / "candidates").glob("met-*.json")):
            record = read_json(path)
            current = str(record.get("state"))
            if current != "expired":
                validate_transition(current, "expired")
                record["state_before_expiry"] = current
                record["state"] = "expired"
                write_json(path, record)
        run["state_before_expiry"] = run.get("state")
        run["state"] = "expired"
        write_json(destination / "run.json", run)
        resolved = destination.resolve()
        if resolved.parent != base.resolve():
            raise ValueError("STATE_TRANSITION_INVALID: prune target escaped candidate root")
        shutil.rmtree(resolved)
        removed.append(destination.name)
    return removed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect and govern The Met CC0 garment candidates for public demos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", default="coat")
    search_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    for name in ("fetch", "audit", "gallery"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--run", required=True)

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("--run", required=True)
    approve_parser.add_argument("--candidate", required=True)
    approve_parser.add_argument("--reviewer", required=True)
    approve_parser.add_argument("--no-person", action="store_true")
    approve_parser.add_argument("--no-logo", action="store_true")
    approve_parser.add_argument("--no-watermark", action="store_true")
    approve_parser.add_argument("--physical-garment", action="store_true")
    approve_parser.add_argument("--not-sensitive", action="store_true")
    approve_parser.add_argument("--confirm", required=True)
    approve_parser.add_argument("--note")

    reject_parser = subparsers.add_parser("reject")
    reject_parser.add_argument("--run", required=True)
    reject_parser.add_argument("--candidate", required=True)
    reject_parser.add_argument("--reason", required=True, choices=sorted(REJECTION_CODES))
    reject_parser.add_argument("--reviewer", required=True)
    reject_parser.add_argument("--note")

    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--run", required=True)
    promote_parser.add_argument("--candidate", required=True)
    promote_parser.add_argument("--case-id", required=True)

    prune_parser = subparsers.add_parser("prune")
    prune_parser.add_argument("--expired", action="store_true", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    now = iso_z(datetime.now(timezone.utc))
    client = MetClient() if args.command in {"search", "fetch", "promote"} else None
    try:
        if args.command == "search":
            run_id = search_run(root, args.query, args.limit, client)
            print(run_id)
        elif args.command == "fetch":
            print(json.dumps(fetch_run(root, args.run, client), ensure_ascii=False, indent=2))
        elif args.command == "audit":
            print(json.dumps(audit_run(root, args.run), ensure_ascii=False, indent=2))
        elif args.command == "gallery":
            print(generate_gallery(root, args.run))
        elif args.command == "approve":
            checks = {
                "no_person": args.no_person,
                "no_logo": args.no_logo,
                "no_watermark": args.no_watermark,
                "physical_garment": args.physical_garment,
                "not_sensitive": args.not_sensitive,
            }
            record = approve_candidate(
                root,
                args.run,
                args.candidate,
                reviewer=args.reviewer,
                checks=checks,
                confirmation=args.confirm,
                reviewed_at=now,
                note=args.note,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
        elif args.command == "reject":
            record = reject_candidate(
                root,
                args.run,
                args.candidate,
                reason=args.reason,
                reviewer=args.reviewer,
                reviewed_at=now,
                note=args.note,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
        elif args.command == "promote":
            rights = promote_candidate(
                root,
                args.run,
                args.candidate,
                args.case_id,
                client,
                promoted_at=now,
            )
            print(json.dumps(rights, ensure_ascii=False, indent=2))
        elif args.command == "prune":
            for run_id in prune_expired_runs(root):
                print(run_id)
    except (FileNotFoundError, FileExistsError, ValueError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
