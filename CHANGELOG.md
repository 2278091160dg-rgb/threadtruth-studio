# Changelog

All notable changes are documented here. Versions follow Semantic Versioning.

## 2026-09-13 — Unreleased preview layout and label contract

### Trigger

- The maintainer found that the corrected single-style collector still lacked explicit acceptance checks for the whole-board ratio, per-cell ratio, full registered style label, native subtitle/footer, and text-to-subject overlap.

### Behavior before

- Schema `2.0` bound one style and six poses but could accept a non-square native board, omitted observed cell/text-band geometry and framing attestations, and did not bind the layout/label contracts into the native receipt. Its earlier narrow machine result therefore did not qualify the real Korean C attempt. The beta.2 mixed-style board was already a separate wrong-format draft.

### Behavior after

- Schema `3.0` now requires a native and retained `1:1` board containing independent title, subtitle, two rows of three `3:4` cells, and footer bands. Poses 1/2/4/6 require full-body framing; 3/5 permit half-body. Native dimensions plus layout and label hashes are bound into each receipt and review evidence.
- Prompts require the full registered bilingual style name, exact mode subtitle and exact bilingual AI preview footer to be rendered natively. Original output is preserved before validation; there is no crop, stretch, padding, enlargement or scripted text repair.
- Human review now records six observed cell rectangles plus observed title/subtitle/footer rectangles in retained-image pixels, allowing only one-pixel size/alignment/raster-ratio rounding. Explicit boundary, text correctness/readability, non-overlap and per-pose framing checks default to pending; missing/pending/fail fields or `public_use_approved: false` are not consent.
- Schema `1.0` and `2.0` runs remain read-only history and cannot be prepared, ingested, approved or promoted. Current evidence requires a new run ID. Style-scoped audit can report file evidence without claiming human visual approval; full audit and promotion require all 24 current-schema sheets and reviews.
- Operator, bilingual, offline, Beta, growth, application and work-status wording now separates local software closure from image readiness. Current counts are one unqualified native single-style attempt, 0/24 qualified, 0/24 human-approved and 0/24 public; the prior mixed-style board is separate. The next Korean C retry and the remaining 23 styles require new explicit native authorization.

### Eval coverage

- Added regressions for non-square native output, bad cell ratio/size/alignment/order, out-of-bounds and overlapping rectangles, malformed numeric fields, missing or pending label/framing attestations, receipt/review/image hash tampering, and direct old-schema promotion.
- Retained transactional promotion, historical-gallery accessibility, scoped/full audit, whole-sheet no-upscale, public projection and six-independent-final isolation coverage. Synthetic `900x900` geometry and all-pass attestations remain disposable test fixtures only; they do not count as real review evidence.

### Verification

- Task 1 reports 24/24 focused preview tests and 108/108 repository tests passing at implementation commit `0922c61`; its independent task spec/quality review reported no findings. Final combined tests and guide rendering are recorded separately in [the controller verification report](docs/verification/2026-09-13-preview-layout-label-contract.md) and must not be inferred before that report is closed.
- This static change does not certify the existing real image or the full project. No native call, human approval, promotion, release, network action, installation or runtime change was performed. External lifecycle remains 0/1, non-maintainer installations 0/5, complete primary cases 1/3, and external-feedback fixes 0/1.

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
