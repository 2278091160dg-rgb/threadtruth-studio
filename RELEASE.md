# Release Readiness

## Released Beta

- Version: `1.0.0-beta.4`
- Status: [`v1.0.0-beta.4`](https://github.com/denggui-ai/threadtruth-studio/releases/tag/v1.0.0-beta.4) published as a GitHub prerelease at `2026-09-15T00:18:31Z` from merge commit `f80b4c4`. beta.1–beta.3 remain available and immutable.
- License: Apache-2.0
- Distribution: Codex Plugin repository plus allowlist-built archive
- Runtime telemetry: none
- External connectors/MCP/API fallback: none
- Guide decision: guide-required; offline guide is in the release envelope, outside runtime

## Required gates before publishing the Beta tag

- All repository tests, 24/24 pack lint, trigger eval, Plugin validation, production strict validation, runtime-stage validation, JSON/YAML/Python checks, privacy/history scans, and release staging checks pass.
- A rights-cleared source garment and full demo chain have a completed rights manifest.
- Maintainer-machine installation proves explicit invocation, substantive implicit discovery, negative isolation, uninstall, upgrade, and rollback.
- The minimal implicit missing-image behavior in [Issue #1](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/1) is release-noted and accepted for this Beta after a rights-cleared real-image workflow passed through explicit invocation.
- A non-maintainer clean environment repeats installation and discovery before the Beta exits.
- The maintainer reviews the final artifact names, checksums, and release notes before publication.

For beta.4, runtime bytes remain unchanged. The release adds a second 24-style, hash-bound, human-accepted direction-preview collection for one coordinated outfit. It does not raise independent-final coverage above 1/24 or complete-case coverage above 1/3. Local failure and replacement records remain private; the public record retains their hashes. Fresh-host CLI activation and external lifecycle evidence remain pending.

## Known limitations

This project does not provide virtual-fit simulation, CAD accuracy, text/logo guarantees, unattended commercial approval, third-party integrations, or platform-performance guarantees. Native image behavior varies by host and must be evidenced in the release compatibility record.

## Release artifacts

Build the allowlisted Plugin archive:

```bash
python3 tools/build-release.py
```

Build the original-resolution primary-case media archive:

```bash
python3 tools/primary-demo.py build-media \
  --staging .threadtruth/primary-demo/white-hooded-puffer-vest \
  --case-id white-hooded-puffer-vest-korean-cold \
  --version 1.0.0-beta.1 \
  --output dist
```

Both commands create a versioned ZIP and a separate SHA-256 sidecar under `dist/`. The Plugin ZIP excludes development tools and full-resolution PNGs; the media ZIP contains four metadata-stripped authorized sources, six metadata-stripped full-resolution PNG results, allowlisted rights/run evidence, a README, and an internal checksum manifest. Raw prompts, private logs, previews, and staging records are excluded.

The beta.1 media archive remains the authoritative unchanged original six-image package; later Betas do not duplicate it. beta.4 carries both accepted 24-style preview collections, including optimized native sheets, layout derivatives, thumbnails and sanitized evidence. Raw native PNGs, local receipts, rejected drafts and private lineage paths never enter the Plugin envelope.
