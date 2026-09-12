# Release Readiness

## Candidate

- Version: `1.0.0-beta.1`
- Status: source candidate, not published
- License: Apache-2.0
- Distribution: Codex Plugin repository plus allowlist-built archive
- Runtime telemetry: none
- External connectors/MCP/API fallback: none

## Required gates before publishing the Beta tag

- All repository tests, 24/24 pack lint, trigger eval, Plugin validation, production strict validation, runtime-stage validation, JSON/YAML/Python checks, privacy/history scans, and release staging checks pass.
- A rights-cleared source garment and full demo chain have a completed rights manifest.
- A clean Plugin installation proves explicit invocation, implicit trigger, negative isolation, uninstall, and rollback.
- The maintainer authorizes public repository creation, push, and Release publication.

## Known limitations

This project does not provide virtual-fit simulation, CAD accuracy, text/logo guarantees, unattended commercial approval, third-party integrations, or platform-performance guarantees. Native image behavior varies by host and must be evidenced in the release compatibility record.

## Release artifacts

Run `python3 tools/build-release.py`. The command creates a versioned ZIP and a SHA-256 file under `dist/`. Artifacts are generated locally and are not uploaded automatically.
