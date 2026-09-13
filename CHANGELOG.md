# Changelog

All notable changes are documented here. Versions follow Semantic Versioning.

## 2026-09-13 — Unreleased preview scope correction and task register

### Trigger

- The maintainer corrected the development preview target from four mixed-style boards to 24 single-style sheets, each showing the same authorized garment in the six canonical runtime action-0 poses.

### Behavior before

- The maintainer clarified the intended example: 24 separate previews of ONE garment, each preview using ONE style and SIX poses from existing runtime action 0. The beta.2 four-board/mixed-style interpretation was wrong, not merely a canvas problem.

### Behavior after

- Replaced the development collector with schema v2: 24 style-owned records, each binding one runtime-derived action-0 prompt, one pack, six canonical poses, one native receipt, observed whole-sheet metadata and its own six-pose human review. Incomplete audit/gallery views remain honest; v1 stays read-only and cannot be promoted.
- Added whole-sheet gallery/public-index integration, v2 release validation, source regressions and current English/Chinese/Growth/Beta/application/offline-guide wording. Runtime Skill/reference bytes are unchanged. No native image was generated, no human review was synthesized and no preview was promoted; approved previews remain 0/24. The historical beta.2 entry below describes what shipped, not the corrected target.
- Closed review gaps: trusted gallery approval now revalidates live sheet bytes; full audit lists unapproved style IDs while scoped audit supports machine-readiness checks; repeat promotion transactionally repairs and validates projections; whole sheets retain intrinsic display dimensions; and Growth treats the gallery template as implemented.

### Eval coverage

- Added v2 contract, drift, source authorization, receipt uniqueness, incomplete review, historical v1 rejection, whole-sheet gallery/public projection and six-final isolation regressions. Synthetic human attestations exist only inside disposable tests and do not count as preview evidence.
- Added regressions for pending/tampered review labels, on-disk image tampering, full-versus-scoped audit results, idempotent projection repair, no-upscale HTML/CSS and current Growth wording.

### Verification

- The 92-test repository suite, strict source and runtime production checks, pack lint, trigger regression, public scan, JSON parsing, diff hygiene and runtime-byte parity pass. Controller browser checks pass at desktop and mobile widths. No real preview image, human approval, promotion, release, remote action or installation was performed.

## 2026-09-13 — 1.0.0-beta.2

### Trigger and behavior

The maintainer requested the same authorized white vest in all24 styles, four six-style preview boards, DENGGUI attribution and clearer Beta onboarding. Previously the style index only accepted independent-final representatives and the download lacked a reproducible personal-source registration entry.

- Added a development-only prepare/ingest/audit/gallery/approve/promote preview pipeline binding all24 actual packs, source rights, native-output receipts and per-tile human review. Four boards are previews, never six-final cases. The runtime Skill and its six-image/safety boundaries are unchanged.
- Separated preview coverage (0/24 approved at this release) from independently generated case coverage (1/24). No unapproved preview image is packaged.
- Added a dry-run-first local-source installer with explicit apply/replace, preserved marketplace metadata and rollback copies. It never enables the Plugin by itself.
- Changed public display attribution to DENGGUI, with authorized WeChat contact Lvmusic0930; existing GitHub namespace, reviewer identities and provenance are preserved.
- Updated bilingual entry points, installation, security and offline documentation. Added opt-in installation feedback and read-only, local-only Beta metric summaries.
- Kept the2026-09-13 Beta start and immutable beta.1 artifacts.30days/5installers/3workflows remain project goals, not official admission requirements.

### Verification and limitations

New refusal/success tests cover source and pack drift, preview attestation/approval/hash tampering, orphan media, installer preservation/rollback, consented deduplication and distinct download categories. Public scans include tracked files even if force-added from ignored directories; private ignored review workspaces are not public source. No scanning rule was weakened. Full release evidence is recorded in [beta.2 verification](docs/verification/2026-09-13-beta.2.md).

Native preview generation and human acceptance are separate later gates. New-host CLI activation, an external installation and real operation recording remain pending; mock-home source registration is not fresh-host functional verification. No new runtime rules, API fallback or telemetry were added.

## 2026-09-13 — 1.0.0-beta.1

### Trigger

The active identity is `$threadtruth-studio`; explicit, positive apparel, negative adjacent-domain, conflict, and authorization paths are covered by public fixtures.

### Behavior before

The private predecessor used a legacy active name, mentioned specific image models, and mixed runtime and development evidence in one Skill tree.

### Behavior after

The public Plugin has one active identity, model-agnostic host-native generation, an allowlisted runtime payload, and explicit publication/installation/application authorization gates.

### Eval coverage

The repository carries behavior evals, 24 per-style suites, deterministic route cases, repository contracts, and an allowlist packaging test.

### Verification

System Skill validation, official Plugin validation, production strict/runtime checks, 24/24 pack lint, trigger regression, privacy scanning, release staging, public CI, and the maintainer-machine Plugin lifecycle passed. The first authorized source-to-six-image primary case and one auxiliary CC0 rights case are public. External clean-environment evidence remains pending. Minimal implicit missing-image behavior is tracked in [Issue #1](https://github.com/2278091160dg-rgb/threadtruth-studio/issues/1).

#### Added

- Clean Codex Plugin repository and Apache-2.0 licensing.
- Public identity `threadtruth-studio` and bilingual user documentation.
- Allowlist release builder, repository contract tests, CI, community files, and Beta evidence templates.
- Competitive boundary and Codex for Open Source readiness packet.
- Public GitHub repository, passing GitHub Actions, and a privacy-safe local lifecycle verification record.
- Development-only The Met Open Access CC0 evidence pipeline with quarantine, machine audit, offline human-review gallery, governed promotion, schemas, and release-time rights validation.
- A rights-cleared primary white-vest case with four sources, six accepted results, hashes, canvas checks, human QA review, and AI-generated-media disclosure.
- A 24-style evidence index with three primary-case targets, eight featured styles, six source families, and honest planned placeholders.
- A 1280×640 source-to-results social preview and a privacy-preserving, telemetry-free GitHub growth cadence.

#### Changed

- Migrated the private `clothing-portrait-studio` runtime from commit `1eb29ad` without its Git history or private evidence.
- Replaced specific image-model wording with the host's native image generation capability.
- Reset public maturity to `DRAFT` until rights-cleared Beta evidence is complete.
- Archived the legacy live Skill after verifying rollback, then restored and enabled Plugin version `1.0.0-beta.1`.

#### Security

- Preserved the R1–R7 safety boundary, explicit paid-action consent, six-call cap, and no API/CLI/third-party fallback.
- Release validation rejects unregistered demo media, stale rights indexes, incomplete human review evidence, undersized or oversized files, malformed JPEGs, metadata drift, and hash mismatch.
- Candidate paths and redirects are fail-closed; expired approvals cannot be promoted but may be explicitly rejected and pruned.
