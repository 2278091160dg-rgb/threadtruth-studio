# Release Readiness

## Candidate

- Version: `1.0.0-beta.1`
- Status: release-ready candidate; GitHub publication remains
- License: Apache-2.0
- Distribution: Codex Plugin repository plus allowlist-built archive
- Runtime telemetry: none
- External connectors/MCP/API fallback: none

## Required gates before publishing the Beta tag

- All repository tests, 24/24 pack lint, trigger eval, Plugin validation, production strict validation, runtime-stage validation, JSON/YAML/Python checks, privacy/history scans, and release staging checks pass.
- A rights-cleared source garment and full demo chain have a completed rights manifest.
- Maintainer-machine installation proves explicit invocation, substantive implicit discovery, negative isolation, uninstall, upgrade, and rollback.
- The minimal implicit missing-image behavior in [Issue #1](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/1) is release-noted and accepted for this Beta after a rights-cleared real-image workflow passed through explicit invocation.
- A non-maintainer clean environment repeats installation and discovery before the Beta exits.
- The maintainer reviews the final artifact names, checksums, and release notes before publication.

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

Both commands create a versioned ZIP and a separate SHA-256 sidecar under `dist/`. The Plugin ZIP excludes development tools and original PNGs; the media ZIP contains the four authorized sources, six accepted original results, rights declaration, public-safe run and prompt evidence, and an internal checksum manifest.
