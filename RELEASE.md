# Release Readiness

## Candidate

- Version: `1.0.0-beta.1`
- Status: public source candidate; no GitHub Release published
- License: Apache-2.0
- Distribution: Codex Plugin repository plus allowlist-built archive
- Runtime telemetry: none
- External connectors/MCP/API fallback: none

## Required gates before publishing the Beta tag

- All repository tests, 24/24 pack lint, trigger eval, Plugin validation, production strict validation, runtime-stage validation, JSON/YAML/Python checks, privacy/history scans, and release staging checks pass.
- A rights-cleared source garment and full demo chain have a completed rights manifest.
- Maintainer-machine installation proves explicit invocation, substantive implicit discovery, negative isolation, uninstall, upgrade, and rollback.
- The minimal implicit missing-image behavior in [Issue #1](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/1) is resolved or explicitly accepted and release-noted after a rights-cleared real-image test.
- A non-maintainer clean environment repeats installation and discovery before the Beta exits.
- The maintainer separately authorizes GitHub Release publication after reviewing the final artifacts.

## Known limitations

This project does not provide virtual-fit simulation, CAD accuracy, text/logo guarantees, unattended commercial approval, third-party integrations, or platform-performance guarantees. Native image behavior varies by host and must be evidenced in the release compatibility record.

## Release artifacts

Run `python3 tools/build-release.py`. The command creates a versioned ZIP and a SHA-256 file under `dist/`. Artifacts are generated locally and are not uploaded automatically.
