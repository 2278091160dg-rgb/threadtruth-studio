# Fixed-card preview delivery implementation

The maintainer approved this plan in the conversation on 2026-09-14. Use task-scoped implementation, TDD and independent review. This plan supersedes the display-only native geometry restriction, not historical findings or the runtime Skill.

## Goal and constraints

- Same authorized white vest, adult female, 24 registered styles, one six-pose native preview per style. Fixed-card layout is explicitly authorized; no new native generation, push, release, global installation or real human approval in this development batch.
- Keep runtime byte-identical. Retain all original images, prompts and receipts. Historical attempts remain 3, native strict-qualified 0, human-approved 0 and public 0 until actual new evidence exists.
- Display board 1200x1200; six 360x480 cards; x=44,420,796; y=140,636. Six complete source panels are fitted using min(1,360/w,480/h), centered with white padding. No image stretch, upscale, generative fill or crop of pose/garment content. Rectangle extraction removes only original gutters/text regions; visual preservation remains a human check.
- Header: registered complete Chinese/English style name, mode and same-white-vest six-pose subtitle. Footer: AI生成 · 排版衍生预览 · 非成片 and PREVIEW ONLY — NOT FINAL. Text stays outside cards. Use supplied local font, record its hash/name, never publish font binaries or absolute paths.
- Native source, display derivative and thumbnail must be distinguishable, hash-linked and never counted as independent finals. Approval is explicit human review, not agent-generated assertions. All 24 approvals remain required before public promotion.
- Existing beta.1/beta.2 are immutable; beta.3 remains unpublished until media and release gates pass. No new API, OCR service, runtime dependency or generic migration framework. A development-only CJK font is required for rendering tests and is never redistributed.

## Task 1: Compose and retain honest preview evidence

Own tools/style_preview.py, an optional small tools/preview_cards.py helper, tests/test_style_preview.py plus focused new card tests and preview schema files. Do not modify runtime, primary_demo.py or human-facing current docs; controller owns those consumers/docs.

- Write failing behavior tests before implementation. Use real synthetic pixel panels, independently calculated rectangles and outcomes; do not test source strings as a substitute for behavior.
- Extend the current collector with compose --run-id --style --layout-json --font. Require an ingested native image and six observed rectangles bound to its hash. Validate numeric types, positive bounds, non-overlap, row/column order and six panels; source panels need not themselves be 3:4.
- Use a new evidence schema to distinguish native and display facts. Keep old runs read-only. Preserve the existing native prompt contract where practical so the registered Korean schema-3 original, exact prompt and real call receipt can be ingested into a fresh run without inventing a new call. Do not alter old receipts or inherit old human reviews. Report any unavoidable interface decision before broadening migration scope.
- Compose exact fixed cards and separate label bands. Require readable supplied font and text-fit checks; use smaller font or wrapping within reserved bands, never silently truncate style names or paint over a card. Output stripped-metadata JPEG display plus whole-board thumbnail and original whole-sheet optimized JPEG. Record actual original hash, actual prompt/call binding, observed extraction rectangles, fit transforms, font hash/name, composition parameters and all asset hashes/dimensions. No machine-generated real visual PASS flags.
- Geometry PASS means deterministic card geometry only. Keep native exact-grid failure/history independent. Review must bind current derivative and source hashes and attest six-pose product/identity/style/framing, complete panel extraction, padding/no subject loss, correct text and disclosure.
- Integrate audit, gallery, promotion and release-facing validation. Public directory allowlist includes only registered originals/derivatives/thumbnails and generated records/pages. Show both native and composed whole sheets with explicit disclosures. Fail closed for absent compose, modified source/derivative/layout, old approval, unsafe paths, malformed rectangles, reused call/hash and unapproved promotion. Repeated identical compose is idempotent; differing approved content cannot be silently overwritten.
- Expose a small public asset enumeration interface if needed for the primary rights consumer; coordinate exact shape with controller. Do not copy rights rendering into a new system.
- Run focused tests, self-review and commit only owned files. Report RED/GREEN results and interface details to the controller; no subagents or image calls.

## Task 2: Case route and current documentation integration

Controller owns tools/primary_demo.py, tests/test_primary_demo.py, current README/Chinese/offline guides, preview instructions, WORK-STATUS/BETA/GROWTH/CODEX-FOR-OSS, source CHANGELOG and integration tests as needed.

- TDD: accept consistent B1/B and C1/C six-independent-final routes, keep current B1 cases valid, reject mismatched mode/action and preview/test image contamination. Keep 2:3 and exactly six unique final images. New planned case defaults: ecommerce-studio B1; american-street C1.
- Consume Task1 native/display/thumbnail asset records in rights index and style pages; generated indexes remain mechanically regenerated. Do not add fixture or unapproved real media to public case directories.
- Synchronize current docs to fixed-card meaning, schema/commands and actual counts: 3 historical native attempts; initially 0 composed, 0 approved, 0 public. Update after the real composed pilot exists, distinguishing machine display checks from visual approval. Historical reports/changelogs stay as snapshots; add a new changelog entry.
- Retain DENGGUI/contact/installation; make extra independent final representatives optional, not part of the 24 same-white-vest preview obligation. Preserve 21 package IDs and mark T11 reopened only for this additional change until verified.
- Record the approved schedule: developer work first execution day; existing Korean pilot first with zero new calls; other23 serial only after signoff and per-style authorization, every4 review not daily cap; beta.3 after24signoffs and release authority. External lifecycle/recording target Sep18; installers5 target Oct5; two new cases target Sep30; Beta exit no earlier Oct13 12:59 Beijing; stable then authorized application. Dates shift only with actual blockers. No automation changes or external posts in this batch.
- Issue1: inspect existing reproduction evidence and trigger behavior, document reproducible code defect versus host discovery limitation. Do not launch paid/real host probes without separate authorization and do not close the public issue without a fix/verified outcome.

## Task 3: Verify and show the real pilot

- Read the canonical schema3 Korean native original and inspect its pixels before layout. Reuse its exact original/prompt/call records in a fresh local run; use observed cell bounds, never assume native geometry from square dimensions. Compose using local Chinese font. Keep review fields pending. Independently view the result, check geometry and six-cell content, then show the complete board to the maintainer.
- Run full repository tests once after integration, 24pack lint, trigger regression, system/Plugin/source/runtime checks, public tree/history scan, JSON/YAML/Python parsing, release allowlist staging and unchanged runtime comparison. Focused failures get targeted reruns, not repeated unrelated audits.
- Browser-check actual offline gallery at desktop/mobile, keyboard links, no external resources/errors; source versus display disclosure must be visible. Update honest count and verification evidence, independent final review, then commit only intended changes.
- Do not merge/push/release or generate remaining images automatically. Preserve worktree for explicit integration/release handoff. Report completed software separately from pending human, external adoption, time and publication gates.
